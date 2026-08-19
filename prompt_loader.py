import re
from dataclasses import dataclass
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PROMPT_NAME = re.compile(r"[a-z][a-z0-9_]*")
_SECTION_HEADERS = {
    "[SYSTEM]": "system",
    "[USER]": "user",
}


class PromptTemplateError(RuntimeError):
    """Raised when a prompt template cannot be loaded or rendered."""


@dataclass(frozen=True)
class PromptTemplate:
    system: str
    user: str | None = None


def load_prompt(name: str) -> PromptTemplate:
    if _PROMPT_NAME.fullmatch(name) is None:
        raise PromptTemplateError(f"Invalid prompt name: {name!r}")

    path = PROMPTS_DIR / f"{name}.txt"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromptTemplateError(f"Could not read prompt template: {path}") from exc

    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in content.splitlines():
        section = _SECTION_HEADERS.get(line.strip())
        if section is not None:
            if section in sections:
                raise PromptTemplateError(
                    f"Prompt template {name!r} repeats the [{section.upper()}] section."
                )
            current_section = section
            sections[section] = []
        elif current_section is None:
            if line.strip():
                raise PromptTemplateError(
                    f"Prompt template {name!r} has text before its first section."
                )
        else:
            sections[current_section].append(line)

    system = "\n".join(sections.get("system", [])).strip()
    if not system:
        raise PromptTemplateError(
            f"Prompt template {name!r} must contain a non-empty [SYSTEM] section."
        )

    user = "\n".join(sections.get("user", [])).strip() or None
    return PromptTemplate(system=system, user=user)


def _render_text(name: str, text: str, values: dict[str, object]) -> str:
    try:
        return text.format_map(values)
    except (KeyError, ValueError) as exc:
        raise PromptTemplateError(
            f"Could not render prompt template {name!r}: {exc}"
        ) from exc


def render_prompt(name: str, **values: object) -> PromptTemplate:
    template = load_prompt(name)
    return PromptTemplate(
        system=_render_text(name, template.system, values),
        user=(
            _render_text(name, template.user, values)
            if template.user is not None
            else None
        ),
    )
