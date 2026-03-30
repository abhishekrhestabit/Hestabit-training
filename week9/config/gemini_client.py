from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from itertools import count
from typing import Any

from pydantic import BaseModel

from autogen_core import FunctionCall

_THOUGHT_SIGNATURE_DELIMITER = "::ts::"
_THOUGHT_SIGNATURES: dict[str, bytes] = {}
_THOUGHT_SIGNATURE_COUNTER = count(1)


class _SerializableUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _encode_call_id(call_id: str, thought_signature: bytes | None) -> str:
    if not thought_signature:
        return call_id

    signature_ref = f"sig{next(_THOUGHT_SIGNATURE_COUNTER)}"
    _THOUGHT_SIGNATURES[signature_ref] = thought_signature
    return f"{call_id}{_THOUGHT_SIGNATURE_DELIMITER}{signature_ref}"


def _decode_call_id(call_id: str) -> tuple[str, bytes | None]:
    if _THOUGHT_SIGNATURE_DELIMITER not in call_id:
        return call_id, None

    raw_call_id, signature_ref = call_id.split(_THOUGHT_SIGNATURE_DELIMITER, maxsplit=1)
    return raw_call_id, _THOUGHT_SIGNATURES.get(signature_ref)


def _patch_semantic_kernel_serialization() -> None:
    from autogen_ext.models.semantic_kernel import _sk_chat_completion_adapter as sk_adapter

    if getattr(sk_adapter, "_week9_safe_serialization_patch", False):
        return

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
            raw_data = data.model_dump()
            normalized = json.dumps(raw_data, default=_json_default)
            return type(data)(**json.loads(normalized))

    sk_adapter.ensure_serializable = _ensure_serializable
    sk_adapter._week9_safe_serialization_patch = True


def _patch_gemini_thought_signatures() -> None:
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

    if getattr(sk_adapter, "_week9_gemini_thought_signature_patch", False):
        return

    original_create_chat_message_content = GoogleAIChatCompletion._create_chat_message_content
    original_create_streaming_chat_message_content = GoogleAIChatCompletion._create_streaming_chat_message_content

    def _attach_thought_signature_metadata(message: Any, candidate: Any) -> Any:
        if not candidate.content or not candidate.content.parts:
            return message

        parts_by_id: dict[str, Any] = {}
        for idx, part in enumerate(candidate.content.parts):
            if part.function_call:
                parts_by_id[f"{part.function_call.name}_{idx}"] = part

        for item in getattr(message, "items", []):
            if not isinstance(item, FunctionCallContent) or item.id not in parts_by_id:
                continue

            part = parts_by_id[item.id]
            metadata = dict(item.metadata)
            if getattr(part, "thought_signature", None):
                metadata["thought_signature"] = base64.urlsafe_b64encode(part.thought_signature).decode("ascii")
            if getattr(part, "thought", None) is not None:
                metadata["thought"] = part.thought
            item.metadata = metadata

        return message

    def _patched_create_chat_message_content(self: Any, response: Any, candidate: Any) -> Any:
        message = original_create_chat_message_content(self, response, candidate)
        return _attach_thought_signature_metadata(message, candidate)

    def _patched_create_streaming_chat_message_content(
        self: Any,
        chunk: Any,
        candidate: Any,
        function_invoke_attempt: int = 0,
    ) -> Any:
        message = original_create_streaming_chat_message_content(
            self,
            chunk,
            candidate,
            function_invoke_attempt=function_invoke_attempt,
        )
        return _attach_thought_signature_metadata(message, candidate)

    def _patched_process_tool_calls(self: Any, result: Any) -> list[FunctionCall]:
        function_calls: list[FunctionCall] = []
        for item in result.items:
            if not isinstance(item, FunctionCallContent):
                continue

            if item.id is None:
                raise ValueError("Function call ID is required")

            plugin_name = item.plugin_name or ""
            function_name = item.function_name
            full_name = f"{plugin_name}-{function_name}" if plugin_name else function_name
            arguments = json.dumps(item.arguments) if isinstance(item.arguments, Mapping) else item.arguments or "{}"

            metadata = item.metadata or {}
            thought_signature = (
                base64.urlsafe_b64decode(metadata["thought_signature"].encode("ascii"))
                if metadata.get("thought_signature")
                else None
            )
            function_calls.append(
                FunctionCall(
                    id=_encode_call_id(item.id, thought_signature),
                    name=full_name,
                    arguments=arguments,
                )
            )

        return function_calls

    def _patched_format_assistant_message(message: Any) -> list[Part]:
        parts: list[Part] = []
        for item in message.items:
            if isinstance(item, TextContent):
                if item.text:
                    parts.append(Part.from_text(text=item.text))
                continue

            if isinstance(item, FunctionCallContent):
                raw_call_id, thought_signature = _decode_call_id(item.id or "")
                arguments = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                metadata = item.metadata or {}
                function_call = GoogleFunctionCall(id=raw_call_id or None, name=item.name, args=arguments)

                if thought_signature is not None or metadata.get("thought") is not None:
                    parts.append(
                        Part(
                            function_call=function_call,
                            thought_signature=thought_signature,
                            thought=metadata.get("thought"),
                        )
                    )
                else:
                    parts.append(Part(function_call=function_call))
                continue

            raise ServiceInvalidRequestError(
                "Unsupported item type in Assistant message while formatting chat history for Google AI"
                f" Inference: {type(item)}"
            )

        return parts

    GoogleAIChatCompletion._create_chat_message_content = _patched_create_chat_message_content
    GoogleAIChatCompletion._create_streaming_chat_message_content = _patched_create_streaming_chat_message_content
    sk_adapter.SKChatCompletionAdapter._process_tool_calls = _patched_process_tool_calls
    google_utils.format_assistant_message = _patched_format_assistant_message
    google_chat_module.format_assistant_message = _patched_format_assistant_message
    sk_adapter._week9_gemini_thought_signature_patch = True


def _patch_gemini_usage_metadata() -> None:
    from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion

    if getattr(GoogleAIChatCompletion, "_week9_usage_metadata_patch", False):
        return

    def _normalize_usage(message: Any) -> Any:
        metadata = getattr(message, "metadata", None)
        if not metadata or "usage" not in metadata:
            return message

        usage = metadata["usage"]
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", None)
        metadata["usage"] = _SerializableUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens if total_tokens is not None else prompt_tokens + completion_tokens,
        )
        return message

    original_get_chat_message_contents = GoogleAIChatCompletion.get_chat_message_contents
    original_get_streaming_chat_message_contents = GoogleAIChatCompletion.get_streaming_chat_message_contents

    async def _patched_get_chat_message_contents(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = await original_get_chat_message_contents(self, *args, **kwargs)
        return [_normalize_usage(message) for message in result]

    async def _patched_get_streaming_chat_message_contents(self: Any, *args: Any, **kwargs: Any) -> Any:
        async for batch in original_get_streaming_chat_message_contents(self, *args, **kwargs):
            yield [_normalize_usage(message) for message in batch]

    GoogleAIChatCompletion.get_chat_message_contents = _patched_get_chat_message_contents
    GoogleAIChatCompletion.get_streaming_chat_message_contents = _patched_get_streaming_chat_message_contents
    GoogleAIChatCompletion._week9_usage_metadata_patch = True


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
            "Gemini tool calling requires the Semantic Kernel Google connector. "
            "Install the updated requirements or switch MODEL_PROVIDER to groq or ollama."
        ) from exc

    _patch_semantic_kernel_serialization()
    _patch_gemini_thought_signatures()

    prompt_settings_kwargs: dict[str, Any] = {}
    if "temperature" in overrides:
        prompt_settings_kwargs["temperature"] = overrides["temperature"]

    sk_client = GoogleAIChatCompletion(
        gemini_model_id=settings["model"],
        api_key=settings["api_key"],
    )
    _patch_gemini_usage_metadata()

    return SKChatCompletionAdapter(
        sk_client,
        kernel=Kernel(memory=NullMemory()),
        prompt_settings=GoogleAIChatPromptExecutionSettings(**prompt_settings_kwargs),
        model_info=model_info,
    )
