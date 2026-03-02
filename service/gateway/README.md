# Gateway Service

`service/gateway` 负责静态资源托管与 API 反向代理。

## 构建

```bash
cmake -S service/gateway -B build/gateway -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/usr/local
cmake --build build/gateway --parallel
```

产物：`build/gateway/static-server`

## 运行

```bash
STATIC_CONFIG_PATH=service/gateway/config/static-server.conf \
  build/gateway/static-server
```

## 默认代理路由

- `/api/v1/auth -> 127.0.0.1:8081` (auth)
- `/api/v1/admin -> 127.0.0.1:8010` (admin)
- `/api -> 127.0.0.1:8080` (business)
- `/ai -> 127.0.0.1:8000` (ai)

## 配置文件

默认：`service/gateway/config/static-server.conf`

支持环境变量覆盖：

- `STATIC_CONFIG_PATH`
- `API_PROXY_ROUTES`（多路由）
- `API_PROXY_UPSTREAM_HOST` / `API_PROXY_UPSTREAM_PORT` / `API_PROXY_ROUTE_PREFIX`（单路由回退）

- `proxy.route` fifth field `preserve_path` (optional):
  - `false` (default): strip route prefix before forwarding
  - `true`: keep original request path when forwarding
