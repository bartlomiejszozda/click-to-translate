import argparse

from history_store import get_translation, update_learning_suggestions
from learning import generate_learning_suggestions


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate and save learning suggestions for a translation."
    )
    parser.add_argument("translation_id", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    item = get_translation(args.translation_id)
    if item is None:
        raise RuntimeError(f"Translation #{args.translation_id} was not found.")

    try:
        suggestions = generate_learning_suggestions(
            source_text=item["source_text"],
            translated_text=item["current_translation"],
            target_language=item["target_language"],
        )
    except Exception:
        update_learning_suggestions(
            args.translation_id,
            "_Learning suggestions could not be generated for this translation._",
        )
        raise

    update_learning_suggestions(args.translation_id, suggestions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
