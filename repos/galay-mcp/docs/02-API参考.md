# 02-API参考

本文档提供 Galay MCP 库的完整 API 参考。

## 命名空间

所有 API 都在 `galay::mcp` 命名空间下：

```cpp
namespace galay {
namespace mcp {
    // API 定义
}
}
```

## 服务器 API

### McpStdioServer

基于标准输入输出的 MCP 服务器。

#### 构造函数

```cpp
McpStdioServer();
~McpStdioServer();
```

#### 服务器配置

```cpp
void setServerInfo(const std::string& name, const std::string& version);
```

设置服务器名称和版本信息。

**参数**:
- `name`: 服务器名称
- `version`: 服务器版本

**示例**:
```cpp
server.setServerInfo("my-mcp-server", "1.0.0");
```

#### 工具管理

```cpp
void addTool(const std::string& name,
             const std::string& description,
             const JsonString& inputSchema,
             ToolHandler handler);
```

注册一个工具。

**参数**:
- `name`: 工具名称（唯一标识）
- `description`: 工具描述
- `inputSchema`: 输入参数的 JSON Schema
- `handler`: 工具处理函数

**ToolHandler 类型**:
```cpp
using ToolHandler = std::function<
    std::expected<JsonString, McpError>(const JsonElement&)
>;
```

**示例**:
```cpp
auto schema = SchemaBuilder()
    .addNumber("x", "First number", true)
    .addNumber("y", "Second number", true)
    .build();

server.addTool("multiply", "Multiply two numbers", schema,
    [](const JsonElement& args) -> std::expected<JsonString, McpError> {
        JsonObject obj;
        if (!JsonHelper::GetObject(args, obj)) {
            return std::unexpected(McpError::invalidParams("Invalid arguments"));
        }

        auto x = obj["x"];
        auto y = obj["y"];
        if (x.error() || y.error()) {
            return std::unexpected(McpError::invalidParams("Missing parameters"));
        }

        double xVal = x.is_double() ? x.get_double().value()
                                    : static_cast<double>(x.get_int64().value());
        double yVal = y.is_double() ? y.get_double().value()
                                    : static_cast<double>(y.get_int64().value());

        JsonWriter writer;
        writer.StartObject();
        writer.Key("result");
        writer.Number(xVal * yVal);
        writer.EndObject();
        return writer.TakeString();
    }
);
```

#### 资源管理

```cpp
void addResource(const std::string& uri,
                 const std::string& name,
                 const std::string& description,
                 const std::string& mimeType,
                 ResourceReader reader);
```

注册一个资源。

**参数**:
- `uri`: 资源 URI（唯一标识）
- `name`: 资源名称
- `description`: 资源描述
- `mimeType`: MIME 类型（如 "text/plain", "application/json"）
- `reader`: 资源读取函数

**ResourceReader 类型**:
```cpp
using ResourceReader = std::function<
    std::expected<std::string, McpError>(const std::string&)
>;
```

**示例**:
```cpp
server.addResource(
    "file:///config.json",
    "Configuration",
    "Application configuration file",
    "application/json",
    [](const std::string& uri) -> std::expected<std::string, McpError> {
        std::ifstream file("config.json");
        if (!file) {
            return std::unexpected(McpError::internalError("File not found"));
        }
        std::string content((std::istreambuf_iterator<char>(file)),
                           std::istreambuf_iterator<char>());
        return content;
    }
);
```

#### 提示管理

```cpp
void addPrompt(const std::string& name,
               const std::string& description,
               const std::vector<PromptArgument>& arguments,
               PromptGetter getter);
```

注册一个提示。

**参数**:
- `name`: 提示名称（唯一标识）
- `description`: 提示描述
- `arguments`: 参数定义列表
- `getter`: 提示获取函数

**PromptGetter 类型**:
```cpp
using PromptGetter = std::function<
    std::expected<JsonString, McpError>(const std::string&, const JsonElement&)
>;
```

**示例**:
```cpp
auto args = PromptArgumentBuilder()
    .addArgument("topic", "Essay topic", true)
    .addArgument("length", "Word count", false)
    .build();

server.addPrompt("write_essay", "Generate essay prompt", args,
    [](const std::string& name, const JsonElement& args)
    -> std::expected<JsonString, McpError> {
        JsonObject obj;
        if (!JsonHelper::GetObject(args, obj)) {
            return std::unexpected(McpError::invalidParams("Invalid arguments"));
        }

        std::string topic;
        auto topicVal = obj["topic"];
        if (topicVal.error() || !JsonHelper::GetString(topicVal.value(), topic)) {
            return std::unexpected(McpError::invalidParams("Missing topic"));
        }

        JsonWriter writer;
        writer.StartObject();
        writer.Key("prompt");
        writer.String("Write an essay about: " + topic);
        writer.EndObject();
        return writer.TakeString();
    }
);
```

#### 服务器控制

```cpp
void run();
void stop();
bool isRunning() const;
```

- `run()`: 启动服务器（阻塞，直到调用 `stop()` 或 stdin 关闭）
- `stop()`: 停止服务器
- `isRunning()`: 检查服务器是否正在运行

**示例**:
```cpp
// 主线程
server.run();

// 其他线程
server.stop();
```

### McpHttpServer

基于 HTTP 的 MCP 服务器。

#### 构造函数

```cpp
McpHttpServer(const std::string& host = "0.0.0.0", int port = 8080);
~McpHttpServer();
```

**参数**:
- `host`: 监听地址
- `port`: 监听端口

#### 服务器配置

```cpp
void setServerInfo(const std::string& name, const std::string& version);
```

同 `McpStdioServer::setServerInfo()`。

#### 工具管理

```cpp
void addTool(const std::string& name,
             const std::string& description,
             const JsonString& inputSchema,
             ToolHandler handler);
```

**ToolHandler 类型**（协程版本）:
```cpp
using ToolHandler = std::function<
    kernel::Coroutine(const JsonElement&, std::expected<JsonString, McpError>&)
>;
```

**示例**:
```cpp
server.addTool("async_fetch", "Fetch data asynchronously", schema,
    [](const JsonElement& args, std::expected<JsonString, McpError>& result)
    -> kernel::Coroutine {
        // 异步操作
        auto data = co_await fetchDataAsync();

        JsonWriter writer;
        writer.StartObject();
        writer.Key("data");
        writer.String(data);
        writer.EndObject();
        result = writer.TakeString();
    }
);
```

#### 资源管理

```cpp
void addResource(const std::string& uri,
                 const std::string& name,
                 const std::string& description,
                 const std::string& mimeType,
                 ResourceReader reader);
```

**ResourceReader 类型**（协程版本）:
```cpp
using ResourceReader = std::function<
    kernel::Coroutine(const std::string&, std::expected<std::string, McpError>&)
>;
```

#### 提示管理

```cpp
void addPrompt(const std::string& name,
               const std::string& description,
               const std::vector<PromptArgument>& arguments,
               PromptGetter getter);
```

**PromptGetter 类型**（协程版本）:
```cpp
using PromptGetter = std::function<
    kernel::Coroutine(const std::string&, const JsonElement&,
                     std::expected<JsonString, McpError>&)
>;
```

#### 服务器控制

```cpp
void start();
void stop();
bool isRunning() const;
```

- `start()`: 启动服务器（非阻塞）
- `stop()`: 停止服务器
- `isRunning()`: 检查服务器是否正在运行

**注意**: 必须在 `start()` 之前完成所有工具、资源和提示的注册。

## 客户端 API

### McpStdioClient

基于标准输入输出的 MCP 客户端。

#### 构造函数

```cpp
McpStdioClient();
~McpStdioClient();
```

#### 连接管理

```cpp
std::expected<void, McpError> initialize(
    const std::string& clientName,
    const std::string& clientVersion
);

void disconnect();
bool isInitialized() const;
```

- `initialize()`: 初始化连接并完成握手
- `disconnect()`: 断开连接
- `isInitialized()`: 检查是否已初始化

**示例**:
```cpp
McpStdioClient client;

auto result = client.initialize("my-client", "1.0.0");
if (!result) {
    std::cerr << "Initialize failed: " << result.error().message() << '\n';
    return 1;
}

// 使用客户端...

client.disconnect();
```

#### 服务器信息

```cpp
const ServerInfo& getServerInfo() const;
const ServerCapabilities& getServerCapabilities() const;
```

- `getServerInfo()`: 获取服务器信息（名称、版本）
- `getServerCapabilities()`: 获取服务器能力（支持的功能）

**示例**:
```cpp
auto info = client.getServerInfo();
std::cout << "Server: " << info.name << " v" << info.version << '\n';

auto caps = client.getServerCapabilities();
if (caps.tools) {
    std::cout << "Server supports tools\n";
}
```

#### 工具操作

```cpp
std::expected<std::vector<Tool>, McpError> listTools();

std::expected<JsonString, McpError> callTool(
    const std::string& toolName,
    const JsonString& arguments
);
```

- `listTools()`: 获取可用工具列表
- `callTool()`: 调用指定工具

**示例**:
```cpp
// 列出工具
auto tools = client.listTools();
if (tools) {
    for (const auto& tool : *tools) {
        std::cout << tool.name << ": " << tool.description << '\n';
    }
}

// 调用工具
JsonWriter argsWriter;
argsWriter.StartObject();
argsWriter.Key("x");
argsWriter.Number(10);
argsWriter.Key("y");
argsWriter.Number(20);
argsWriter.EndObject();

auto result = client.callTool("multiply", argsWriter.TakeString());
if (result) {
    std::cout << "Result: " << result.value() << '\n';
} else {
    std::cerr << "Error: " << result.error().message() << '\n';
}
```

#### 资源操作

```cpp
std::expected<std::vector<Resource>, McpError> listResources();

std::expected<std::string, McpError> readResource(
    const std::string& uri
);
```

- `listResources()`: 获取可用资源列表
- `readResource()`: 读取指定资源

**示例**:
```cpp
// 列出资源
auto resources = client.listResources();
if (resources) {
    for (const auto& res : *resources) {
        std::cout << res.uri << ": " << res.name << '\n';
    }
}

// 读取资源
auto content = client.readResource("file:///config.json");
if (content) {
    std::cout << "Content: " << content.value() << '\n';
}
```

#### 提示操作

```cpp
std::expected<std::vector<Prompt>, McpError> listPrompts();

std::expected<JsonString, McpError> getPrompt(
    const std::string& name,
    const JsonString& arguments
);
```

- `listPrompts()`: 获取可用提示列表
- `getPrompt()`: 获取指定提示

**示例**:
```cpp
// 列出提示
auto prompts = client.listPrompts();
if (prompts) {
    for (const auto& prompt : *prompts) {
        std::cout << prompt.name << ": " << prompt.description << '\n';
    }
}

// 获取提示
JsonWriter argsWriter;
argsWriter.StartObject();
argsWriter.Key("topic");
argsWriter.String("Climate Change");
argsWriter.EndObject();

auto prompt = client.getPrompt("write_essay", argsWriter.TakeString());
if (prompt) {
    std::cout << "Prompt: " << prompt.value() << '\n';
}
```

#### 心跳检测

```cpp
std::expected<void, McpError> ping();
```

发送心跳请求，检查连接状态。

**示例**:
```cpp
auto result = client.ping();
if (result) {
    std::cout << "Server is alive\n";
} else {
    std::cerr << "Ping failed: " << result.error().message() << '\n';
}
```

### McpHttpClient

基于 HTTP 的 MCP 客户端（异步协程模型）。

#### 构造函数

```cpp
explicit McpHttpClient(kernel::Runtime& runtime);
~McpHttpClient();
```

**参数**:
- `runtime`: Galay-Kernel 运行时实例

#### 连接管理

```cpp
async::ConnectAwaitable connect(const std::string& url);

kernel::Coroutine initialize(
    std::string clientName,
    std::string clientVersion,
    std::expected<void, McpError>& result
);

async::CloseAwaitable disconnect();

bool isConnected() const;
bool isInitialized() const;
```

**示例**:
```cpp
kernel::Coroutine run(kernel::Runtime& runtime) {
    McpHttpClient client(runtime);

    // 连接
    co_await client.connect("http://127.0.0.1:8080/mcp");

    // 初始化
    std::expected<void, McpError> init_result;
    co_await client.initialize("my-client", "1.0.0", init_result);

    if (!init_result) {
        std::cerr << "Initialize failed\n";
        co_return;
    }

    // 使用客户端...

    // 断开连接
    co_await client.disconnect();
}
```

#### 服务器信息

```cpp
const ServerInfo& getServerInfo() const;
const ServerCapabilities& getServerCapabilities() const;
```

同 `McpStdioClient`。

#### 工具操作

```cpp
kernel::Coroutine listTools(
    std::expected<std::vector<Tool>, McpError>& result
);

kernel::Coroutine callTool(
    std::string toolName,
    JsonString arguments,
    std::expected<JsonString, McpError>& result
);
```

**示例**:
```cpp
// 列出工具
std::expected<std::vector<Tool>, McpError> tools_result;
co_await client.listTools(tools_result);

if (tools_result) {
    for (const auto& tool : *tools_result) {
        std::cout << tool.name << '\n';
    }
}

// 调用工具
JsonWriter argsWriter;
argsWriter.StartObject();
argsWriter.Key("message");
argsWriter.String("Hello");
argsWriter.EndObject();

std::expected<JsonString, McpError> call_result;
co_await client.callTool("echo", argsWriter.TakeString(), call_result);

if (call_result) {
    std::cout << "Result: " << call_result.value() << '\n';
}
```

#### 资源操作

```cpp
kernel::Coroutine listResources(
    std::expected<std::vector<Resource>, McpError>& result
);

kernel::Coroutine readResource(
    std::string uri,
    std::expected<std::string, McpError>& result
);
```

#### 提示操作

```cpp
kernel::Coroutine listPrompts(
    std::expected<std::vector<Prompt>, McpError>& result
);

kernel::Coroutine getPrompt(
    std::string name,
    JsonString arguments,
    std::expected<JsonString, McpError>& result
);
```

#### 心跳检测

```cpp
kernel::Coroutine ping(std::expected<void, McpError>& result);
```

## 辅助类

### SchemaBuilder

JSON Schema 构建器，提供链式 API。

#### 方法

```cpp
SchemaBuilder& addString(const std::string& name,
                         const std::string& description,
                         bool required = false);

SchemaBuilder& addNumber(const std::string& name,
                         const std::string& description,
                         bool required = false);

SchemaBuilder& addInteger(const std::string& name,
                          const std::string& description,
                          bool required = false);

SchemaBuilder& addBoolean(const std::string& name,
                          const std::string& description,
                          bool required = false);

SchemaBuilder& addArray(const std::string& name,
                        const std::string& description,
                        const std::string& itemType = "string",
                        bool required = false);

SchemaBuilder& addObject(const std::string& name,
                         const std::string& description,
                         const JsonString& objectSchema,
                         bool required = false);

SchemaBuilder& addEnum(const std::string& name,
                       const std::string& description,
                       const std::vector<std::string>& enumValues,
                       bool required = false);

JsonString build() const;
```

**示例**:
```cpp
auto schema = SchemaBuilder()
    .addString("name", "User name", true)
    .addInteger("age", "User age", false)
    .addEnum("role", "User role", {"admin", "user", "guest"}, true)
    .addArray("tags", "User tags", "string", false)
    .build();
```

### PromptArgumentBuilder

提示参数构建器。

#### 方法

```cpp
PromptArgumentBuilder& addArgument(const std::string& name,
                                   const std::string& description,
                                   bool required = false);

std::vector<PromptArgument> build() const;
```

**示例**:
```cpp
auto args = PromptArgumentBuilder()
    .addArgument("topic", "Essay topic", true)
    .addArgument("length", "Word count", false)
    .addArgument("style", "Writing style", false)
    .build();
```

### McpError

错误类，封装 MCP 错误信息。

#### 方法

```cpp
int code() const;
const std::string& message() const;
const std::string& details() const;
```

#### 工厂方法

```cpp
static McpError parseError(const std::string& details);
static McpError invalidRequest(const std::string& details);
static McpError methodNotFound(const std::string& method);
static McpError invalidParams(const std::string& details);
static McpError internalError(const std::string& details);
static McpError custom(int code, const std::string& message,
                       const std::string& details = "");
```

**示例**:
```cpp
if (!valid) {
    return std::unexpected(McpError::invalidParams("Missing required field"));
}

if (notFound) {
    return std::unexpected(McpError::methodNotFound("unknown_tool"));
}

if (exception) {
    return std::unexpected(McpError::internalError("Database connection failed"));
}
```

## JSON 辅助类

### JsonWriter

流式 JSON 序列化器。

#### 方法

```cpp
void StartObject();
void EndObject();
void StartArray();
void EndArray();
void Key(const std::string& key);
void String(const std::string& value);
void Number(int64_t value);
void Number(double value);
void Bool(bool value);
void Null();
void Raw(const std::string& json);
std::string TakeString();
```

**示例**:
```cpp
JsonWriter writer;
writer.StartObject();
writer.Key("name");
writer.String("Alice");
writer.Key("age");
writer.Number(30);
writer.Key("active");
writer.Bool(true);
writer.Key("tags");
writer.StartArray();
writer.String("admin");
writer.String("user");
writer.EndArray();
writer.EndObject();

std::string json = writer.TakeString();
// {"name":"Alice","age":30,"active":true,"tags":["admin","user"]}
```

### JsonHelper

JSON 解析辅助函数。

#### 方法

```cpp
static bool GetObject(const JsonElement& element, JsonObject& obj);
static bool GetArray(const JsonElement& element, JsonArray& arr);
static bool GetString(const JsonElement& element, std::string& str);
static bool GetInt64(const JsonElement& element, int64_t& val);
static bool GetDouble(const JsonElement& element, double& val);
static bool GetBool(const JsonElement& element, bool& val);
static bool GetRawJson(const JsonElement& element, std::string& json);
```

**示例**:
```cpp
auto doc = JsonDocument::Parse(jsonString);
if (doc) {
    JsonElement root = doc.value().Root();
    JsonObject obj;
    if (JsonHelper::GetObject(root, obj)) {
        auto nameVal = obj["name"];
        std::string name;
        if (!nameVal.error() && JsonHelper::GetString(nameVal.value(), name)) {
            std::cout << "Name: " << name << '\n';
        }
    }
}
```

## 数据结构

### Tool

```cpp
struct Tool {
    std::string name;
    std::string description;
    JsonString inputSchema;
};
```

### Resource

```cpp
struct Resource {
    std::string uri;
    std::string name;
    std::string description;
    std::string mimeType;
};
```

### Prompt

```cpp
struct Prompt {
    std::string name;
    std::string description;
    std::vector<PromptArgument> arguments;
};
```

### PromptArgument

```cpp
struct PromptArgument {
    std::string name;
    std::string description;
    bool required;
};
```

### ServerInfo

```cpp
struct ServerInfo {
    std::string name;
    std::string version;
    JsonString capabilities;
};
```

### ServerCapabilities

```cpp
struct ServerCapabilities {
    bool tools;
    bool resources;
    bool prompts;
    bool logging;
};
```

## 常量

### MCP 版本

```cpp
constexpr const char* MCP_VERSION = "2024-11-05";
constexpr const char* JSONRPC_VERSION = "2.0";
```

### 错误码

```cpp
namespace ErrorCodes {
    constexpr int PARSE_ERROR = -32700;
    constexpr int INVALID_REQUEST = -32600;
    constexpr int METHOD_NOT_FOUND = -32601;
    constexpr int INVALID_PARAMS = -32602;
    constexpr int INTERNAL_ERROR = -32603;
    constexpr int SERVER_ERROR_START = -32099;
    constexpr int SERVER_ERROR_END = -32000;
}
```

## 下一步

- [使用指南](03-使用指南.md) - 详细的使用说明和最佳实践
- [示例代码](04-示例代码.md) - 更多实用示例
- [常见问题](05-常见问题.md) - 常见问题解答
