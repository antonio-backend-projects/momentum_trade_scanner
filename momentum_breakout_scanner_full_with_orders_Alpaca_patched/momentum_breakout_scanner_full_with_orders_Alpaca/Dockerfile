# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scanner.py signals.py trade.py options.py db.py config.yaml tickers.csv ./
COPY notify/ ./notify/
RUN mkdir -p /app/state
CMD ["python", "scanner.py"]
