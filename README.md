# Galay Blog

基于 Galay Framework 的博客系统，当前采用独立进程架构：

- `gateway`：统一入口与静态资源
- `business`：博客业务接口
- `auth`：认证接口
- `db`：数据库抽象与用户/文档元数据存储
- `admin`：后台文档管理（上传/更新/删除）
- `indexer`：索引任务消费与重建执行
- `ai`：检索问答（chat/search）

## 项目结构

```text
blog/
├── frontend/
├── service/
│   ├── gateway/
│   ├── business/
│   ├── auth/
│   ├── db/
│   ├── admin/
│   ├── indexer/
│   └── ai/
└── docker-compose.yml
```

## 网关路由

- `/api/v1/auth -> auth(8081)`
- `/api/v1/admin -> admin(8010)`
- `/api -> business(8080)`
- `/ai -> ai(8000)`

## 服务端口汇总

当前 `docker-compose.yml` 使用 `network_mode: host`，服务监听端口如下：

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| gateway | 80 | 网关入口与静态资源 |
| business | 8080 | 博客业务 API |
| auth | 8081 | 认证 API |
| db | 8082 | 数据库抽象服务 API |
| admin | 8010 | 后台管理 API |
| indexer | 8011 | 索引任务服务 API |
| ai | 8000 | 检索问答服务 API |

## 本地构建

```bash
bash service/db/scripts/S3-Build.sh
bash service/auth/scripts/S3-Build.sh
bash service/business/scripts/S3-Build.sh
bash service/gateway/scripts/builder.sh
```

Python 服务安装依赖：

```bash
python3 -m venv service/admin/venv && service/admin/venv/bin/pip install -r service/admin/requirements.txt
python3 -m venv service/indexer/venv && service/indexer/venv/bin/pip install -r service/indexer/requirements.txt
python3 -m venv service/ai/venv && service/ai/venv/bin/pip install -r service/ai/requirements.txt
```

## Docker 运行

```bash
bash scripts/compose-stack.sh up
```

服务清单：`gateway`, `business`, `auth`, `db`, `admin`, `indexer`, `ai`（全部由 Dockerfile 构建）。

## 一键构建与启动（推荐）

脚本会自动：

- 创建各服务挂载目录（配置/日志/数据）
- 初始化默认配置文件（如 `gateway` 配置、`ai` 的 `.env`）
- 构建全部镜像并后台启动

```bash
bash scripts/compose-stack.sh up
```

默认挂载根目录为 `/root/service`，目录示例：

- `/root/service/gateway/config`
- `/root/service/gateway/logs`
- `/root/service/business/logs`
- `/root/service/auth/logs`
- `/root/service/db/logs`
- `/root/service/admin/config`
- `/root/service/admin/logs`
- `/root/service/admin/managed_docs`
- `/root/service/ai/config`
- `/root/service/ai/logs`
- `/root/service/ai/data`
- `/root/service/indexer/logs`

### 自定义挂载目录

可通过环境变量覆盖，示例：

```bash
export SERVICE_MOUNT_ROOT=/data/blog-services
export GATEWAY_CONFIG_DIR=/data/custom/gateway/config
export AI_ENV_FILE=/data/custom/ai/.env
bash scripts/compose-stack.sh up
```

脚本支持动作：

```bash
bash scripts/compose-stack.sh build
bash scripts/compose-stack.sh down
bash scripts/compose-stack.sh restart
bash scripts/compose-stack.sh ps
bash scripts/compose-stack.sh logs gateway
```

## 基础镜像说明

依赖 Galay 系列库的服务（`gateway/business/auth/db`）统一从 `ubuntu:galay-v1` 进行编译和运行，可通过环境变量覆盖：

```bash
export GALAY_BASE_IMAGE=ubuntu:galay-v1
export GALAY_KERNEL_BACKEND=epoll
```
