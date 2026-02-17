# Galay Static Service

`service/static` 现在提供两部分能力：
- 静态资源服务（`/`）
- API 反向代理（`/api/*` Raw 转发到上游 `/*`）

## Docker Compose 运行

```bash
cd service/static
cp .env.example .env
docker compose up --build -d
```

启动后访问：`http://localhost:8080`

转发行为示例：
- 请求 `GET /api/projects` -> 上游 `GET /projects`
- 请求 `POST /api/chat` -> 上游 `POST /chat`

停止服务：

```bash
cd service/static
docker compose down
```

## 直接构建镜像

在仓库根目录执行（构建上下文需要包含 `frontend/`）：

```bash
docker build -f service/static/Dockerfile -t galay-static:latest .
docker run --rm -p 8080:8080 galay-static:latest
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `STATIC_HOST` | `0.0.0.0` | 监听地址 |
| `STATIC_PORT` | `8080` | 监听端口 |
| `STATIC_FRONTEND_ROOT` | `/app/frontend` | 静态文件目录 |
| `API_PROXY_UPSTREAM_HOST` | `127.0.0.1` | `/api/*` 转发上游主机 |
| `API_PROXY_UPSTREAM_PORT` | `8081` | `/api/*` 转发上游端口 |
| `GALAY_KERNEL_REPO` | `https://github.com/gzj-creator/galay-kernel.git` | 构建阶段仓库地址 |
| `GALAY_KERNEL_REF` | `main` | 构建阶段分支/Tag/Commit |
| `GALAY_HTTP_REPO` | `https://github.com/gzj-creator/galay-http.git` | 构建阶段仓库地址 |
| `GALAY_HTTP_REF` | `main` | 构建阶段分支/Tag/Commit |

## 本地非容器运行

`main.cc` 同样支持以上 `STATIC_*` 与 `API_PROXY_*` 环境变量。  
本地编译可继续使用：

```bash
cd service/static
./compiler.sh
./server
```
