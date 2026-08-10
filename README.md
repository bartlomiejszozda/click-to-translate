# Clipboard Translator

Fast clipboard translation through a host keyboard shortcut, plus a Streamlit
window for translation history and chat-based revisions.

## Configuration

Requires an env file. Default: `~/.config/translator/.env`. Use `TRANSLATOR_ENV_FILE` to use a different path.

```bash
API_KEY=sk-...
```

Optional: `MODEL`, `OPENAI_BASE_URL`
Restart the container after editing the file.

## Build

```bash
docker build -t my-llm-app .
```

## Run Streamlit With Clipboard And History

Allow the container to access your X clipboard:

```bash
xhost +SI:localuser:root
```

Run the app with a persistent SQLite history volume:

```bash
docker run --rm --name translator \
  --env-file "${TRANSLATOR_ENV_FILE:-$HOME/.config/translator/.env}" \
  -p 8501:8501 \
  -e DISPLAY="$DISPLAY" \
  -e XAUTHORITY=/tmp/.docker.xauth \
  -e TRANSLATOR_DB_PATH=/app/data/translations.sqlite3 \
  -v translator-data:/app/data \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  -v "${XAUTHORITY:-$HOME/.Xauthority}:/tmp/.docker.xauth:ro" \
  my-llm-app
```

Open Streamlit:

```text
http://localhost:8501
```

The named Docker volume `translator-data` keeps translation history after the
container stops or the image is rebuilt.

## Fast Shortcut Flow

Bind this command to a custom desktop keyboard shortcut:

```bash
~/projects/my_llm_projects/translator/clipboard_to_docker.sh
```

Usage:

1. Copy text normally with `Ctrl+C`.
2. Press your custom shortcut.
3. The running Docker container translates the clipboard.
4. The translated text is copied back to the clipboard.
5. Paste it with `Ctrl+V`.
6. Learning suggestions are generated in the background and saved with the
   translation for later review in Streamlit.

The shortcut also saves the translation to the same SQLite history used by the
Streamlit app. Background generation keeps the copy-and-paste flow fast; refresh
Streamlit if the learning suggestions are still being prepared.

To target another language from the shortcut:

```bash
TARGET_LANGUAGE=Polish ~/projects/my_llm_projects/translator/clipboard_to_docker.sh
```

## Streamlit Workflow

In the Streamlit window you can:

- translate clipboard text with `Read + translate`
- translate manually edited text with `Translate current text`
- copy the current result back to the clipboard
- review specific grammar, vocabulary, and natural-phrasing lessons generated
  from the source text and its translation
- select previous translations from the sidebar
- send feedback in chat to create revised translations
- inspect revision history for each translation

## Notes

This setup uses `xclip`, so it is designed for Linux/X11 or XWayland. Pure
Wayland sessions may need a different clipboard backend.
