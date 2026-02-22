# galay-mysql 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-mysql.html` for AI vector indexing.

## 概览

galay-mysql 是 Galay 库体系的 MySQL 客户端组件，提供同步/异步查询、预处理与事务支持。

它聚焦协议连接与执行链路，SQL 设计和 ORM 抽象由业务侧决定。

## 架构

- **AsyncMysqlClient** — 协程异步路径，使用 Awaitable 处理连接与查询
- **MysqlClient** — 同步阻塞路径，便于脚本化和简单服务接入
- **MysqlResultSet** — 结果集读取接口，支持行列访问
- **预处理与事务** — 提供 `prepare/stmtExecute` 与 `beginTransaction/commit/rollback`

## 核心 API

### 异步查询（example/include/E1-AsyncQuery.cc）

```cpp
#include "galay-mysql/async/AsyncMysqlClient.h"
#include
#include
#include

using namespace galay::mysql;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    AsyncMysqlClient client(scheduler);

    auto& conn_aw = client.connect("127.0.0.1", 3306, "root", "password", "test");
    std::expected, MysqlError> conn;
    do {
        conn = co_await conn_aw;
        if (!conn) co_return;
    } while (!conn->has_value());

    auto& query_aw = client.query("SELECT 1");
    std::expected, MysqlError> result;
    do {
        result = co_await query_aw;
        if (!result) co_return;
    } while (!result->has_value());

    co_await client.close();
}
```

### 同步预处理与事务（example/include/E4-SyncPreparedTx.cc）

```cpp
#include "galay-mysql/sync/MysqlClient.h"

MysqlClient session;
session.connect("127.0.0.1", 3306, "root", "password", "test");
session.beginTransaction();

auto prep = session.prepare("SELECT ? + ?");
std::vector> params = {"3", "5"};
auto exec = session.stmtExecute(prep->statement_id, params);

session.stmtClose(prep->statement_id);
session.commit();
session.close();
```

### 示例入口（与仓库一致）

- `E1-AsyncQuery` — 异步查询
- `E2-SyncQuery` — 同步查询
- `E3-AsyncPool` — 异步连接池
- `E4-SyncPreparedTx` — 预处理 + 事务
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
-DGALAY_MYSQL_BUILD_TESTS=ON/OFF
-DGALAY_MYSQL_BUILD_EXAMPLES=ON/OFF
-DGALAY_MYSQL_BUILD_SHARED_LIBS=ON/OFF
-DGALAY_MYSQL_ENABLE_IMPORT_COMPILATION=ON/OFF
-DGALAY_MYSQL_BUILD_MODULE_EXAMPLES=ON/OFF
```

## 依赖

C++23 编译器、CMake 3.20+、OpenSSL、spdlog、galay-kernel。

运行示例/测试需要可访问的 MySQL 5.7+ / 8.0+ 实例（推荐 8.0）。

## 项目地址

[https://github.com/gzj-creator/galay-mysql](https://github.com/gzj-creator/galay-mysql)
