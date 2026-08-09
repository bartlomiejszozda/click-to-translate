#!/bin/bash

set -euo pipefail

ENV_FILE="${TRANSLATOR_ENV_FILE:-$HOME/.config/translator/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' "Missing env file: $ENV_FILE" >&2
  printf '%s\n' "Create it or set TRANSLATOR_ENV_FILE to another path." >&2
  exit 1
fi

xhost +local:docker

docker run -d --rm --name translator \
  --env-file "$ENV_FILE" \
  -p 8501:8501 \
  -e DISPLAY="$DISPLAY" \
  -e STREAMLIT_SERVER_HEADLESS=true \
  -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v translator-data:/app/data \
  my-llm-app

echo "Streamlit should be available at http://localhost:8501"
