import os

from openai import OpenAI


DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TARGET_LANGUAGE = "English"


def get_model_name() -> str:
    return os.getenv("MODEL", DEFAULT_MODEL)


def _client():
    return OpenAI(
        api_key=os.environ["API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
    )


def _system_prompt(target_language: str) -> str:
    return (
        f"You are a professional translator and editor. Translate the user's text "
        f"to {target_language}. Preserve the original meaning, tone, formatting, "
        f"and technical terms. If the text is already natural {target_language}, "
        f"return it unchanged. If it is already {target_language} but awkward, "
        f"improve grammar, clarity, fluency, and natural tone without changing "
        f"the meaning. Return only the final text."
    )


def translate_text(text: str, target_language: str = DEFAULT_TARGET_LANGUAGE) -> str:
    cleaned_text = text.strip()
    if not cleaned_text:
        return ""

    response = _client().chat.completions.create(
        model=get_model_name(),
        messages=[
            {
                "role": "system",
                "content": _system_prompt(target_language.strip() or DEFAULT_TARGET_LANGUAGE),
            },
            {
                "role": "user",
                "content": cleaned_text,
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def refine_translation(
    source_text: str,
    current_translation: str,
    user_feedback: str,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
    chat_messages=None,
) -> str:
    target_language = target_language.strip() or DEFAULT_TARGET_LANGUAGE
    feedback = user_feedback.strip()
    if not feedback:
        return current_translation

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional translation editor. Revise the current "
                f"{target_language} translation according to the user's feedback. "
                "Preserve the original meaning unless the user explicitly asks "
                "for a tone, style, or wording change. Return only the complete "
                "revised translation, without explanations or markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                "Original text:\n"
                f"{source_text.strip()}\n\n"
                f"Current {target_language} translation:\n"
                f"{current_translation.strip()}"
            ),
        },
    ]

    for message in (chat_messages or [])[-10:]:
        if message["role"] in {"user", "assistant"}:
            messages.append(
                {
                    "role": message["role"],
                    "content": message["content"],
                }
            )

    messages.append(
        {
            "role": "user",
            "content": (
                "Apply this new feedback to the current translation:\n"
                f"{feedback}\n\n"
                "Return only the complete revised translation."
            ),
        }
    )

    response = _client().chat.completions.create(
        model=get_model_name(),
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content
