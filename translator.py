import os

from openai import OpenAI


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TARGET_LANGUAGE = "English"


def get_model_name() -> str:
    return os.getenv("MODEL", DEFAULT_MODEL)


def _api_key() -> str:
    key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No API key found. Set API_KEY (or OPENAI_API_KEY) in "
            "~/.config/translator/.env and restart the container so docker "
            "reads the file again."
        )
    return key.strip()


def _client():
    return OpenAI(
        api_key=_api_key(),
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
    )
    return response.choices[0].message.content


def _learning_prompt(target_language: str) -> str:
    return (
        "You are a supportive language coach. Compare the learner's source text "
        f"with the final {target_language} version and identify what the learner "
        "should study to write more accurately and naturally.\n\n"
        "Focus only on lessons supported by this specific example, including any "
        "useful grammar, vocabulary, collocations, idioms, word choice, register, "
        "clarity, or natural phrasing. Prioritize the most valuable points and "
        "ignore trivial differences that are merely matters of taste.\n\n"
        "For each point:\n"
        "- quote a short relevant phrase from the source and its improved form;\n"
        "- explain the rule or usage in simple language;\n"
        "- give one short new example the learner can reuse.\n\n"
        "Use clear Markdown with the headings `Main lessons`, `Useful vocabulary "
        "and phrasing`, and `Practice`. Include only sections that have useful "
        "content. In `Practice`, give 1-2 very short exercises based on the main "
        "lessons, followed by a short `Answers` subsection. "
        "Be concise, encouraging, and specific. Do not repeat the full translation. "
        "If the source is already excellent, say so and explain at most two subtle "
        "ways to make it sound even more natural."
    )


def generate_learning_suggestions(
    source_text: str,
    translated_text: str,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
) -> str:
    source_text = source_text.strip()
    translated_text = translated_text.strip()
    if not source_text or not translated_text:
        return ""

    target_language = target_language.strip() or DEFAULT_TARGET_LANGUAGE
    response = _client().chat.completions.create(
        model=get_model_name(),
        messages=[
            {
                "role": "system",
                "content": _learning_prompt(target_language),
            },
            {
                "role": "user",
                "content": (
                    "Source text written by the learner:\n"
                    f"{source_text}\n\n"
                    f"Final {target_language} version:\n"
                    f"{translated_text}"
                ),
            },
        ],
    )
    return response.choices[0].message.content or ""


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
    )
    return response.choices[0].message.content
