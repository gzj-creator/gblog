FROM python:3.11-slim AS base

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY src/ src/
COPY scripts/ scripts/

ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO

EXPOSE 8000

CMD ["python", "scripts/run_server.py", "--host", "0.0.0.0", "--port", "8000"]
