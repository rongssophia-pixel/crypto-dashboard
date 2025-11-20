FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared /app/shared
COPY ../proto /app/proto
COPY . /app/

EXPOSE 50053

CMD ["python", "main.py"]

