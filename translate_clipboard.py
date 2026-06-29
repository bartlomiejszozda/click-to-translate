import argparse
import sys

from clipboard_io import read_clipboard, write_clipboard
from history_store import create_translation, update_clipboard_status
from translator import DEFAULT_TARGET_LANGUAGE, get_model_name, translate_text


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
    return parser.parse_args()

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

        if should_copy:
            write_clipboard(result)
            update_clipboard_status(translation_id, True)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
