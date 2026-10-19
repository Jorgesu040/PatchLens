"""Una sesión local de ChatGPT para desarrollo; ejecutar un proceso a la vez."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid
import webbrowser

RESOURCE = "https://api.openai.com/v1"
ISSUER = "https://auth.openai.com"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
REQUIRED_SCOPES = {"resource.invoke", "chatgpt.tokens.use.direct"}


def request_json(url, fields=None):
    data = urlencode(fields).encode() if fields is not None else None
    headers = {"Content-Type": "application/x-www-form-urlencoded"} if data else {}
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else {}


class ChatGPTSession:
    def __init__(self, directory=None):
        self.directory = Path(directory or Path(__file__).resolve().parent / ".patchlens-auth")
        self.path = self.directory / "default.json"

    def _load(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _save(self, record):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump(record, output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _tokens(self, record, tokens):
        scopes = tokens.get("scope")
        scopes = scopes.split() if scopes is not None else record.get("scopes", [])
        if not REQUIRED_SCOPES.issubset(scopes):
            raise RuntimeError("No se autorizó el uso del plan de ChatGPT para PatchLens.")
        if not tokens.get("access_token") or tokens.get("token_type", "").lower() != "bearer":
            raise RuntimeError("La respuesta OAuth no contiene un token Bearer válido.")
        credentials = {key: tokens[key] for key in ("access_token", "refresh_token", "id_token") if key in tokens}
        return record | credentials | dict(scopes=scopes, expires_at=time.time() + float(tokens["expires_in"]))

    def login(self, timeout=180, open_browser=True):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        record = self._load()
        host_file = self.directory / "host.json"
        if host_file.exists():
            host = json.loads(host_file.read_text())["id"]
        else:
            host = "urn:uuid:" + str(uuid.uuid4())
            fd = os.open(host_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump({"id": host}, output)
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        callback = {}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # Callback URLs contain credentials.

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                if parsed.path != "/auth/callback" or query.get("state") != [state]:
                    self.send_error(400, "Invalid OAuth callback")
                    return
                if any(len(values) != 1 for values in query.values()):
                    self.send_error(400, "Duplicate OAuth parameters")
                    return
                callback.update({k: v[0] for k, v in query.items()})
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b"Puedes volver a PatchLens.")

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            server.timeout = 1
            redirect = f"http://127.0.0.1:{server.server_port}/auth/callback"
            client_id = record.get("client_id", "dynamic_agent_client")
            params = dict(client_id=client_id, ext_agent_host_id=host,
                          response_type="code", redirect_uri=redirect,
                          scope="openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
                          resource=RESOURCE, state=state, nonce=nonce,
                          code_challenge_method="S256", code_challenge=challenge)
            if client_id == "dynamic_agent_client":
                params["agent_name_hint"] = "PatchLens"
            # No id_token_hint in the URL printed to the terminal.
            url = ISSUER + "/api/accounts/authorize?" + urlencode(params)
            print("Continue with ChatGPT — abre esta URL para autorizar PatchLens:\n" + url)
            if open_browser:
                webbrowser.open(url)
            deadline = time.monotonic() + timeout
            while not callback and time.monotonic() < deadline:
                server.handle_request()
        if not callback:
            raise TimeoutError("Se agotó el tiempo para iniciar sesión.")
        if callback.get("error"):
            raise RuntimeError("El inicio de sesión no fue autorizado.")
        issued = callback.get("client_id", client_id)
        if not issued or issued == "dynamic_agent_client" or (client_id != "dynamic_agent_client" and issued != client_id):
            raise RuntimeError("El callback contiene un client_id inválido.")
        if not callback.get("code"):
            raise RuntimeError("El callback no contiene un código OAuth.")
        tokens = request_json(TOKEN_URL, dict(grant_type="authorization_code", client_id=issued,
                              code=callback["code"], code_verifier=verifier,
                              redirect_uri=redirect, resource=RESOURCE))
        claims = self._validate_identity(tokens["id_token"], issued, nonce)
        if record.get("subject") and record["subject"] != claims["sub"]:
            raise RuntimeError("La cuenta no coincide con la sesión guardada.")
        record.update(client_id=issued, subject=claims["sub"])
        self._save(self._tokens(record, tokens))

    @staticmethod
    def _validate_identity(token, client_id, nonce):
        import jwt
        discovery = request_json(ISSUER + "/.well-known/openid-configuration")
        if discovery["issuer"] != ISSUER or not discovery["jwks_uri"].startswith(ISSUER + "/"):
            raise RuntimeError("Configuración OIDC inesperada.")
        key = jwt.PyJWKClient(discovery["jwks_uri"]).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256"], audience=client_id,
                            issuer=ISSUER, options={"require": ["exp", "iat", "sub", "nonce"]})
        if claims["nonce"] != nonce or not claims["sub"]:
            raise RuntimeError("La identidad OAuth no es válida.")
        return claims

    def access_token(self):
        record = self._load()
        if not record.get("access_token"):
            raise RuntimeError("Inicia sesión primero: python AI.py login")
        if record.get("expires_at", 0) <= time.time() + 60:
            if not record.get("refresh_token"):
                raise RuntimeError("La sesión ha caducado. Ejecuta python AI.py login.")
            tokens = request_json(TOKEN_URL, dict(grant_type="refresh_token", client_id=record["client_id"],
                                  refresh_token=record["refresh_token"], resource=RESOURCE))
            record = self._tokens(record, tokens)
            self._save(record)
        return record["access_token"]

    def logout(self):
        record = self._load()
        if record.get("refresh_token"):
            discovery = request_json(ISSUER + "/.well-known/openid-configuration")
            endpoint = discovery["revocation_endpoint"]
            if not endpoint.startswith(ISSUER + "/"):
                raise RuntimeError("Endpoint de revocación inesperado.")
            request_json(endpoint, dict(token=record["refresh_token"], token_type_hint="refresh_token",
                                       client_id=record["client_id"]))
        for field in ("access_token", "refresh_token", "id_token", "expires_at", "scopes"):
            record.pop(field, None)
        self._save(record)
