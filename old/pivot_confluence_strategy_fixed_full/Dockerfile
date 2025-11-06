FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     bash ca-certificates tzdata &&     rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt
COPY . /app
ENV TZ=Europe/Rome
CMD ["python", "src/main.py", "--mode", "backtest", "--config", "config.yaml"]
