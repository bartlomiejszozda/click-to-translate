# Clipboard Translator

Fast clipboard translation through a host keyboard shortcut, plus a Streamlit
window for translation history and chat-based revisions.

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
  -p 8501:8501 \
  -e API_KEY="$API_KEY" \
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
/home/bzd/projects/my_llm_projects/translator/clipboard_to_docker.sh
```

Usage:

1. Copy text normally with `Ctrl+C`.
2. Press your custom shortcut.
3. The running Docker container translates the clipboard.
4. The translated text is copied back to the clipboard.
5. Paste it with `Ctrl+V`.

The shortcut also saves the translation to the same SQLite history used by the
Streamlit app.

To target another language from the shortcut:

```bash
TARGET_LANGUAGE=Polish /home/bzd/projects/my_llm_projects/translator/clipboard_to_docker.sh
```

## Streamlit Workflow

In the Streamlit window you can:

- translate clipboard text with `Read + translate`
- translate manually edited text with `Translate current text`
- copy the current result back to the clipboard
- select previous translations from the sidebar
- send feedback in chat to create revised translations
- inspect revision history for each translation

## Notes

This setup uses `xclip`, so it is designed for Linux/X11 or XWayland. Pure
Wayland sessions may need a different clipboard backend.
