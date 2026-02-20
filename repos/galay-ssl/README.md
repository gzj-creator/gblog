# galay-ssl 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-ssl.html` for AI vector indexing.

## 概览

galay-ssl 是 Galay 库体系的 TLS 传输层，提供异步握手、加密收发与证书校验能力。

它专注链路安全与兼容性，HTTP/RPC 等协议语义仍由上层库承担。

## 架构

- **SslContext** — 负责证书、私钥、TLS 方法与校验策略等上下文配置
- **SslSocket** — 异步 TLS 套接字，封装 `connect/handshake/recv/send/shutdown/close`
- **Memory BIO 管线** — 将 TLS 状态机与网络 IO 解耦，便于与协程调度器协同
- **多后端调度** — 随平台使用 `kqueue` / `epoll` / `io_uring`

## 核心 API

### 最小 TLS Echo 服务端（examples/include/E1-SslEchoServer.cc）

```
#include "galay-ssl/async/SslSocket.h"
#include "galay-ssl/ssl/SslContext.h"
#include 
#include 
#include 
#include 
#include 
#include 

#ifdef USE_KQUEUE
#include 
using IOSchedulerType = galay::kernel::KqueueScheduler;
#elif defined(USE_EPOLL)
#include 
using IOSchedulerType = galay::kernel::EpollScheduler;
#elif defined(USE_IOURING)
#include 
using IOSchedulerType = galay::kernel::IOUringScheduler;
#endif

using namespace galay::ssl;
using namespace galay::kernel;

std::atomic g_running{true};

void signalHandler(int) { g_running = false; }

Coroutine handleClient(SslContext* ctx, GHandle handle) {
    SslSocket client(ctx, handle);
    client.option().handleNonBlock();

    while (!client.isHandshakeCompleted()) {
        auto hs = co_await client.handshake();
        if (!hs) {
            co_await client.close();
            co_return;
        }
    }

    char buffer[4096];
    auto recvResult = co_await client.recv(buffer, sizeof(buffer));
    if (recvResult && recvResult.value().size() > 0) {
        auto& bytes = recvResult.value();
        co_await client.send(reinterpret_cast(bytes.data()), bytes.size());
    }

    co_await client.shutdown();
    co_await client.close();
}

Coroutine sslEchoServer(IOSchedulerType* scheduler, SslContext* ctx, uint16_t port) {
    SslSocket listener(ctx);
    listener.option().handleReuseAddr();
    listener.option().handleNonBlock();

    if (!listener.bind(Host(IPType::IPV4, "0.0.0.0", port))) co_return;
    if (!listener.listen(128)) co_return;

    while (g_running) {
        Host clientHost;
        auto accepted = co_await listener.accept(&clientHost);
        if (accepted) {
            scheduler->spawn(handleClient(ctx, accepted.value()));
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc (std::stoi(argv[1]));
    SslContext ctx(SslMethod::TLS_Server);
    if (!ctx.isValid()) return 1;
    if (!ctx.loadCertificate(argv[2])) return 1;
    if (!ctx.loadPrivateKey(argv[3])) return 1;

    IOSchedulerType scheduler;
    scheduler.start();
    scheduler.spawn(sslEchoServer(&scheduler, &ctx, port));

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    scheduler.stop();
    return 0;
}
```

### 示例入口（与仓库一致）

- `E1-SslEchoServer-Include` — `examples/include/E1-SslEchoServer.cc`
- `E2-SslClient-Include` — `examples/include/E2-SslClient.cc`
- `E1-SslEchoServer-Import` — `examples/import/E1-SslEchoServer.cc`
- `E2-SslClient-Import` — `examples/import/E2-SslClient.cc`

## 构建

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

### 构建选项

```
-DBUILD_TESTS=ON/OFF
-DBUILD_BENCHMARKS=ON/OFF
-DBUILD_EXAMPLES=ON/OFF
-DBUILD_SHARED_LIBS=ON/OFF
-DENABLE_LOG=ON/OFF
-DENABLE_LTO=ON/OFF
-DDISABLE_IOURING=ON/OFF
-DBUILD_MODULE_EXAMPLES=ON/OFF
```

`BUILD_MODULE_EXAMPLES` 需要 CMake >= 3.28 且建议使用 Ninja/Visual Studio 生成器。

## 依赖

C++23 编译器、CMake 3.16+、OpenSSL（1.1.1+）、galay-kernel。

启用日志时需要 spdlog；Linux 如启用 io_uring 需要 `liburing`。

## 项目地址

[https://github.com/gzj-creator/galay-ssl](https://github.com/gzj-creator/galay-ssl)
