"""Responses adapters. Authentication is separate from binary analysis."""
import os
from typing import Protocol


class InferenceAdapter(Protocol):
    def generate(self, prompt: str, instructions: str) -> str: ...


class ResponsesAdapter:
    def __init__(self, model, credential):
        self.model = model
        self.credential = credential

    def generate(self, prompt, instructions):
        from openai import OpenAI

        # Explicit endpoint prevents environment overrides from receiving credentials.
        with OpenAI(api_key=self.credential(), base_url="https://api.openai.com/v1",
                    max_retries=0, timeout=120) as client:
            parts = []
            completed = False
            with client.responses.create(
                model=self.model, instructions=instructions,
                input=[{"role": "user", "content": prompt}], store=False, stream=True,
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        parts.append(event.delta)
                    elif event.type in ("response.failed", "response.incomplete", "error"):
                        # Never return a partial report as successful.
                        code = getattr(event, "code", None)
                        response = getattr(event, "response", None)
                        error = getattr(response, "error", None)
                        code = code or getattr(error, "code", None) or event.type
                        raise RuntimeError(f"La inferencia no terminó: {code}")
                    elif event.type == "response.completed":
                        completed = True
            if not completed or not parts:
                raise RuntimeError("No se recibió una respuesta de texto completa.")
            return "".join(parts)


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
