# static-server

`service/static` 现在使用 **CMake** 构建，不再依赖 `compiler.sh`。

## 导出二进制（推荐）

在 `service/static` 目录执行：

```bash
bash scripts/builder.sh
```

等价命令：

```bash
docker buildx build \
  --build-arg STATIC_BASE_IMAGE=ubuntu-24.04:galay-web-1.0 \
  --build-arg GALAY_KERNEL_BACKEND=epoll \
  --target artifact \
  --output type=local,dest=/home/ubuntu/service/gblob/service/static/bin \
  -f docker/Dockerfile \
  .
```

导出结果：

```text
/home/ubuntu/service/gblob/service/static/bin/static-server
```

## 本地 CMake 构建

在仓库根目录执行：

```bash
cmake -S service/static -B build/static \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/usr/local \
  -DGALAY_KERNEL_BACKEND=epoll
cmake --build build/static --parallel
```

产物：

```text
build/static/static-server
```

## 配置文件

默认配置文件：

```text
/app/config/static-server.conf
```

示例文件在：

```text
service/static/config/static-server.conf
```

关键配置项：

```text
proxy.enabled=true
proxy.route=/api,backend,8080,http
proxy.route=/auth,backend,8080,http
proxy.route=/ai,ai,8000,raw
```

支持两种多路由写法：

```text
# 1) 重复行（推荐）
proxy.route=<prefix>,<host>,<port>,<mode>

# 2) 索引键
proxy.route.1.prefix=/api
proxy.route.1.upstream_host=backend
proxy.route.1.upstream_port=8080
proxy.route.1.mode=http
```

可通过环境变量覆盖路径：

```text
STATIC_CONFIG_PATH=/custom/path/static-server.conf
```

兼容的环境变量：

```text
# 多路由（优先）
API_PROXY_ROUTES=/api,backend,8080,http;/auth,backend,8080,http;/ai,ai,8000,raw

# 单路由（兼容旧配置）
API_PROXY_ROUTE_PREFIX=/api
API_PROXY_UPSTREAM_HOST=backend
API_PROXY_UPSTREAM_PORT=8080
API_PROXY_MODE=http
```

## Local Stream Proxy Demo (No Docker)

This demo starts:

- a mock AI SSE upstream (`127.0.0.1:19000`)
- static-server in `raw` mode (`127.0.0.1:19080`)
- static-server in `http` mode (`127.0.0.1:19081`)

Then it probes `/ai/api/chat/stream` on both modes and prints per-line arrival timestamps.

```bash
bash service/static/scripts/demo-stream-proxy.sh
```

Optional environment variables:

```text
STATIC_BIN=/absolute/path/to/static-server
UPSTREAM_PORT=19000
RAW_PORT=19080
HTTP_PORT=19081
MOCK_CHUNK_DELAY=0.35
MOCK_LINGER_SECONDS=0
PROBE_TIMEOUT=8
```
