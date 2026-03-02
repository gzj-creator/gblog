FROM python:3.11-slim

WORKDIR /app

COPY service/indexer/requirements.txt ./requirements-indexer.txt
COPY service/ai/requirements.txt ./requirements-ai.txt
RUN pip install --no-cache-dir -r requirements-indexer.txt -r requirements-ai.txt

COPY service/indexer/src ./src
COPY service/indexer/scripts ./scripts
COPY service/indexer/docs ./docs
COPY service/ai/src ./ai/src
COPY service/ai/scripts ./ai/scripts

ENV PYTHONUNBUFFERED=1
ENV INDEXER_AI_ROOT=/app/ai

EXPOSE 8011

CMD ["python", "scripts/run_server.py", "--host", "0.0.0.0", "--port", "8011"]
