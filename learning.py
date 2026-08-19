from typing import Mapping, Sequence

from llm_client import (
    DEFAULT_TARGET_LANGUAGE,
    ChatMessage,
    complete_chat,
    recent_chat_messages,
)
from prompt_loader import render_prompt


def _normalized_target_language(target_language: str) -> str:
    return target_language.strip() or DEFAULT_TARGET_LANGUAGE


def generate_learning_suggestions(
    source_text: str,
    translated_text: str,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
) -> str:
    source_text = source_text.strip()
    translated_text = translated_text.strip()
    if not source_text or not translated_text:
        return ""

    prompt = render_prompt(
        "learning_suggestions",
        source_text=source_text,
        translated_text=translated_text,
        target_language=_normalized_target_language(target_language),
    )
    messages: list[ChatMessage] = [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": prompt.user or ""},
    ]
    return complete_chat(messages)


def continue_learning_chat(
    source_text: str,
    translated_text: str,
    learning_suggestions: str,
    user_message: str,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
    chat_messages: Sequence[Mapping[str, object]] | None = None,
) -> str:
    question = user_message.strip()
    if not question:
        return ""

    prompt = render_prompt(
        "learning_chat",
        source_text=source_text.strip(),
        translated_text=translated_text.strip(),
        learning_suggestions=learning_suggestions.strip(),
        target_language=_normalized_target_language(target_language),
    )
    messages: list[ChatMessage] = [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": prompt.user or ""},
    ]
    messages.extend(recent_chat_messages(chat_messages, limit=20))
    messages.append({"role": "user", "content": question})
    return complete_chat(messages)
