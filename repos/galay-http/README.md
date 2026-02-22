# galay-http 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-http.html` for AI vector indexing.

## 概览

galay-http 是 Galay 库体系的 HTTP 协议实现，覆盖 HTTP/1.1、HTTP/2(h2c)、WebSocket、路由与静态文件。

它关注协议编解码与连接处理效率，鉴权、业务模型和领域逻辑由应用层实现。

## 架构

- **HttpServer + HttpRouter** — 服务端监听、路由分发与处理器执行
- **HttpClient + HttpSession** — 协程客户端连接与请求收发
- **协议层** — HTTP/1.1、HTTP/2（h2c）与 WebSocket 能力
- **静态资源** — `mount` 方式挂载目录，可结合缓存协商能力

## 核心 API

### 最小服务端（example/include/E1-EchoServer.cpp）

```cpp
#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"

using namespace galay::http;

Coroutine echoHandler(HttpConn& conn, HttpRequest req) {
    auto response = Http1_1ResponseBuilder::ok()
        .text("Echo: " + req.getBodyStr())
        .build();
    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

int main() {
    HttpRouter router;
    router.addHandler("/echo", echoHandler);
    router.mount("/static", "./html");

    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));
    return 0;
}
```

### 示例入口（与仓库一致）

- `E1/E2` — HTTP Echo（`example/include/E1-EchoServer.cpp`、`E2-EchoClient.cpp`）
- `E3/E4` — WebSocket Echo
- `E5/E6` — HTTPS
- `E7/E8` — WSS
- `E9/E10` — H2c Echo
- `E11` — 静态文件服务
- `E12` — HTTP 反向代理

## 安装与构建

### macOS

```bash
brew install cmake ninja pkg-config
# 根据下方“依赖”章节补充库（如 openssl、spdlog、simdjson、liburing 等）
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build pkg-config
# 根据下方“依赖”章节补充库（如 libssl-dev、libspdlog-dev、libsimdjson-dev、liburing-dev 等）
```

### 通用构建

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

### 构建选项

```text
-DBUILD_TESTS=ON/OFF
-DBUILD_BENCHMARKS=ON/OFF
-DBUILD_EXAMPLES=ON/OFF
-DBUILD_MODULE_EXAMPLES=ON/OFF
-DGALAY_HTTP_ENABLE_SSL=ON/OFF
```

`BUILD_MODULE_EXAMPLES` 需要 CMake >= 3.28，推荐 Ninja/Visual Studio 生成器。

## 依赖

C++23 编译器、CMake 3.22+、spdlog、galay-kernel。

若启用 TLS（HTTPS/WSS）需要额外链接 galay-ssl 与 OpenSSL。

## 项目地址

[https://github.com/gzj-creator/galay-http](https://github.com/gzj-creator/galay-http)
