import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai.types.responses import Response, ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

from AIAdapters import ResponsesAdapter


class AgentToolTests(unittest.TestCase):
    def adapter(self, responses):
        with patch("AIAdapters.OpenAI"):
            adapter = ResponsesAdapter("test-model", lambda: "test-key")
        adapter.client.responses.create.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=iter([
                SimpleNamespace(type=f"response.{response.status}", response=response)
            ])))
            for response in responses
        ]
        return adapter

    @staticmethod
    def response(output):
        return Response.model_construct(output=output, error=None, status="completed")

    @staticmethod
    def final_message():
        return ResponseOutputMessage(
            id="message", type="message", role="assistant", status="completed", phase="final_answer",
            content=[ResponseOutputText(type="output_text", text="Conclusión", annotations=[])],
        )

    @staticmethod
    def function_call(call_id="call_1"):
        return ResponseFunctionToolCall(
            type="function_call", name="get_function", arguments='{"address": "0x401000"}', call_id=call_id
        )

    def test_tool_result_is_added_to_the_next_agent_turn(self):
        call = self.function_call()
        adapter = self.adapter([self.response([call]), self.response([self.final_message()])])
        with patch.object(adapter, "make_tool_call", return_value={"name": "validate_input"}):
            result = adapter.agent_loop("analiza", "instrucciones", [], 2)

        self.assertEqual(result["stop_reason"], "completed")
        outputs = [item for item in result["history"] if item.get("type") == "function_call_output"]
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["call_id"], "call_1")
        self.assertEqual(json.loads(outputs[0]["output"]), {
            "call_result": "success", "name": "validate_input",
        })
        second_request = adapter.client.responses.create.call_args_list[1].kwargs["input"]
        self.assertIn(outputs[0], second_request)

    def test_iteration_limit_prevents_an_unbounded_loop(self):
        call = self.function_call()
        adapter = self.adapter([self.response([call])])
        with patch.object(adapter, "make_tool_call", return_value={"name": "validate_input"}):
            result = adapter.agent_loop("analiza", "instrucciones", [], 1)

        self.assertEqual(result["stop_reason"], "max_iterations_reached")
        self.assertEqual(adapter.client.responses.create.call_count, 1)

    def test_missing_function_returns_error_and_continues_pending_calls(self):
        adapter = self.adapter([
            self.response([self.function_call("missing"), self.function_call("valid")]),
            self.response([self.final_message()]),
        ])
        with patch.object(adapter, "make_tool_call", side_effect=[
            FileNotFoundError("Function not found"), {"name": "validate_input"},
        ]):
            result = adapter.agent_loop("analiza", "instrucciones", [], 2)

        self.assertEqual(result["stop_reason"], "completed")
        error_log = next(log for log in adapter.logs if log.get("call_id") == "missing")
        self.assertEqual(error_log["tool"], "get_function")
        outputs = [item for item in result["history"] if item.get("type") == "function_call_output"]
        self.assertEqual([item["call_id"] for item in outputs], ["missing", "valid"])
        self.assertEqual(json.loads(outputs[0]["output"]), {
            "call_result": "error", "message": "Function not found",
        })
        self.assertEqual(json.loads(outputs[1]["output"])["call_result"], "success")
        second_request = adapter.client.responses.create.call_args_list[1].kwargs["input"]
        for output in outputs:
            self.assertIn(output, second_request)

    def test_lists_and_scalar_results_have_one_success_envelope(self):
        for value in ([{"name": "example"}], [], "text", True, False, None):
            with self.subTest(value=value):
                adapter = self.adapter([self.response([self.function_call()])])
                with patch.object(adapter, "make_tool_call", return_value=value):
                    result = adapter.agent_loop("analiza", "instrucciones", [], 1)
                output = next(item for item in result["history"] if item.get("type") == "function_call_output")
                self.assertEqual(json.loads(output["output"]), {
                    "call_result": "success", "result": value,
                })

    def test_serialization_errors_are_returned_to_the_agent(self):
        adapter = self.adapter([self.response([self.function_call()])])
        with patch.object(adapter, "make_tool_call", return_value=object()):
            result = adapter.agent_loop("analiza", "instrucciones", [], 1)
        output = next(item for item in result["history"] if item.get("type") == "function_call_output")
        error = json.loads(output["output"])
        self.assertEqual(error["call_result"], "error")
        self.assertIn("not JSON serializable", error["message"])
