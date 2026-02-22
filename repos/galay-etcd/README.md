# galay-etcd 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-etcd.html` for AI vector indexing.

## 概览

galay-etcd 是 Galay 库体系的 etcd v3 客户端组件，提供 KV、租约、前缀与 pipeline 操作。

它用于配置中心与服务发现访问层，集群治理和权限策略由外部系统负责。

## 架构

- **AsyncEtcdClient** — 底层协程客户端，封装 v3 HTTP/JSON 请求与响应解析
- **EtcdClient（sync wrapper）** — 面向业务侧的会话封装，暴露 `put/get/del/lease/pipeline`
- **PipelineOp** — 对应 etcd txn success ops，支持 Put/Get/Del 组合提交
- **状态回读** — 通过 `lastKeyValues/lastLeaseId/lastDeletedCount` 获取最近结果

## 核心 API

### 最小 Smoke 流程（test/T1-EtcdSmoke.cc）

```cpp
#include "galay-etcd/sync/EtcdClient.h"

using namespace galay::etcd;

Coroutine run(IOScheduler* scheduler) {
    EtcdConfig cfg;
    cfg.endpoint = "http://127.0.0.1:2379";
    cfg.api_prefix = "/v3";
    EtcdClient session(scheduler, cfg);

    co_await session.connect();
    co_await session.put("/galay/key", "value");
    co_await session.get("/galay/key");
    co_await session.del("/galay/key");
    co_await session.grantLease(3);
    co_await session.close();
}
```

### 前缀与 Pipeline（API 对齐）

```cpp
// 前缀查询：get(key, prefix=true)
co_await session.get("/services/app/", true);

// 前缀删除：del(key, prefix=true)
co_await session.del("/services/app/", true);

// Pipeline：提交 Put/Get/Del 组合
std::vector ops;
ops.push_back(EtcdClient::PipelineOp::Put("/k1", "v1"));
ops.push_back(EtcdClient::PipelineOp::Get("/k1"));
ops.push_back(EtcdClient::PipelineOp::Del("/k1"));
co_await session.pipeline(std::move(ops));
```

### 测试入口（与仓库一致）

- `T1-EtcdSmoke` — KV + lease 生命周期
- `T2-EtcdPrefixOps` — 前缀范围与删除
- `T3-EtcdPipeline` — txn success ops 管道
- `B1-EtcdKvBenchmark` — KV 压测

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

# 功能测试
./build/test/T1-EtcdSmoke http://127.0.0.1:2379
./build/test/T2-EtcdPrefixOps http://127.0.0.1:2379
./build/test/T3-EtcdPipeline http://127.0.0.1:2379
```

### 构建选项

```text
-DGALAY_ETCD_BUILD_TESTS=ON/OFF
-DGALAY_ETCD_BUILD_BENCHMARKS=ON/OFF
-DGALAY_ETCD_BUILD_SHARED_LIBS=ON/OFF
-DGALAY_ETCD_ENABLE_IMPORT_COMPILATION=ON/OFF
-DGALAY_ETCD_INSTALL_MODULE_INTERFACE=ON/OFF
```

## 依赖

C++23 编译器、CMake 3.20+、simdjson（通过 pkg-config）、galay-kernel、galay-utils、galay-http、spdlog。

## 项目地址

[https://github.com/gzj-creator/galay-etcd](https://github.com/gzj-creator/galay-etcd)
