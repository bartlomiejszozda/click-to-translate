FROM python:3.11-slim

WORKDIR /app

ENV TRANSLATOR_DB_PATH=/app/data/translations.sqlite3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends xclip vim && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
