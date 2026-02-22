# galay-mcp 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-mcp.html` for AI vector indexing.

## 概览

galay-mcp 是 Galay 库体系的 MCP 接入组件，支持 stdio/HTTP 传输与工具、资源、提示词暴露。

它专注协议对接与工具桥接，不承担模型推理和业务工作流编排。

## 架构

- **McpStdioServer / McpStdioClient** — 面向本地 Agent 的 stdin/stdout 传输
- **McpHttpServer / McpHttpClient** — 面向远程服务化的 HTTP 传输
- **SchemaBuilder** — 工具参数 schema 构建器
- **simdjson + JsonWriter** — 协议 JSON 解析与序列化主链路

## 核心 API

### Stdio 工具注册（example/common/E1-BasicStdioUsageMain.inc）

```cpp
#include "galay-mcp/server/McpStdioServer.h"
#include "galay-mcp/common/McpSchemaBuilder.h"

using namespace galay::mcp;

McpStdioServer server;
server.setServerInfo("example-server", "1.0.0");

auto schema = SchemaBuilder()
    .addString("message", "要回显的消息", true)
    .build();

server.addTool(
    "echo",
    "回显输入消息",
    schema,
    [](const JsonElement& args) -> std::expected {
        // 解析参数并返回 JsonString（完整逻辑见 E1 示例）
        JsonWriter writer;
        writer.StartObject();
        writer.Key("ok");
        writer.Bool(true);
        writer.EndObject();
        return writer.TakeString();
    });

server.run();
```

### HTTP 传输（example/common/E2-BasicHttpUsageMain.inc）

```cpp
#include "galay-mcp/server/McpHttpServer.h"
#include "galay-mcp/client/McpHttpClient.h"

McpHttpServer server("0.0.0.0", 8080);
// addTool / addResource / addPrompt 与 stdio 版本一致
server.start();

// 客户端侧（在协程中）：
// McpHttpClient client(scheduler);
// co_await client.connect("http://127.0.0.1:8080/mcp");
```

### 示例入口（与仓库一致）

- `E1-BasicStdioUsage` — `example/include/E1-BasicStdioUsage.cc`
- `E2-BasicHttpUsage` — `example/include/E2-BasicHttpUsage.cc`
- import 对应：`example/import/` 同名示例

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
```

`BUILD_MODULE_EXAMPLES` 需要 CMake >= 3.28 且推荐 Ninja/Visual Studio 生成器。

## 依赖

C++23 编译器、CMake 3.20+、simdjson（必需）。

HTTP 传输链路会按环境探测并链接 galay-http 与 galay-kernel（若可用）。

## 项目地址

[https://github.com/gzj-creator/galay-mcp](https://github.com/gzj-creator/galay-mcp)
