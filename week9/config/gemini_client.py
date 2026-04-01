from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from autogen_core import FunctionCall

_DELIM = "::ts::"
_PATCHED = False


class _Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _encode_call_id(call_id: str, sig: bytes | None) -> str:
    if not sig:
        return call_id
    return f"{call_id}{_DELIM}{base64.urlsafe_b64encode(sig).decode('ascii')}"


def _decode_call_id(call_id: str) -> tuple[str, bytes | None]:
    if _DELIM not in call_id:
        return call_id, None
    raw_id, sig_b64 = call_id.split(_DELIM, maxsplit=1)
    return raw_id, base64.urlsafe_b64decode(sig_b64)


def _apply_patches() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from google.genai.types import FunctionCall as GoogleFunctionCall
    from google.genai.types import Part
    from semantic_kernel.connectors.ai.google.google_ai.services import (
        google_ai_chat_completion as google_chat_module,
    )
    from semantic_kernel.connectors.ai.google.google_ai.services import utils as google_utils
    from semantic_kernel.connectors.ai.google.google_ai.services.google_ai_chat_completion import (
        GoogleAIChatCompletion,
    )
    from semantic_kernel.contents import FunctionCallContent, TextContent
    from semantic_kernel.exceptions.service_exceptions import ServiceInvalidRequestError

    from autogen_ext.models.semantic_kernel import _sk_chat_completion_adapter as sk_adapter

    # -- Serialization fix --

    def _json_default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            try:
                return value.model_dump(mode="json")
            except TypeError:
                return value.model_dump()
        if hasattr(value, "__dict__"):
            return vars(value)
        if isinstance(value, (set, tuple)):
            return list(value)
        return str(value)

    def _ensure_serializable(data: BaseModel) -> BaseModel:
        try:
            json.dumps(data.model_dump(mode="json"))
            return data
        except Exception:
            raw = json.dumps(data.model_dump(), default=_json_default)
            return type(data)(**json.loads(raw))

    sk_adapter.ensure_serializable = _ensure_serializable

    # -- Thought signature handling --

    orig_create = GoogleAIChatCompletion._create_chat_message_content
    orig_create_stream = GoogleAIChatCompletion._create_streaming_chat_message_content

    def _attach_thought_meta(message: Any, candidate: Any) -> Any:
        if not candidate.content or not candidate.content.parts:
            return message

        parts_by_id: dict[str, Any] = {
            f"{p.function_call.name}_{i}": p
            for i, p in enumerate(candidate.content.parts)
            if p.function_call
        }

        for item in getattr(message, "items", []):
            if not isinstance(item, FunctionCallContent) or item.id not in parts_by_id:
                continue
            part = parts_by_id[item.id]
            md = dict(item.metadata)
            if getattr(part, "thought_signature", None):
                md["thought_signature"] = base64.urlsafe_b64encode(part.thought_signature).decode("ascii")
            if getattr(part, "thought", None) is not None:
                md["thought"] = part.thought
            item.metadata = md

        return message

    def _patched_create(self: Any, response: Any, candidate: Any) -> Any:
        return _attach_thought_meta(orig_create(self, response, candidate), candidate)

    def _patched_create_stream(
        self: Any, chunk: Any, candidate: Any, function_invoke_attempt: int = 0
    ) -> Any:
        msg = orig_create_stream(self, chunk, candidate, function_invoke_attempt=function_invoke_attempt)
        return _attach_thought_meta(msg, candidate)

    def _patched_process_tool_calls(self: Any, result: Any) -> list[FunctionCall]:
        calls: list[FunctionCall] = []
        for item in result.items:
            if not isinstance(item, FunctionCallContent):
                continue
            if item.id is None:
                raise ValueError("Function call ID is required")

            name = f"{item.plugin_name}-{item.function_name}" if item.plugin_name else item.function_name
            args = json.dumps(item.arguments) if isinstance(item.arguments, Mapping) else item.arguments or "{}"

            md = item.metadata or {}
            sig = (
                base64.urlsafe_b64decode(md["thought_signature"].encode("ascii"))
                if md.get("thought_signature")
                else None
            )
            calls.append(FunctionCall(id=_encode_call_id(item.id, sig), name=name, arguments=args))

        return calls

    def _patched_format_assistant(message: Any) -> list[Part]:
        parts: list[Part] = []
        for item in message.items:
            if isinstance(item, TextContent):
                if item.text:
                    parts.append(Part.from_text(text=item.text))
                continue

            if isinstance(item, FunctionCallContent):
                raw_id, sig = _decode_call_id(item.id or "")
                args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                fc = GoogleFunctionCall(id=raw_id or None, name=item.name, args=args)
                md = item.metadata or {}

                if sig is not None or md.get("thought") is not None:
                    parts.append(Part(function_call=fc, thought_signature=sig, thought=md.get("thought")))
                else:
                    parts.append(Part(function_call=fc))
                continue

            raise ServiceInvalidRequestError(
                f"Unsupported item type in Assistant message: {type(item)}"
            )

        return parts

    GoogleAIChatCompletion._create_chat_message_content = _patched_create
    GoogleAIChatCompletion._create_streaming_chat_message_content = _patched_create_stream
    sk_adapter.SKChatCompletionAdapter._process_tool_calls = _patched_process_tool_calls
    google_utils.format_assistant_message = _patched_format_assistant
    google_chat_module.format_assistant_message = _patched_format_assistant

    # -- Usage metadata fix --

    orig_get = GoogleAIChatCompletion.get_chat_message_contents
    orig_get_stream = GoogleAIChatCompletion.get_streaming_chat_message_contents

    def _fix_usage(message: Any) -> Any:
        md = getattr(message, "metadata", None)
        if not md or "usage" not in md:
            return message
        u = md["usage"]
        prompt = getattr(u, "prompt_tokens", 0) or 0
        completion = getattr(u, "completion_tokens", 0) or 0
        total = getattr(u, "total_tokens", None)
        md["usage"] = _Usage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total if total is not None else prompt + completion,
        )
        return message

    async def _patched_get(self: Any, *args: Any, **kwargs: Any) -> Any:
        return [_fix_usage(m) for m in await orig_get(self, *args, **kwargs)]

    async def _patched_get_stream(self: Any, *args: Any, **kwargs: Any) -> Any:
        async for batch in orig_get_stream(self, *args, **kwargs):
            yield [_fix_usage(m) for m in batch]

    GoogleAIChatCompletion.get_chat_message_contents = _patched_get
    GoogleAIChatCompletion.get_streaming_chat_message_contents = _patched_get_stream

    _PATCHED = True


def build_gemini_client(settings: dict[str, Any], model_info: dict[str, Any], **overrides: Any):
    try:
        from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.google.google_ai import (
            GoogleAIChatCompletion,
            GoogleAIChatPromptExecutionSettings,
        )
        from semantic_kernel.memory.null_memory import NullMemory
    except ImportError as exc:
        raise RuntimeError(
            "Gemini requires the Semantic Kernel Google connector. "
            "Install the updated requirements or switch MODEL_PROVIDER to ollama."
        ) from exc

    _apply_patches()

    prompt_kwargs: dict[str, Any] = {}
    if "temperature" in overrides:
        prompt_kwargs["temperature"] = overrides["temperature"]

    sk_client = GoogleAIChatCompletion(
        gemini_model_id=settings["model"],
        api_key=settings["api_key"],
    )

    return SKChatCompletionAdapter(
        sk_client,
        kernel=Kernel(memory=NullMemory()),
        prompt_settings=GoogleAIChatPromptExecutionSettings(**prompt_kwargs),
        model_info=model_info,
    )
