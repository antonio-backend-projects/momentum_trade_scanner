# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# codice (includiamo anche signal_queue.py)
COPY scanner.py signals.py trade.py options.py db.py config.yaml tickers.csv signal_queue.py ./
COPY notify/ ./notify/

# state dir (coda segnali/logs se servono)
RUN mkdir -p /app/state

CMD ["python", "scanner.py"]
