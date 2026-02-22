# galay-mongo 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-mongo.html` for AI vector indexing.

## 概览

galay-mongo 是 Galay 库体系的 MongoDB 客户端组件，覆盖 OP_MSG、BSON、同步/异步与 pipeline 请求。

它负责协议通信与认证流程，集合结构设计和高级查询封装由应用层实现。

## 架构

- **MongoClient（sync）** — 同步会话接口，覆盖 `connect/ping/find/insert/update/delete`
- **AsyncMongoClient（async）** — 协程接口，支持 Pipeline 并发请求
- **MongoDocument** — 文档构造与 BSON 编解码核心结构
- **认证路径** — 同步与异步连接都支持 SCRAM-SHA-256

## 核心 API

### 同步 Ping（example/include/E1-SyncPing.cc）

```cpp
#include "galay-mongo/sync/MongoClient.h"

using namespace galay::mongo;

int main() {
    MongoClient session;

    MongoConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 27017;
    cfg.database = "admin";

    auto connected = session.connect(cfg);
    if (!connected) return 1;

    auto ping = session.ping(cfg.database);
    if (!ping) return 1;

    session.close();
    return 0;
}
```

### 同步 CRUD（example/include/E3-SyncCrud.cc）

```cpp
#include "galay-mongo/sync/MongoClient.h"

MongoClient session;
MongoConfig cfg;
cfg.database = "admin";
session.connect(cfg);

MongoDocument doc;
doc.append("_id", int64_t(1));
doc.append("name", "sync-example");
session.insertOne(cfg.database, "items", doc);

MongoDocument filter;
filter.append("_id", int64_t(1));
session.findOne(cfg.database, "items", filter);
session.deleteOne(cfg.database, "items", filter);
```

### 异步 Pipeline（example/include/E4-AsyncPipeline.cc）

```cpp
Coroutine run(IOScheduler* scheduler, MongoConfig cfg, AsyncMongoConfig async_cfg) {
    AsyncMongoClient client(scheduler, async_cfg);
    co_await client.connect(cfg);

    std::vector commands;
    MongoDocument c1; c1.append("ping", int32_t(1));
    MongoDocument c2; c2.append("hello", int32_t(1));
    commands.push_back(std::move(c1));
    commands.push_back(std::move(c2));

    auto result = co_await client.pipeline(cfg.database, std::move(commands));
    co_await client.close();
}
```

### 示例入口（与仓库一致）

- `E1-SyncPing`、`E2-AsyncPing`
- `E3-SyncCrud`、`E4-AsyncPipeline`、`E5-AsyncCommandCrud`
- 源码路径：`example/include/` 与 `example/import/`

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
-DGALAY_MONGO_BUILD_TESTS=ON/OFF
-DGALAY_MONGO_BUILD_EXAMPLES=ON/OFF
-DGALAY_MONGO_BUILD_BENCHMARKS=ON/OFF
-DGALAY_MONGO_BUILD_SHARED_LIBS=ON/OFF
-DGALAY_MONGO_ENABLE_IMPORT_COMPILATION=ON/OFF
-DGALAY_MONGO_BUILD_MODULE_EXAMPLES=ON/OFF
```

## 依赖

C++23 编译器、CMake 3.20+、OpenSSL、spdlog、galay-kernel。

运行示例/测试需要可访问的 MongoDB 实例。

## 项目地址

[https://github.com/gzj-creator/galay-mongo](https://github.com/gzj-creator/galay-mongo)
