# Galay AI Service

基于 RAG（检索增强生成）的 Galay 框架智能问答服务，为用户提供关于 Galay 高性能 C++ 网络框架的实时文档问答。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (chat.js)                     │
│                  fetch('/api/chat', ...)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Application                     │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐ │
│  │ /api/chat│  │/api/search│  │ /api/rebuild /api/stats│ │
│  └────┬─────┘  └────┬─────┘  └──────────┬─────────────┘ │
│       │              │                   │               │
│  ┌────▼──────────────▼───────────────────▼─────────────┐ │
│  │                 Service Layer                        │ │
│  │  ChatService  │  RAGService  │  IndexService        │ │
│  └────┬──────────────┬──────────────────┬──────────────┘ │
│       │              │                  │                │
│  ┌────▼──────────────▼──────────────────▼─────────────┐  │
│  │                  Core Layer                         │  │
│  │  VectorStore  │  Embeddings  │  DocumentLoader     │  │
│  └────┬──────────────┬──────────────────┬─────────────┘  │
│       │              │                  │                │
│  ┌────▼────┐   ┌─────▼─────┐   ┌───────▼──────┐        │
│  │ ChromaDB│   │ OpenAI API│   │ Markdown Docs│        │
│  └─────────┘   └───────────┘   └──────────────┘        │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
service/ai/
├── README.md                 # 本文档
├── requirements.txt          # Python 依赖
├── Makefile                  # 常用命令
├── .env.example              # 环境变量模板
├── .gitignore
├── docker/
│   ├── Dockerfile            # Docker 构建
│   └── docker-compose.yml    # Docker Compose
├── scripts/
│   ├── builder.sh           # Docker 镜像构建脚本
│   ├── build_index.py        # 构建向量索引
│   ├── install_linux.sh      # Linux 一键安装脚本
│   ├── run_server.py         # 启动服务
│   └── test_api.py           # API 集成测试
├── src/
│   ├── app.py                # FastAPI 应用工厂 + 生命周期
│   ├── config.py             # Pydantic Settings 配置
│   ├── api/                  # API 路由层
│   │   ├── router.py         # 路由注册中心
│   │   ├── chat.py           # POST /api/chat
│   │   ├── search.py         # POST /api/search
│   │   ├── admin.py          # 管理接口
│   │   └── middleware.py     # 中间件（错误处理、日志、CORS）
│   ├── core/                 # 核心组件
│   │   ├── embeddings.py     # Embedding 模型管理
│   │   ├── vector_store.py   # Chroma 向量存储
│   │   ├── document_loader.py# Markdown 文档加载
│   │   └── text_splitter.py  # 文本分割
│   ├── services/             # 业务服务
│   │   ├── chat_service.py   # 对话服务（含会话记忆）
│   │   ├── rag_service.py    # RAG 检索增强生成
│   │   └── index_service.py  # 索引管理
│   ├── models/               # Pydantic 数据模型
│   │   ├── request.py        # 请求模型
│   │   └── response.py       # 响应模型
│   └── utils/                # 工具
│       ├── logger.py         # 结构化日志
│       └── exceptions.py     # 自定义异常
└── docs/
    ├── architecture.md       # 架构设计
    └── api-reference.md      # API 参考
```

## 快速开始

### Linux 一键安装

```bash
cd service/ai
bash scripts/install_linux.sh --docs-root /path/to/repos --api-key sk-xxx --build-index --run
```

可选参数说明：
- `--docs-root`：写入 `.env` 的 `GALAY_DOCS_ROOT_PATH`
- `--api-key`：写入 `.env` 的 `OPENAI_API_KEY`
- `--build-index`：安装后自动执行 `build_index.py --force`
- `--run`：安装后直接启动服务
- `--no-system-deps`：跳过系统包安装（已手动安装 Python 时使用）

### 1. 安装依赖

```bash
cd service/ai
make install
# 或
pip install -r requirements.txt
```

### Docker 构建

```bash
cd service/ai
bash scripts/builder.sh
```

可选环境变量：
- `AI_BASE_IMAGE`：默认 `python:3.11-slim`
- `AI_IMAGE_TAG`：默认 `gblob-ai:local`

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和文档配置（推荐 GALAY_DOCS_ROOT_PATH 或 GALAY_DOCS_PATHS_FILE）
# 如需文件列表模式，可参考 docs_paths.example.txt
```

### 3. 构建向量索引

```bash
make build-index
# 强制重建
make build-index-force
```

索引构建前会自动做文档清洗（去除常见装饰符号并修复粘连段落/列表），
如果你调整了清洗逻辑，需要执行 `make build-index-force` 让存量索引生效。

### 4. 启动服务

```bash
make run
# 或
python scripts/run_server.py --reload
```

服务启动后访问：
- 健康检查：`http://localhost:8000/`
- Swagger 文档：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`

### 5. 运行测试

```bash
make test

# 本地格式回归（不依赖 AI 网络调用）
make verify-format

# 统一仓库文档风格（按 docs/doc_style_prompt.md）
make apply-doc-style
make verify-doc-style
```

### 6. 知识库自动重建与评测

默认会同时索引 Markdown 与代码文件（`.h/.hpp/.cc/.cpp/...`），并跳过过大文件与二进制文件。
另外会自动排除目录：`.claude/`、`todo/`（避免将规范草稿和待办笔记写入知识库）。

```bash
# 一键重建（可选先从 frontend/docs 生成 galay-* markdown）
python scripts/rebuild_kb.py --force --generate-docs

# 运行检索/问答基准评测
python scripts/evaluate_kb.py --mode all
```

评测样例文件：

```text
service/ai/eval/benchmark_cases.json
```

### 7. 一键部署（Docker Compose）

```bash
cd service/ai
bash scripts/builder.sh --docs-root /home/ubuntu/service/gblog/repos
```

常用参数：

```bash
# 重新构建镜像并部署 + 重建索引 + 评测
bash scripts/builder.sh --docs-root /home/ubuntu/service/gblog/repos --run-eval

# 仅重启服务，不重建索引
bash scripts/builder.sh --no-build --no-rebuild-kb
```

## 使用流程

```
用户提问
   │
   ▼
Frontend (chat.js)
   │  POST /api/chat { message, session_id }
   ▼
ChatService
   │  1. 获取/创建会话记忆
   │  2. 调用 RAGService
   ▼
RAGService
   │  3. VectorStore.search(query) → 相关文档片段
   │  4. 构建 prompt = system_prompt + context + history + question
   │  5. LLM.generate(prompt) → 回答
   ▼
ChatService
   │  6. 保存对话到记忆
   │  7. 提取引用来源
   ▼
返回 { success, response, sources, session_id }
   │
   ▼
Frontend 展示回答 + 引用来源
```

## 运转流程

```
启动服务 (uvicorn)
   │
   ▼
create_app()
   │  1. setup_logging() — 配置日志
   │  2. 注册中间件（错误处理、请求日志、CORS）
   │  3. 注册路由（/api/chat, /api/search, /api/rebuild, ...）
   ▼
lifespan 启动
   │  4. 校验 OPENAI_API_KEY
   │  5. VectorStoreManager.initialize()
   │     ├─ 存在索引 → 加载 ChromaDB
   │     └─ 不存在 → 加载文档 → 分割 → 嵌入 → 存储
   │  6. 初始化 ChatService, IndexService
   ▼
监听请求 (0.0.0.0:8000)
   │
   ▼
收到请求 → request_logger → error_handler → 路由处理 → 返回响应
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| GET | `/health` | 健康检查 |
| POST | `/api/chat` | 聊天问答 |
| POST | `/api/search` | 文档搜索 |
| POST | `/api/rebuild` | 重建向量索引 |
| GET | `/api/stats` | 服务统计 |
| DELETE | `/api/session/{id}` | 清除会话 |

### POST /api/chat

请求：
```json
{
  "message": "Galay 框架的核心特性是什么？",
  "session_id": "session_123",
  "use_memory": true
}
```

响应：
```json
{
  "success": true,
  "response": "Galay 框架的核心特性包括...",
  "sources": [
    { "project": "galay", "file": "README.md", "file_name": "README.md" }
  ],
  "session_id": "session_123"
}
```

### POST /api/search

请求：
```json
{
  "query": "协程调度",
  "k": 3
}
```

响应：
```json
{
  "success": true,
  "results": [
    { "content": "...", "metadata": {...}, "score": 0.85 }
  ]
}
```

## 配置参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | OpenAI API 密钥（必填） |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | API 基础地址 |
| `MODEL_NAME` | `gpt-4-turbo-preview` | LLM 模型 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_BATCH_SIZE` | `32` | Embedding 批量大小（兼容部分第三方 OpenAI 接口） |
| `EMBEDDING_REQUEST_TIMEOUT` | `120` | Embedding 请求超时（秒） |
| `EMBEDDING_MAX_RETRIES` | `6` | Embedding 失败重试次数 |
| `TEMPERATURE` | `0.7` | 生成温度 |
| `VECTOR_STORE_PATH` | `./vector_store` | 向量存储路径 |
| `CHUNK_SIZE` | `1000` | 文本分割大小 |
| `CHUNK_OVERLAP` | `200` | 分割重叠 |
| `GALAY_DOCS_ROOT_PATH` | `""` | 仓库根目录，自动扫描一级子目录 |
| `GALAY_DOCS_CONTAINER_ROOT_PATH` | `"/docs/repos"` | Docker 容器内文档根路径（可选） |
| `GALAY_DOCS_PATHS_FILE` | `""` | 路径文件（每行一个目录，支持 `#` 注释） |
| `GALAY_DOCS_PATH` | `""` | 额外单仓库路径（可选） |
| `GALAY_*_DOCS_PATH` | — | 旧版逐仓库路径变量（可选，兼容） |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `ENVIRONMENT` | `development` | 环境（development/production） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## Docker 部署

```bash
# 构建镜像
make docker-build

# 启动服务
make docker-up

# 停止服务
make docker-down
```

确保 `.env` 文件中至少配置一种文档来源：`GALAY_DOCS_ROOT_PATH`、`GALAY_DOCS_PATHS_FILE` 或兼容的 `GALAY_*_DOCS_PATH`。  
使用 Docker 时，如需修改容器内挂载目标，可设置 `GALAY_DOCS_CONTAINER_ROOT_PATH`。

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| `OPENAI_API_KEY is required` | 在 `.env` 中配置有效的 API Key |
| `No valid documentation paths found` | 检查 `.env` 中的文档路径是否存在 |
| `Vector store not initialized` | 运行 `make build-index` 构建索引 |
| `TypeError: 'NoneType' object is not iterable`（embedding） | 降低 `EMBEDDING_BATCH_SIZE`（如 `16`），并重跑 `make build-index-force` |
| 搜索结果不相关 | 尝试 `make build-index-force` 重建索引 |
| 前端无法连接 | 确认服务运行在 `localhost:8000`，检查 CORS 配置 |
