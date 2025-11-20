FROM python:3.13-slim

WORKDIR /app

# Install Java (required for Flink)
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared /app/shared
COPY ../proto /app/proto
COPY . /app/

EXPOSE 50055

CMD ["python", "main.py"]

