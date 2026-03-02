# Galay AI Service

AI 服务仅负责检索问答（RAG）能力，不再承载管理后台与认证逻辑。

## 角色定位

- 提供聊天问答：`/api/chat`、`/api/chat/stream`
- 提供检索接口：`/api/search`
- 加载本地 Chroma 持久化向量库
- 监听 DB 服务 `index_state` 版本变化并热重载向量库（无需重启）

管理能力已拆分：
- 管理后台：`service/admin`
- 索引任务执行：`service/indexer`
- 元数据与任务队列：`service/db`

## 快速开始

```bash
cd service/ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run_server.py --host 0.0.0.0 --port 8000
```

可选：首次构建索引

```bash
python scripts/build_index.py --force
```

## 关键配置

- `OPENAI_API_KEY`：必填
- `GALAY_DOCS_ROOT_PATH`：文档根目录
- `VECTOR_STORE_PATH`：Chroma 持久化目录
- `DB_SERVICE_BASE_URL`：DB 服务地址（用于 index_state 监听）
- `INDEX_STATE_AUTO_RELOAD`：是否开启热重载（默认 true）
- `INDEX_STATE_POLL_INTERVAL_SECONDS`：轮询间隔（默认 2.0）

完整示例见：`service/ai/.env.example`

## API

Base URL: `http://<ai-host>:8000`

- `GET /`：服务状态
- `GET /health`：健康检查（包含 `index_version` 和 watcher 状态）
- `POST /api/chat`
- `POST /api/chat/stream`（SSE）
- `POST /api/search`

详细接口：`service/ai/docs/接口参考.md`

## 热重载流程

1. `admin` 写文档并创建重建任务
2. `indexer` 执行重建，完成后调用 DB `finish-success`
3. DB 增加 `index_state.current_version`
4. AI watcher 检测到版本变化，执行 `load_existing()` 热重载

## 文档

- `service/ai/docs/架构设计.md`
- `service/ai/docs/接口参考.md`
