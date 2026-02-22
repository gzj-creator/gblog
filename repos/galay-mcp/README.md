# Galay MCP

基于 Galay-Kernel 框架实现的 MCP (Model Context Protocol) 协议库。

## 文档导航

建议按以下顺序阅读：

1. [标准输入输出MCP测试](docs/02-标准输入输出MCP测试.md)
2. [Stdio服务器测试](docs/03-Stdio服务器测试.md)
3. [HTTP客户端测试](docs/05-HTTP客户端测试.md)
4. [HTTP服务器测试](docs/06-HTTP服务器测试.md)
5. [性能测试总览](docs/04-性能测试.md)

## 📁 项目结构

```
galay-mcp/
├── CMakeLists.txt              # 根项目配置
├── README.md                   # 项目说明（本文件）
├── galay-mcp/                  # 核心库
│   ├── CMakeLists.txt          # 库构建配置
│   ├── module/                 # C++23 命名模块接口（galay.mcp.cppm）
│   ├── common/                 # 通用模块
│   │   ├── McpBase.h           # 基础数据结构
│   │   ├── McpError.h          # 错误处理
│   │   └── McpError.cc         # 错误处理实现
│   ├── client/                 # 客户端实现
│   │   ├── McpStdioClient.h    # 标准输入输出客户端
│   │   └── McpStdioClient.cc   # 标准输入输出客户端实现
│   └── server/                 # 服务器实现
│       ├── McpStdioServer.h    # 标准输入输出服务器
│       └── McpStdioServer.cc   # 标准输入输出服务器实现
├── example/                    # 示例
│   ├── common/                 # include/import 共用示例主体
│   ├── include/                # #include 版本示例
│   └── import/                 # import 版本示例
├── test/                       # 测试
│   ├── CMakeLists.txt
│   ├── T1-StdioClient.cc
│   └── ...
├── benchmark/                  # 性能测试
├── docs/                       # 文档
├── scripts/                    # 脚本
│   ├── run.sh                  # 运行脚本
│   └── check.sh                # 检查脚本
└── todo/                       # 待办事项
```

## ✨ 特性

- ✅ **标准输入输出**：支持基于 stdin/stdout 的 MCP 通信
- ✅ **简洁易用**：提供简洁的 API 接口
- ✅ **类型安全**：使用 C++23 和 std::expected 进行错误处理
- ✅ **标准兼容**：遵循 MCP 2024-11-05 规范
- ✅ **高性能**：基于 Galay-Kernel 框架的高效实现
- ✅ **HTTP 传输**：已支持（基于 Galay-HTTP）

## 📦 依赖

- C++23 编译器（GCC 13+, Clang 16+）
- [galay-kernel](https://github.com/gzj-creator/galay-kernel)
- [galay-utils](https://github.com/gzj-creator/galay-utils)
- [galay-http](https://github.com/gzj-creator/galay-http)（HTTP 传输场景）
- [simdjson](https://github.com/simdjson/simdjson) JSON 解析库

## 🔧 构建

### 前置要求

先安装基础依赖（`simdjson` 为必需，`galay-http` 为 HTTP 传输场景推荐）：

```bash
# macOS (Homebrew)
brew install cmake simdjson

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y cmake g++ libsimdjson-dev
```

统一联调推荐拉取：

```bash
git clone https://github.com/gzj-creator/galay-kernel.git
git clone https://github.com/gzj-creator/galay-utils.git
git clone https://github.com/gzj-creator/galay-http.git
git clone https://github.com/gzj-creator/galay-mcp.git
```

### 编译步骤

```bash
# 1. 创建构建目录
mkdir build && cd build

# 2. 配置 CMake
cmake ..

# 3. 编译
cmake --build . --parallel

# 4. （可选）安装到系统
sudo cmake --install .
```

### 构建选项

```bash
# 不构建测试
cmake -DBUILD_TESTS=OFF ..

# 不构建性能测试
cmake -DBUILD_BENCHMARKS=OFF ..

# 构建 C++23 module(import/export) 示例（支持环境会自动开启）
cmake -DBUILD_MODULE_EXAMPLES=ON ..

# 安装到系统
cmake --build . --target install
```

### C++23 模块（import/export）

- 模块接口文件统一为 `.cppm`，当前接口：`galay-mcp/module/galay.mcp.cppm`
- import 示例目标：`E1-BasicStdioUsageImport`、`E2-BasicHttpUsageImport`
- 构建限制：
  - 需要 CMake `>= 3.28`
  - 生成器需为 `Ninja` 或 `Visual Studio`
  - Clang 工具链需要 `clang-scan-deps`
  - 不满足条件时，`BUILD_MODULE_EXAMPLES` 会自动降级为 `OFF`，不影响 include 版本构建

```cpp
import galay.mcp;
```

```bash
cmake -S . -B build-mod -G Ninja -DBUILD_MODULE_EXAMPLES=ON
cmake --build build-mod --parallel
```

### 模块支持更新（2026-02）

本次模块接口已统一为：

- `module;`
- `#include "galay-mcp/module/ModulePrelude.hpp"`
- `export module galay.mcp;`
- `export { #include ... }`

对应文件：

- `galay-mcp/module/galay.mcp.cppm`
- `galay-mcp/module/ModulePrelude.hpp`

推荐构建命令（Clang 20）：

```bash
cmake -S . -B build-mod -G Ninja \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm@20/bin/clang++ \
  -DBUILD_MODULE_EXAMPLES=ON
cmake --build build-mod --target galay-mcp-modules --parallel
```

## 🚀 快速开始

### 服务器端（标准输入输出）

```cpp
#include "galay-mcp/server/McpStdioServer.h"
#include "galay-mcp/common/McpSchemaBuilder.h"

McpStdioServer server;

// 添加工具
auto schema = SchemaBuilder()
    .addNumber("a", "First number", true)
    .addNumber("b", "Second number", true)
    .build();

server.addTool("add", "Add two numbers", schema,
    [](const JsonElement& args) -> std::expected<JsonString, McpError> {
        JsonObject obj;
        if (!JsonHelper::GetObject(args, obj)) {
            return std::unexpected(McpError::invalidParams("Invalid arguments"));
        }

        auto aVal = obj["a"];
        auto bVal = obj["b"];
        if (aVal.error() || bVal.error()) {
            return std::unexpected(McpError::invalidParams("Missing parameters"));
        }

        double a = aVal.is_double() ? aVal.get_double().value() : static_cast<double>(aVal.get_int64().value());
        double b = bVal.is_double() ? bVal.get_double().value() : static_cast<double>(bVal.get_int64().value());

        JsonWriter writer;
        writer.StartObject();
        writer.Key("result");
        writer.Number(a + b);
        writer.EndObject();
        return writer.TakeString();
    }
);

// 启动服务器（从 stdin 读取，向 stdout 写入）
server.run();
```

### 客户端（标准输入输出）

```cpp
#include "galay-mcp/client/McpStdioClient.h"

McpStdioClient client;

// 初始化连接
auto init_result = client.initialize("MyClient", "1.0.0");
if (!init_result) {
    // 处理错误
}

// 调用工具
JsonWriter argsWriter;
argsWriter.StartObject();
argsWriter.Key("a");
argsWriter.Number(static_cast<int64_t>(10));
argsWriter.Key("b");
argsWriter.Number(static_cast<int64_t>(20));
argsWriter.EndObject();
auto result = client.callTool("add", argsWriter.TakeString());
if (result) {
    std::cout << "Result: " << result.value() << std::endl;
}
```

## 🧪 运行测试

```bash
cd build

# 运行单元测试
./bin/test_stdio_server
./bin/test_stdio_client

# 运行集成测试（通过管道连接）
./bin/test_stdio_server | ./bin/test_stdio_client
```

## 📖 协议格式

### 标准输入输出协议

- **传输**: stdin/stdout
- **格式**: JSON-RPC 2.0
- **分隔**: 每条消息一行（换行符分隔）

### 请求示例

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":10,"b":20}}}
```

### 响应示例

```json
{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"30"}]}}
```

## 📚 API 文档

> 说明：`JsonString` 为原始 JSON 字符串，`JsonElement` 为 simdjson 的只读 DOM 视图。

### McpStdioServer

```cpp
class McpStdioServer {
public:
    // 添加工具
    void addTool(const std::string& name,
                 const std::string& description,
                 const JsonString& inputSchema,
                 ToolHandler handler);

    // 添加资源
    void addResource(const std::string& uri,
                     const std::string& name,
                     const std::string& mimeType);

    // 添加提示
    void addPrompt(const std::string& name,
                   const std::string& description,
                   const std::vector<PromptArgument>& arguments,
                   PromptGetter getter);

    // 运行服务器（阻塞）
    void run();

    // 停止服务器
    void stop();
};
```

### McpStdioClient

```cpp
class McpStdioClient {
public:
    // 初始化连接
    std::expected<void, McpError> initialize(
        const std::string& clientName,
        const std::string& clientVersion);

    // 调用工具
    std::expected<JsonString, McpError> callTool(
        const std::string& toolName,
        const JsonString& arguments);

    // 获取工具列表
    std::expected<std::vector<Tool>, McpError> listTools();

    // 获取资源列表
    std::expected<std::vector<Resource>, McpError> listResources();

    // 断开连接
    void disconnect();
};
```

## 🏗️ 架构设计

```
应用层：McpStdioClient/Server（标准输入输出实现）
    ↓
协议层：MCP JSON-RPC 2.0 消息处理
    ↓
编解码：simdjson（解析）+ JsonWriter（序列化）
    ↓
传输层：stdin/stdout（标准输入输出流）
```

## 🔍 示例代码

完整示例请查看：
- [test/T1-StdioClient.cc](test/T1-StdioClient.cc) - Stdio 客户端示例
- [test/T2-StdioServer.cc](test/T2-StdioServer.cc) - Stdio 服务器示例
- [test/T3-HttpClient.cc](test/T3-HttpClient.cc) - HTTP 客户端示例
- [test/T4-HttpServer.cc](test/T4-HttpServer.cc) - HTTP 服务器示例

## 🛣️ 开发路线图

- [x] 标准输入输出传输层实现
- [x] 基础 MCP 协议支持
- [x] 简化 API 设计
- [ ] 完整的单元测试
- [ ] 性能测试和优化
- [x] HTTP 传输支持（基于 Galay-HTTP）
- [ ] WebSocket 传输支持
- [ ] 文档完善

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🙏 致谢

本项目基于以下优秀开源项目：
- [galay-kernel](https://github.com/gzj-creator/galay-kernel) - 高性能 C++ 框架
- [simdjson](https://github.com/simdjson/simdjson) - JSON 解析库
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol 规范
