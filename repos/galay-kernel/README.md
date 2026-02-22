# galay-kernel 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-kernel.html` for AI vector indexing.

## 概览

galay-kernel 是 Galay 库体系的运行时基座，提供协程调度、事件循环与跨平台异步 IO 能力。

它面向执行层性能与并发模型，不负责上层协议语义和业务编排。

## 架构

- **Runtime** — 管理 IO/Compute 调度器生命周期，并通过 `getNextIOScheduler()` 分配协程执行位点
- **Coroutine / Awaitable** — 统一 `co_await` 异步风格，覆盖网络、文件、同步原语与定时器
- **Scheduler** — IO 调度与计算调度解耦，支持多调度器并行
- **多后端 IO** — macOS 使用 `kqueue`；Linux 在 `epoll/io_uring` 间按配置选择

## 核心 API

### 最小示例（example/include/E4-CoroutineBasic.cc）

```cpp
#include "galay-kernel/kernel/Coroutine.h"
#include "galay-kernel/kernel/ComputeScheduler.h"

using namespace galay::kernel;

Coroutine simpleTask(int id) {
    // 业务逻辑
    co_return;
}

int main() {
    ComputeScheduler scheduler;
    scheduler.start();
    scheduler.spawn(simpleTask(1));
    scheduler.stop();
    return 0;
}
```

### 示例入口（与仓库一致）

- `E1-SendfileExample` — `example/include/E1-SendfileExample.cc`
- `E2-TcpEchoServer` — `example/include/E2-TcpEchoServer.cc`
- `E3-TcpClient` — `example/include/E3-TcpClient.cc`
- `E4-CoroutineBasic` — `example/include/E4-CoroutineBasic.cc`
- `E5-UdpEcho` — `example/include/E5-UdpEcho.cc`

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
-DBUILD_SHARED_LIBS=ON/OFF
-DENABLE_LOG=ON/OFF
-DDISABLE_IOURING=ON/OFF
-DENABLE_CPP23_MODULES=ON/OFF
```

`ENABLE_CPP23_MODULES` 需要 CMake >= 3.28，并建议使用 Ninja/Visual Studio 生成器；不满足条件会被禁用。

## 依赖

C++23 编译器、CMake 3.16+。日志开启时使用 spdlog。

Linux 下按 IO 后端需要 `libaio`（epoll 文件 IO）或 `liburing`（io_uring）。

## 项目地址

[https://github.com/gzj-creator/galay-kernel](https://github.com/gzj-creator/galay-kernel)
