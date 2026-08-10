#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${TRANSLATOR_ENV_FILE:-$HOME/.config/translator/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' "Missing env file: $ENV_FILE" >&2
  printf '%s\n' "Create it or set TRANSLATOR_ENV_FILE to another path." >&2
  exit 1
fi

xhost +local:docker

# Mount source over /app so code edits apply without rebuild.
# Keep translator-data after the source mount so SQLite stays on the named volume.
docker run -d --rm --name translator \
  --env-file "$ENV_FILE" \
  -p 8501:8501 \
  -e DISPLAY="$DISPLAY" \
  -e STREAMLIT_SERVER_HEADLESS=true \
  -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$SCRIPT_DIR:/app" \
  -v translator-data:/app/data \
  my-llm-app

echo "Streamlit should be available at http://localhost:8501"
echo "Source mounted from $SCRIPT_DIR (no rebuild needed for code changes)"
