# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) codice
COPY scanner.py signals.py config.yaml tickers.csv ./
# copia esplicita della cartella notify (meglio che usare "notify/" nello stesso COPY)
COPY notify/ ./notify/

# 3) stato runtime (persistito via volume)
RUN mkdir -p /app/state

CMD ["python", "scanner.py"]
