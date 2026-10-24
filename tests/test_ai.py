import json
import os
import stat
import tempfile
import time
from types import SimpleNamespace as Event
import unittest
from unittest.mock import MagicMock, patch

from AI import analyze_report, final_report, INSTRUCTIONS
from AIAdapters import APIKeyAdapter, ChatGPTAdapter, create_adapter
from ChatGPTAuth import ChatGPTSession, REQUIRED_SCOPES


class AdapterTests(unittest.TestCase):
    def stream(self, adapter, events):
        client = MagicMock()
        client.responses.create.return_value.__enter__.return_value = iter(events)
        adapter.client = client
        result = adapter.generate(
            history=[{"role": "user", "content": "evidence"}],
            tools=[], instructions="instructions")
        return result, client.responses.create.call_args

    def test_both_adapters_share_request_but_use_separate_credentials(self):
        session = MagicMock()
        session.access_token.return_value = "oauth-test"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "api-test"}), patch("AIAdapters.OpenAI"):
            for adapter, key in ((APIKeyAdapter("test-model"), "api-test"),
                                 (ChatGPTAdapter("test-model", session), "oauth-test")):
                response = Event(status="completed", error=None, output=[], output_text="report")
                result, request = self.stream(adapter, [
                    Event(type="response.output_text.delta", delta="report"),
                    Event(type="response.completed", response=response)])
                self.assertIs(result, response)
                self.assertEqual(adapter.credential(), key)
                self.assertEqual(request.kwargs["input"], [{"role": "user", "content": "evidence"}])
                self.assertFalse(request.kwargs["store"])
                self.assertTrue(request.kwargs["stream"])

    def test_stream_without_terminal_or_with_error_is_rejected(self):
        for terminal in (None, "error"):
            events = [Event(type="response.output_text.delta", delta="partial")]
            if terminal:
                events.append(Event(type=terminal))
            with self.subTest(terminal=terminal), patch("AIAdapters.OpenAI"), self.assertRaises(RuntimeError):
                self.stream(ChatGPTAdapter("test", MagicMock()), events)

    def test_missing_api_key_does_not_use_chatgpt(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            APIKeyAdapter("test").credential()
        with self.assertRaises(ValueError):
            create_adapter("unknown", "test")

    def test_report_is_passed_as_untrusted_evidence(self):
        adapter = MagicMock()
        run = {"history": [], "stop_reason": "completed", "iterations": {}}
        adapter.agent_loop.return_value = run
        report = {"schema_version": "2.0", "binaries": {}, "analyses": {},
                  "changes": [{"change_id": "change_0000"}], "conflicts": []}
        self.assertEqual(analyze_report(report, adapter), run)
        adapter.generate.assert_not_called()
        request = adapter.agent_loop.call_args.kwargs
        self.assertEqual(json.loads(request["prompt"]), report)
        self.assertEqual(request["tools"], [])
        self.assertEqual(request["instructions"], INSTRUCTIONS)

    def test_final_report_shows_the_useful_trace(self):
        run = {"stop_reason": "completed", "history": [
            {"role": "user", "content": "entrada"},
            {"type": "function_call", "name": "get_function", "call_id": "call_1", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call_1", "output": "resultado"},
            {"type": "message", "role": "assistant", "phase": "final_answer",
             "content": [{"type": "output_text", "text": "conclusión"}]},
        ]}
        text = final_report(run)
        for expected in ("entrada", "get_function", "resultado", "conclusión"):
            self.assertIn(expected, text)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.session = ChatGPTSession(self.temp.name)
        self.record = dict(client_id="issued", subject="user", access_token="old",
                           refresh_token="refresh-old", scopes=list(REQUIRED_SCOPES), expires_at=0)
        self.session._save(self.record)

    def test_refresh_rotates_credentials_and_preserves_registration(self):
        with patch("ChatGPTAuth.request_json", return_value=dict(access_token="new", refresh_token="refresh-new",
                   token_type="Bearer", expires_in=3600)) as request:
            self.assertEqual(self.session.access_token(), "new")
            self.assertEqual(request.call_args.args[1]["client_id"], "issued")
        saved = self.session._load()
        self.assertEqual(saved["refresh_token"], "refresh-new")
        self.assertEqual(saved["subject"], "user")
        self.assertEqual(stat.S_IMODE(self.session.path.stat().st_mode), 0o600)

    def test_denied_scopes_cannot_overwrite_session(self):
        with patch("ChatGPTAuth.request_json", return_value=dict(access_token="new", token_type="Bearer",
                   expires_in=3600, scope="openid")), self.assertRaises(RuntimeError):
            self.session.access_token()
        self.assertEqual(self.session._load()["access_token"], "old")

    def test_fresh_session_does_not_refresh(self):
        self.record["expires_at"] = time.time() + 3600
        self.session._save(self.record)
        with patch("ChatGPTAuth.request_json") as request:
            self.assertEqual(self.session.access_token(), "old")
            request.assert_not_called()

    def test_logout_revokes_then_removes_tokens_but_keeps_registration(self):
        with patch("ChatGPTAuth.request_json", side_effect=[
                {"revocation_endpoint": "https://auth.openai.com/revoke"}, {}]):
            self.session.logout()
        self.assertNotIn("access_token", self.session._load())
        self.assertEqual(self.session._load()["client_id"], "issued")

    def test_failed_revocation_preserves_credentials_for_retry(self):
        with patch("ChatGPTAuth.request_json", side_effect=OSError("network")), self.assertRaises(OSError):
            self.session.logout()
        self.assertEqual(self.session._load()["refresh_token"], "refresh-old")



class OAuthLoginTests(unittest.TestCase):
    def test_browser_callback_pkce_and_registration(self):
        import base64
        import hashlib
        import io
        from urllib.parse import parse_qs, urlencode, urlsplit
        with tempfile.TemporaryDirectory() as directory:
            session = ChatGPTSession(directory)
            captured = {}

            def browser(url):
                captured.update(parse_qs(urlsplit(url).query))

            def server_factory(address, handler_class):
                server = MagicMock()
                server.server_port = 54321
                server.__enter__.return_value = server

                def callback():
                    handler = object.__new__(handler_class)
                    handler.path = "/auth/callback?" + urlencode(dict(
                        state=captured["state"][0], code="code", client_id="issued"))
                    handler.send_response = MagicMock()
                    handler.send_header = MagicMock()
                    handler.end_headers = MagicMock()
                    handler.wfile = io.BytesIO()
                    handler.do_GET()
                server.handle_request.side_effect = callback
                return server

            tokens = dict(access_token="access", refresh_token="refresh", id_token="id",
                          token_type="Bearer", expires_in=3600, scope=" ".join(REQUIRED_SCOPES))
            with patch("ChatGPTAuth.HTTPServer", side_effect=server_factory), \
                 patch("ChatGPTAuth.webbrowser.open", side_effect=browser), \
                 patch("ChatGPTAuth.request_json", return_value=tokens) as request, \
                 patch.object(session, "_validate_identity", return_value={"sub": "user"}) as validate, \
                 patch("builtins.print"):
                session.login()
            exchange = request.call_args.args[1]
            challenge = base64.urlsafe_b64encode(hashlib.sha256(exchange["code_verifier"].encode()).digest()).rstrip(b"=").decode()
            self.assertEqual(captured["code_challenge"], [challenge])
            self.assertEqual(exchange["client_id"], "issued")
            self.assertEqual(exchange["redirect_uri"], captured["redirect_uri"][0])
            validate.assert_called_once_with("id", "issued", captured["nonce"][0])
            self.assertEqual(session._load()["subject"], "user")

    def test_id_token_signature_audience_and_nonce(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        claims = dict(iss="https://auth.openai.com", aud="issued", sub="user", nonce="nonce",
                      iat=int(time.time()), exp=int(time.time()) + 300)
        discovery = {"issuer": "https://auth.openai.com", "jwks_uri": "https://auth.openai.com/.well-known/jwks.json"}
        with patch("ChatGPTAuth.request_json", return_value=discovery), \
             patch("jwt.PyJWKClient") as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value.key = key.public_key()
            token = jwt.encode(claims, key, algorithm="RS256")
            self.assertEqual(ChatGPTSession._validate_identity(token, "issued", "nonce")["sub"], "user")
            with self.assertRaises(RuntimeError):
                ChatGPTSession._validate_identity(token, "issued", "wrong")
            with self.assertRaises(jwt.InvalidAudienceError):
                ChatGPTSession._validate_identity(token, "other", "nonce")
            other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            with self.assertRaises(jwt.InvalidSignatureError):
                ChatGPTSession._validate_identity(jwt.encode(claims, other_key, algorithm="RS256"), "issued", "nonce")


if __name__ == "__main__":
    unittest.main()
