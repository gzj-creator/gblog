FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY docs ./docs

ENV PYTHONUNBUFFERED=1

EXPOSE 8010

CMD ["python", "scripts/run_server.py", "--host", "0.0.0.0", "--port", "8010"]
