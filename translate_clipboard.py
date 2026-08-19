import argparse
import subprocess
import sys
import traceback
from pathlib import Path

from clipboard_io import read_clipboard, write_clipboard
from history_store import (
    create_translation,
    update_clipboard_status,
    update_learning_suggestions,
)
from llm_client import DEFAULT_TARGET_LANGUAGE, get_model_name
from translator import translate_text


def parse_args():
    parser = argparse.ArgumentParser(
        description="Translate the current X clipboard text."
    )
    parser.add_argument(
        "--target-language",
        default=DEFAULT_TARGET_LANGUAGE,
        help="Language to translate to. Defaults to English.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy the translated result back to the clipboard without prompting.",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Do not ask whether to copy the result.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the translated result.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print a full traceback when an error occurs (default: on).",
    )
    return parser.parse_args()


def print_error(exc: Exception, debug: bool = True) -> None:
    if debug:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        return

    print(f"Error ({type(exc).__name__}): {exc}", file=sys.stderr)

    seen = {id(exc)}
    cause = exc.__cause__ or exc.__context__
    while cause is not None and id(cause) not in seen:
        print(f"Caused by {type(cause).__name__}: {cause}", file=sys.stderr)
        seen.add(id(cause))
        cause = cause.__cause__ or cause.__context__


def start_learning_generation(translation_id: int) -> None:
    worker = Path(__file__).with_name("generate_learning.py")
    try:
        subprocess.Popen(
            [sys.executable, str(worker), str(translation_id)],
            cwd=worker.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        update_learning_suggestions(
            translation_id,
            "_Learning suggestions could not be started for this translation._",
        )
        print(
            f"Warning: could not start learning-suggestions worker: {exc}",
            file=sys.stderr,
        )


def main():
    args = parse_args()

    try:
        user_input = read_clipboard()
        result = translate_text(user_input, args.target_language)
        if not args.quiet:
            print(result)

        should_copy = args.copy
        if not args.copy and not args.no_prompt and sys.stdin.isatty():
            answer = input("\nCopy result to clipboard? [y/N]: ").strip().lower()
            should_copy = answer == "y"

        translation_id = create_translation(
            source_text=user_input,
            translated_text=result,
            target_language=args.target_language,
            model=get_model_name(),
            origin="shortcut",
            # The host shortcut copies stdout after docker exec exits, so this
            # starts false and is only updated when Python itself writes xclip.
            copied_to_clipboard=False,
        )
        start_learning_generation(translation_id)

        if should_copy:
            write_clipboard(result)
            update_clipboard_status(translation_id, True)
    except Exception as exc:
        print_error(exc, debug=args.debug)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
