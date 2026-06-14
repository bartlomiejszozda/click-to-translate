#!/bin/bash

set -euo pipefail

CONTAINER_NAME="${TRANSLATOR_CONTAINER:-translator}"
TARGET_LANGUAGE="${TARGET_LANGUAGE:-English}"

notify() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$@"
  fi
}

if ! command -v xclip >/dev/null 2>&1; then
  notify "Clipboard Translator" "xclip is not installed on the host."
  printf '%s\n' "xclip is not installed on the host." >&2
  exit 1
fi

if result=$(
  docker exec \
    -e TARGET_LANGUAGE="$TARGET_LANGUAGE" \
    "$CONTAINER_NAME" \
    python /app/translate_clipboard.py \
      --target-language "$TARGET_LANGUAGE" \
      --no-prompt
); then
  if printf '%s' "$result" | xclip -selection clipboard -i; then
    notify "Clipboard Translator" "Translated text copied to clipboard."
  else
    notify "Clipboard Translator" "Could not copy translation to clipboard."
    printf '%s\n' "Could not copy translation to clipboard." >&2
    exit 1
  fi
else
  notify "Clipboard Translator" "Translation failed."
  printf '%s\n' "$result" >&2
  exit 1
fi
