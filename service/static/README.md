# static-server

`service/static` 现在使用 **CMake** 构建，不再依赖 `compiler.sh`。

## 导出二进制（推荐）

在 `service/static` 目录执行：

```bash
docker buildx build \
  --build-arg STATIC_BASE_IMAGE=ubuntu-24.04:galay-web-1.0 \
  --build-arg GALAY_KERNEL_BACKEND=epoll \
  --target artifact \
  --output type=local,dest=/home/ubuntu/service/gblob/static/bin \
  -f docker/Dockerfile \
  .
```

导出结果：

```text
/home/ubuntu/service/gblob/static/bin/static-server
```

## 本地 CMake 构建

在仓库根目录执行：

```bash
cmake -S service/static -B build/static \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/usr/local \
  -DGALAY_KERNEL_BACKEND=epoll
cmake --build build/static -j"$(nproc)"
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
proxy.route=/api,127.0.0.1,8080,http
proxy.route=/auth,127.0.0.1,8081,http
```

支持两种多路由写法：

```text
# 1) 重复行（推荐）
proxy.route=<prefix>,<host>,<port>,<mode>

# 2) 索引键
proxy.route.1.prefix=/api
proxy.route.1.upstream_host=127.0.0.1
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
API_PROXY_ROUTES=/api,127.0.0.1,8080,http;/auth,127.0.0.1,8081,http

# 单路由（兼容旧配置）
API_PROXY_ROUTE_PREFIX=/api
API_PROXY_UPSTREAM_HOST=127.0.0.1
API_PROXY_UPSTREAM_PORT=8080
API_PROXY_MODE=http
```
