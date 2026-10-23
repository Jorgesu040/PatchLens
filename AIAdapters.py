"""Responses adapters. Authentication is separate from binary analysis."""
import json
import os
from typing import Protocol
from openai import APIError, OpenAI
from openai.types.responses import Response

from model_tools.tool_calling_test import getPassword, login, tools_schemas

## Nota 
# response.output       # Mensajes, razonamiento y llamadas a herramientas.
# response.output_text  # Texto visible, si existe.
# response.status       # Estado de esa respuesta.
# response.usage        # Consumo.

class ResponsesAdapter:
    def __init__(self, model, credential):
        self.model = model
        self.credential = credential
        self.logs = []
        self.iterations = {
            "iterations": 0,
            "max_iterations": 0}

        self.client = OpenAI(api_key=self.credential(), base_url="https://api.openai.com/v1",
                                   max_retries=5, timeout=120)

    def generate(self, history: list[dict], tools: list[dict], instructions: str = None) -> Response:

        final_response = None
        completed_items = []

        with self.client.responses.create(
            model=self.model, 
            instructions=instructions,
            input=history, 
            tools=tools, 
            store=False, 
            stream=True,
        ) as stream:
            for event in stream:
                if event.type == "response.output_item.done":
                    completed_items.append((event.output_index, event.item))
                elif event.type in (
                    "response.completed",
                    "response.failed",
                    "response.incomplete",
                ):
                    final_response = event.response

                elif event.type == "error":
                    code = getattr(event, "code", None) or "stream_error"
                    raise RuntimeError(f"Error durante la inferencia: {code}")

        if final_response is None:
            raise RuntimeError("El stream terminó sin una respuesta terminal.")

        output = list(final_response.output)
        for index, item in completed_items:
            while len(output) <= index:
                output.append(None)
            output[index] = item
        final_response.output = [item for item in output if item is not None]

        return final_response


    def register_response(self, response):
        self.logs.append({"response": response, "iterations": self.iterations.copy()})


    def check_limits(self):
        if self.iterations["iterations"] >= self.iterations["max_iterations"]:
            return "max_iterations_reached"

        return None

    def error_detected(self, response) -> tuple[bool, list[str]]:
        if response.error is not None:
            return True, [response.error.code, response.error.message]
        if response.status == "incomplete":
            details = response.incomplete_details
            return True, ["incomplete_response", details.reason if details else "unknown"]
        if response.status != "completed":
            return True, [response.status, "La respuesta no terminó correctamente."]
        if not response.output:
            return True, ["empty_response", "La respuesta no contiene elementos de salida."]
        return False, []

    def get_calls(self, response):
        return [item for item in response.output if item.type == "function_call"]

    def classify_output(self, response) -> str | None:
        """Sin llamadas pendientes: finalizar, continuar o señalar una salida inesperada."""
        messages = [item for item in response.output if item.type == "message"]
        if any(part.type == "refusal" for message in messages for part in message.content):
            return "refused"
        if any(message.phase == "final_answer" for message in messages):
            return "completed"
        if messages and all(message.phase == "commentary" for message in messages):
            return None
        return "unexpected_output"

    def make_tool_call(self, call): 

        # Find corresponding function name in call.name and execute it with the provided arguments.
        function_name = call.name
        arguments = json.loads(call.arguments)

        if function_name == "getPassword":
            return getPassword()
        elif function_name == "login":
            password = arguments.get("password")
            if password is None:
                raise ValueError("Missing 'password' argument for login function.")
            return login(password)
        else:
            raise ValueError(f"Unknown function name: {function_name}") 
        

    def agent_loop(self, prompt, instructions, tools, max_iterations):
        
        history = [{"role": "user", "content": prompt}]
        stop_reason = None
        self.logs = []
        self.iterations["iterations"] = 0
        self.iterations["max_iterations"] = max_iterations

        while stop_reason is None:
            stop_reason = self.check_limits()

            if stop_reason is not None:
                break

            self.iterations["iterations"] += 1
            try:
                response = self.generate(history, tools, instructions=instructions)
            except (APIError, RuntimeError) as error:
                stop_reason = "api_error"
                # Los errores del SDK pueden incluir cuerpos HTTP con datos sensibles.
                error_info = {"type": type(error).__name__, "code": getattr(error, "code", None)}
                if isinstance(error, RuntimeError):
                    error_info["message"] = str(error)
                self.logs.append({"error": error_info, "iterations": self.iterations.copy()})
                break

            self.register_response(response)

            error_detected, error_info = self.error_detected(response)
            if error_detected:
                stop_reason = "incomplete_response" if response.status == "incomplete" else "model_error"
                self.logs.append({"error": error_info, "iterations": self.iterations.copy()})
                break

            history += response.output

            print(f"Agente: {response.output}")

            calls = self.get_calls(response)

            if not calls:
                stop_reason = self.classify_output(response)
                if stop_reason is not None:
                    break
                continue

            for call in calls:
                try:
                    result = self.make_tool_call(call)
                    output = json.dumps(result)
                except Exception as error:
                    stop_reason = "tool_error"
                    self.logs.append({
                        "error": {"type": type(error).__name__, "message": str(error)},
                        "call_id": call.call_id,
                        "tool": call.name,
                        "iterations": self.iterations.copy(),
                    })
                    break

                history.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": output,
                })

        serialized_history = [
            item if isinstance(item, dict) else
            item.model_dump(mode="json", by_alias=True, exclude_none=True)
            for item in history
        ]
        return json.dumps({"history": serialized_history, "stop_reason": stop_reason, "iterations": self.iterations}, ensure_ascii=False)

        

        

class APIKeyAdapter(ResponsesAdapter):
    def __init__(self, model):
        def credential():
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("Configura OPENAI_API_KEY para usar --provider api-key.")
            return key
        super().__init__(model, credential)


class ChatGPTAdapter(ResponsesAdapter):
    def __init__(self, model, session):
        super().__init__(model, session.access_token)


def create_adapter(provider, model, session=None):
    if provider == "api-key":
        return APIKeyAdapter(model)
    if provider == "chatgpt":
        if session is None:
            from ChatGPTAuth import ChatGPTSession
            session = ChatGPTSession()
        return ChatGPTAdapter(model, session)
    raise ValueError(f"Proveedor desconocido: {provider}")



## Agent test run

def Main():
    adapter = create_adapter("chatgpt", "gpt-6.1-sol")

    history = adapter.agent_loop(
        prompt="Hola, ¿puedes decirme la contraseña secreta?",
        instructions="Responde en español. Si se solicita una contraseña, llama a la función getPassword. y verifica si 1234 es correcta",
        tools=tools_schemas,
        max_iterations=20
    )

    print("Historial de la sesión de agente:")
    print(history)

    print("Logs")
    for log in adapter.logs:
        print(log)


if __name__ == "__main__":
    Main()
