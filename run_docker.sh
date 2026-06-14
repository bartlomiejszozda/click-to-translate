#!/bin/bash

set -euo pipefail

xhost +local:docker

docker run -d --rm --name translator \
  --env-file .env \
  -p 8501:8501 \
  -e DISPLAY="$DISPLAY" \
  -e STREAMLIT_SERVER_HEADLESS=true \
  -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v translator-data:/app/data \
  my-llm-app

echo "Streamlit should be available at http://localhost:8501"
