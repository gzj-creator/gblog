# galay-redis 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-redis.html` for AI vector indexing.

## 概览

galay-redis 是 Galay 库体系的 Redis 客户端组件，提供协程命令、同步会话与 pipeline 能力。

它聚焦 RESP 通信与高并发访问，不涉及 Redis 服务端运维和数据建模策略。

## 架构

- **RedisClient（async）** — 协程命令接口，返回 Awaitable 并支持超时链式配置
- **RedisSession（sync）** — 同步阻塞接口，便于脚本或简单场景接入
- **RedisPipelineAwaitable** — 批量命令单次往返，降低 RTT 开销
- **拓扑与连接池** — 提供 `RedisConnectionPool` 与 `RedisTopologyClient` 扩展能力

## 核心 API

### 最小异步示例（README 快速开始）

```
#include "galay-redis/async/RedisClient.h"
#include 

using namespace galay::redis;
using namespace galay::kernel;

Coroutine example(IOScheduler* scheduler) {
    RedisClient client(scheduler);
    co_await client.connect("127.0.0.1", 6379);

    co_await client.set("key", "value").timeout(std::chrono::seconds(5));
    auto r = co_await client.get("key");
    if (r && r.value()) {
        auto& vals = r.value().value();
        // vals[0].toString()
    }

    co_await client.close();
}
```

### Pipeline 示例（async/RedisClient.h）

```
Coroutine pipelineExample(IOScheduler* scheduler) {
    RedisClient client(scheduler);
    co_await client.connect("127.0.0.1", 6379);

    std::vector> commands = {
        {"SET", "k1", "v1"},
        {"SET", "k2", "v2"},
        {"MGET", "k1", "k2"}
    };

    auto result = co_await client.pipeline(commands).timeout(std::chrono::seconds(10));
    co_await client.close();
}
```

### 测试与示例入口

- `test/test_redis_client_timeout.cc` — 超时与稳定性
- `test/test_redis_client_benchmark.cc` — 普通/管道压测
- `test/test_sync.cc`、`test/test_async.cc` — 同步与异步路径

## 构建

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

### 构建选项

```
-DGALAY_REDIS_ENABLE_IMPORT_COMPILATION=ON/OFF
-DGALAY_REDIS_INSTALL_MODULE_INTERFACE=ON/OFF
```

当前顶层 CMake 默认构建库与 test 目录，没有单独的 `BUILD_TESTS` 开关。

## 依赖

C++23 编译器、CMake 3.20+、galay-kernel、galay-utils、OpenSSL、spdlog。

## 项目地址

[https://github.com/gzj-creator/galay-redis](https://github.com/gzj-creator/galay-redis)
