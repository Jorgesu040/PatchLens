import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai.types.responses import Response, ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

from AIAdapters import ResponsesAdapter
from model_tools import companion_set
from model_tools.schema_tools import tools_schemas
from model_tools.schema_tools.companion_set_schemas import tools_schemas as companion_schemas


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

    def test_companion_calls_are_dispatched_and_returned_to_the_next_turn(self):
        arguments = {
            "get_disassembly": {"version": "old", "address": "00101000", "instruction_count": 3},
            "read_data": {"version": "new", "address": "00102000"},
            "read_memory": {"version": "new", "address": "00102000", "size": 16},
            "list_memory_blocks": {"version": "old"},
            "list_data_items": {"version": "new", "block_name": ".rodata", "offset": 0, "limit": 25},
            "list_exports": {"version": "new"},
        }
        for name, args in arguments.items():
            with self.subTest(name=name):
                call = ResponseFunctionToolCall(
                    type="function_call", name=name, arguments=json.dumps(args), call_id="companion",
                )
                adapter = self.adapter([self.response([call]), self.response([self.final_message()])])
                with patch.object(companion_set, name, return_value=["evidence"]) as function:
                    result = adapter.agent_loop("analiza", "instrucciones", tools_schemas, 2)
                function.assert_called_once_with(**args)
                self.assertEqual(result["stop_reason"], "completed")
                requests = adapter.client.responses.create.call_args_list
                self.assertEqual(requests[0].kwargs["tools"], tools_schemas)
                output = next(item for item in requests[1].kwargs["input"]
                              if isinstance(item, dict) and item.get("type") == "function_call_output")
                self.assertEqual(output["call_id"], "companion")
                self.assertEqual(json.loads(output["output"]), {
                    "call_result": "success", "result": ["evidence"],
                })

    def test_companion_schemas_match_signatures_and_strict_requirements(self):
        import inspect

        names = [schema["name"] for schema in tools_schemas]
        self.assertEqual(len(names), 16)
        self.assertEqual(len(names), len(set(names)))
        for schema in companion_schemas:
            with self.subTest(name=schema["name"]):
                self.assertEqual(schema["type"], "function")
                self.assertTrue(schema["strict"])
                parameters = schema["parameters"]
                self.assertFalse(parameters["additionalProperties"])
                self.assertEqual(set(parameters["required"]), set(parameters["properties"]))
                signature = inspect.signature(getattr(companion_set, schema["name"]))
                self.assertEqual(set(parameters["properties"]), set(signature.parameters))
