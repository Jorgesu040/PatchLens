import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai import APIError
from openai.types.responses import (
    Response, ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText,
)

from AIAdapters import ResponsesAdapter
from model_tools.tool_calling_test import tools_schemas


class AgentToolTests(unittest.TestCase):
    def adapter(self, responses):
        with patch("AIAdapters.OpenAI"):
            adapter = ResponsesAdapter("test-model", lambda: "test-key")
        adapter.client.responses.create.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=iter([
                SimpleNamespace(type=f"response.{response.status}", response=response)
            ]))) for response in responses
        ]
        return adapter

    def response(self, output):
        if not output:
            output = [self.message()]
        return Response.model_construct(output=output, error=None, status="completed")

    def message(self, phase="final_answer"):
        return ResponseOutputMessage(
            id="message", type="message", role="assistant", status="completed", phase=phase,
            content=[ResponseOutputText(type="output_text", text="Mensaje de prueba", annotations=[])],
        )

    def test_stream_items_survive_empty_terminal_output(self):
        call = ResponseFunctionToolCall(
            type="function_call", name="getPassword", arguments="{}", call_id="call"
        )
        adapter = self.adapter([self.response([])])
        terminal = Response.model_construct(output=[], error=None, status="completed")
        adapter.client.responses.create.side_effect = None
        adapter.client.responses.create.return_value.__enter__.return_value = iter([
            SimpleNamespace(type="response.output_item.done", output_index=0, item=call),
            SimpleNamespace(type="response.completed", response=terminal),
        ])
        response = adapter.generate([], tools_schemas)
        self.assertEqual(response.output, [call])
        self.assertEqual(adapter.make_tool_call(response.output[0]), "secret_password")

    def test_loop_logs_failed_incomplete_and_empty_responses(self):
        for status, reason in (
            ("failed", "model_error"),
            ("incomplete", "incomplete_response"),
            ("completed", "model_error"),
        ):
            with self.subTest(status=status):
                response = Response.model_construct(
                    output=[], status=status,
                    error=SimpleNamespace(code="server_error", message="Generation failure")
                    if status == "failed" else None,
                    incomplete_details=SimpleNamespace(reason="max_output_tokens")
                    if status == "incomplete" else None,
                )
                adapter = self.adapter([response])
                result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
                self.assertEqual(result["stop_reason"], reason)
                self.assertEqual(result["iterations"]["iterations"], 1)
                self.assertIs(adapter.logs[0]["response"], response)
                self.assertIn("error", adapter.logs[1])
                self.assertEqual(len(result["history"]), 1)
                if status == "incomplete":
                    self.assertIn("max_output_tokens", adapter.logs[1]["error"])
                if status == "failed":
                    self.assertEqual(adapter.logs[1]["error"], ["server_error", "Generation failure"])

    def test_stream_error_and_missing_terminal_are_recorded(self):
        for events in ([], [SimpleNamespace(type="error", code="stream_error")]):
            with self.subTest(events=events):
                adapter = self.adapter([])
                adapter.client.responses.create.side_effect = None
                adapter.client.responses.create.return_value.__enter__.return_value = iter(events)
                result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
                self.assertEqual(result["stop_reason"], "api_error")
                self.assertEqual(adapter.logs[0]["error"]["type"], "RuntimeError")
                self.assertIn("message", adapter.logs[0]["error"])

    def test_tool_errors_keep_call_identity_and_stop_the_batch(self):
        # Una consulta válida puede fallar porque Ghidra no encuentre la función.
        for error in (FileNotFoundError("Function not found"), RuntimeError("Analysis unavailable")):
            with self.subTest(error=type(error).__name__):
                calls = [
                    ResponseFunctionToolCall(
                        type="function_call", name="getPassword", arguments="{}", call_id="failed_call"
                    ),
                    ResponseFunctionToolCall(
                        type="function_call", name="getPassword", arguments="{}", call_id="next_call"
                    ),
                ]
                adapter = self.adapter([self.response(calls)])
                with patch.object(adapter, "make_tool_call", side_effect=error) as execute:
                    result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
                self.assertEqual(result["stop_reason"], "tool_error")
                self.assertEqual(execute.call_count, 1)
                self.assertEqual(adapter.logs[1]["call_id"], "failed_call")
                self.assertEqual(adapter.logs[1]["tool"], "getPassword")
                self.assertEqual(adapter.logs[1]["error"]["type"], type(error).__name__)
                self.assertFalse(any(item.get("type") == "function_call_output" for item in result["history"]))

    def test_failed_request_preserves_previous_history_and_counts_attempt(self):
        call = ResponseFunctionToolCall(
            type="function_call", name="getPassword", arguments="{}", call_id="call"
        )
        adapter = self.adapter([])
        first_stream = MagicMock(__enter__=MagicMock(return_value=iter([
            SimpleNamespace(type="response.completed", response=self.response([call]))
        ])))
        adapter.client.responses.create.side_effect = [
            first_stream, APIError("private HTTP response body", request=MagicMock(), body=None)
        ]
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
        self.assertEqual(result["stop_reason"], "api_error")
        self.assertEqual(result["iterations"]["iterations"], 2)
        self.assertEqual(len(result["history"]), 3)
        self.assertEqual(adapter.logs[0]["iterations"]["iterations"], 1)
        self.assertEqual(adapter.logs[1]["iterations"]["iterations"], 2)
        self.assertEqual(adapter.logs[1]["error"]["type"], "APIError")
        self.assertNotIn("private HTTP response body", str(adapter.logs))

    def test_tool_round_trip_and_final_history_are_serializable(self):
        calls = [ResponseFunctionToolCall(
            type="function_call", name=name, arguments=arguments, call_id=str(index)
        ) for index, (name, arguments) in enumerate([
            ("getPassword", "{}"), ("login", '{"password":"secret_password"}')
        ])]
        adapter = self.adapter([
            self.response([calls[0]]), self.response([calls[1]]), self.response([])
        ])
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
        self.assertEqual(result["stop_reason"], "completed")
        self.assertEqual(result["iterations"]["iterations"], 3)
        outputs = [item for item in result["history"] if item.get("type") == "function_call_output"]
        self.assertEqual([item["call_id"] for item in outputs], [call.call_id for call in calls])
        self.assertEqual([json.loads(item["output"]) for item in outputs], ["secret_password", True])
        for request in adapter.client.responses.create.call_args_list:
            self.assertEqual(request.kwargs["instructions"], "instructions")
            self.assertEqual(request.kwargs["tools"], tools_schemas)

    def test_iteration_limit_and_reset(self):
        calls = [ResponseFunctionToolCall(
            type="function_call", name="getPassword", arguments="{}", call_id=str(index)
        ) for index in range(3)]
        adapter = self.adapter([self.response(calls), self.response([])])
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 1))
        self.assertEqual(result["stop_reason"], "max_iterations_reached")
        self.assertEqual(adapter.client.responses.create.call_count, 1)
        outputs = [item for item in result["history"] if item.get("type") == "function_call_output"]
        self.assertEqual(len(outputs), 3)  # Varias herramientas siguen siendo una ronda.
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 1))
        self.assertEqual(result["stop_reason"], "completed")
        self.assertEqual(result["iterations"]["iterations"], 1)

    def test_commentary_continues_to_tools_and_final_answer(self):
        commentary = self.message("commentary")
        call = ResponseFunctionToolCall(
            type="function_call", name="getPassword", arguments="{}", call_id="call"
        )
        adapter = self.adapter([
            self.response([commentary]), self.response([call]), self.response([]),
        ])
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 3))
        self.assertEqual(result["stop_reason"], "completed")
        self.assertEqual(result["iterations"]["iterations"], 3)
        self.assertEqual(adapter.client.responses.create.call_count, 3)
        self.assertEqual(result["history"][1]["phase"], "commentary")
        self.assertEqual(result["history"][-1]["phase"], "final_answer")

    def test_commentary_only_remains_bounded_by_round_limit(self):
        commentary = self.message("commentary")
        adapter = self.adapter([self.response([commentary]), self.response([commentary])])
        result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 2))
        self.assertEqual(result["stop_reason"], "max_iterations_reached")
        self.assertEqual(result["iterations"]["iterations"], 2)

    def test_final_refusal_and_unknown_output(self):
        refusal = self.message()
        refusal.content = [ResponseOutputRefusal(type="refusal", refusal="No puedo ayudar.")]
        for messages, reason in (
            ([self.message()], "completed"),
            ([self.message("commentary"), self.message()], "completed"),
            ([refusal], "refused"),
            ([self.message(None)], "unexpected_output"),
        ):
            with self.subTest(reason=reason, messages=len(messages)):
                adapter = self.adapter([self.response(messages)])
                result = json.loads(adapter.agent_loop("hello", "instructions", tools_schemas, 5))
                self.assertEqual(result["stop_reason"], reason)
                self.assertEqual(result["iterations"]["iterations"], 1)
