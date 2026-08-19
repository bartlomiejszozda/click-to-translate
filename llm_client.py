import os
from functools import lru_cache
from typing import Literal, Mapping, Sequence, TypedDict

from openai import OpenAI


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TARGET_LANGUAGE = "English"

ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str


class LLMResponseError(RuntimeError):
    """Raised when the model response does not contain usable text."""


def get_model_name() -> str:
    return os.getenv("MODEL", DEFAULT_MODEL)


def get_api_key() -> str:
    key = (os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "No API key found. Set API_KEY (or OPENAI_API_KEY) in "
            "~/.config/translator/.env and restart the container so docker "
            "reads the file again."
        )
    return key


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(
        api_key=get_api_key(),
        base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
    )


def recent_chat_messages(
    chat_messages: Sequence[Mapping[str, object]] | None,
    limit: int,
) -> list[ChatMessage]:
    """Return recent valid user/assistant messages in their original order."""
    recent_messages: list[ChatMessage] = []
    for message in (chat_messages or [])[-limit:]:
        role = message.get("role")
        content = message.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            recent_messages.append({"role": role, "content": content})
    return recent_messages


def complete_chat(messages: Sequence[ChatMessage]) -> str:
    response = get_client().chat.completions.create(
        model=get_model_name(),
        messages=list(messages),
    )
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMResponseError("The model returned no response choice.") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("The model returned an empty text response.")
    return content
