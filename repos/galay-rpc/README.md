# galay-rpc 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-rpc.html` for AI vector indexing.

## 概览

galay-rpc 是 Galay 库体系的服务通信组件，提供 unary/stream 调用模型与协程化客户端/服务端接口。

它负责消息传输、超时与连接管理，服务治理策略可按业务场景扩展。

## 架构

- **RpcService** — 以服务名+方法名注册处理器，统一四种调用模式
- **RpcServer** — 负责连接管理、请求分发与响应回写
- **RpcClient** — 提供 unary / stream 调用接口与超时控制
- **ServiceDiscovery** — 注册发现抽象（内置本地实现与 Concept 约束）

## 核心 API

### 服务注册（example/include/E1-EchoServer.cpp）

```
#include "galay-rpc/kernel/RpcServer.h"
#include "galay-rpc/kernel/RpcService.h"

using namespace galay::rpc;

class EchoService : public RpcService {
public:
    EchoService() : RpcService("EchoService") {
        registerMethod("echo", &EchoService::echo);
        registerClientStreamingMethod("echo", &EchoService::echo);
        registerServerStreamingMethod("echo", &EchoService::echo);
        registerBidiStreamingMethod("echo", &EchoService::echo);
    }

    Coroutine echo(RpcContext& ctx) {
        ctx.setPayload(ctx.request().payloadView());
        co_return;
    }
};

int main() {
    auto service = std::make_shared();
    RpcServerConfig config;
    config.host = "0.0.0.0";
    config.port = 9000;
    RpcServer server(config);
    server.registerService(service);
    server.start();
    return 0;
}
```

### 客户端调用（example/include/E2-EchoClient.cpp）

```
#include "galay-rpc/kernel/RpcClient.h"

Coroutine runClient() {
    RpcClient client;
    co_await client.connect("127.0.0.1", 9000);

    auto unary = co_await client.call("EchoService", "echo", "hello");
    auto bidi = co_await client.callBidiStreamFrame(
        "EchoService", "echo", "hello", 5, true);

    co_await client.close();
}
```

### 示例入口（与仓库一致）

- `E1/E2` — Echo（四模式：unary/client_stream/server_stream/bidi）
- `E3/E4` — 真实流式（STREAM_INIT/STREAM_DATA/STREAM_END）
- 源码路径：`example/include/` 与 `example/import/`

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
-DBUILD_MODULE_EXAMPLES=ON/OFF
-DGALAY_RPC_INSTALL_MODULE_INTERFACE=ON/OFF
```

`BUILD_MODULE_EXAMPLES` 需要 CMake >= 3.28，推荐 Ninja/Visual Studio 生成器。

## 依赖

C++23 编译器、CMake 3.16+、spdlog、galay-kernel（CMake 中为必需依赖）。

服务发现默认提供本地注册中心；远端注册中心按业务侧扩展接入。

## 项目地址

[https://github.com/gzj-creator/galay-rpc](https://github.com/gzj-creator/galay-rpc)
