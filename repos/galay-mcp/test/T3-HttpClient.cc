/**
 * @file T3-HttpClient.cc
 * @brief HTTP MCP Client 测试示例
 * @details 演示如何使用 McpHttpClient 连接到HTTP MCP服务器并调用功能
 */

#include "galay-mcp/client/McpHttpClient.h"
#include "galay-kernel/kernel/Runtime.h"
#include <iostream>
#include <string>

using namespace galay::mcp;
using namespace galay::kernel;

void printSeparator() {
    std::cout << "========================================\n";
}

void printError(const McpError& error) {
    std::cerr << "Error: " << error.message() << "\n";
    if (!error.details().empty()) {
        std::cerr << "Details: " << error.details() << "\n";
    }
}

// 测试协程
Coroutine runTest(McpHttpClient& client, const std::string& url, int& exitCode) {
    // 连接到服务器
    std::cout << "Connecting to server...\n";
    auto connectResult = co_await client.connect(url);
    if (!connectResult) {
        std::cerr << "Connect error: " << connectResult.error().message() << "\n";
        exitCode = 1;
        co_return;
    }
    std::cout << "Connected successfully\n\n";

    // 初始化
    std::cout << "Initializing...\n";
    std::expected<void, McpError> initResult;
    co_await client.initialize("test-http-client", "1.0.0", initResult).wait();
    if (!initResult) {
        printError(initResult.error());
        exitCode = 1;
        co_return;
    }
    std::cout << "Initialized successfully\n";

    auto serverInfo = client.getServerInfo();
    std::cout << "Server: " << serverInfo.name << " v" << serverInfo.version << "\n\n";

    // 测试ping
    printSeparator();
    std::cout << "Testing ping...\n";
    std::expected<void, McpError> pingResult;
    co_await client.ping(pingResult).wait();
    if (pingResult) {
        std::cout << "Ping successful\n";
    } else {
        printError(pingResult.error());
    }
    std::cout << "\n";

    // 列出工具
    printSeparator();
    std::cout << "Listing tools...\n";
    std::expected<std::vector<Tool>, McpError> toolsResult;
    co_await client.listTools(toolsResult).wait();
    if (toolsResult) {
        std::cout << "Available tools:\n";
        for (const auto& tool : toolsResult.value()) {
            std::cout << "  - " << tool.name << ": " << tool.description << "\n";
        }
    } else {
        printError(toolsResult.error());
    }
    std::cout << "\n";

    // 调用echo工具
    printSeparator();
    std::cout << "Calling echo tool...\n";
    JsonWriter echoArgsWriter;
    echoArgsWriter.StartObject();
    echoArgsWriter.Key("message");
    echoArgsWriter.String("Hello from HTTP client!");
    echoArgsWriter.EndObject();
    std::expected<JsonString, McpError> echoResult;
    co_await client.callTool("echo", echoArgsWriter.TakeString(), echoResult).wait();
    if (echoResult) {
        std::cout << "Echo result: " << echoResult.value() << "\n";
    } else {
        printError(echoResult.error());
    }
    std::cout << "\n";

    // 调用add工具
    printSeparator();
    std::cout << "Calling add tool...\n";
    JsonWriter addArgsWriter;
    addArgsWriter.StartObject();
    addArgsWriter.Key("a");
    addArgsWriter.Number(static_cast<int64_t>(42));
    addArgsWriter.Key("b");
    addArgsWriter.Number(static_cast<int64_t>(58));
    addArgsWriter.EndObject();
    std::expected<JsonString, McpError> addResult;
    co_await client.callTool("add", addArgsWriter.TakeString(), addResult).wait();
    if (addResult) {
        std::cout << "Add result: " << addResult.value() << "\n";
    } else {
        printError(addResult.error());
    }
    std::cout << "\n";

    // 列出资源
    printSeparator();
    std::cout << "Listing resources...\n";
    std::expected<std::vector<Resource>, McpError> resourcesResult;
    co_await client.listResources(resourcesResult).wait();
    if (resourcesResult) {
        std::cout << "Available resources:\n";
        for (const auto& resource : resourcesResult.value()) {
            std::cout << "  - " << resource.uri << ": " << resource.name << "\n";
        }
    } else {
        printError(resourcesResult.error());
    }
    std::cout << "\n";

    // 读取资源
    printSeparator();
    std::cout << "Reading resource...\n";
    std::expected<std::string, McpError> readResult;
    co_await client.readResource("example://hello", readResult).wait();
    if (readResult) {
        std::cout << "Resource content: " << readResult.value() << "\n";
    } else {
        printError(readResult.error());
    }
    std::cout << "\n";

    // 列出提示
    printSeparator();
    std::cout << "Listing prompts...\n";
    std::expected<std::vector<Prompt>, McpError> promptsResult;
    co_await client.listPrompts(promptsResult).wait();
    if (promptsResult) {
        std::cout << "Available prompts:\n";
        for (const auto& prompt : promptsResult.value()) {
            std::cout << "  - " << prompt.name << ": " << prompt.description << "\n";
        }
    } else {
        printError(promptsResult.error());
    }
    std::cout << "\n";

    // 获取提示
    printSeparator();
    std::cout << "Getting prompt...\n";
    JsonWriter promptArgsWriter;
    promptArgsWriter.StartObject();
    promptArgsWriter.Key("name");
    promptArgsWriter.String("Alice");
    promptArgsWriter.EndObject();
    std::expected<JsonString, McpError> promptResult;
    co_await client.getPrompt("greeting", promptArgsWriter.TakeString(), promptResult).wait();
    if (promptResult) {
        std::cout << "Prompt result: " << promptResult.value() << "\n";
    } else {
        printError(promptResult.error());
    }
    std::cout << "\n";

    // 断开连接
    printSeparator();
    std::cout << "Disconnecting...\n";
    co_await client.disconnect();
    std::cout << "Disconnected\n\n";

    exitCode = 0;
    co_return;
}

int main(int argc, char* argv[]) {
    // 解析命令行参数
    std::string url = "http://127.0.0.1:8080/mcp";

    if (argc > 1) {
        url = argv[1];
    }

    printSeparator();
    std::cout << "HTTP MCP Client Test\n";
    printSeparator();
    std::cout << "Server URL: " << url << "\n";
    printSeparator();
    std::cout << "\n";

    int exitCode = 0;

    try {
        // 创建Runtime
        Runtime runtime(1, 1);
        runtime.start();
        std::cout << "Runtime started\n\n";

        // 创建客户端
        McpHttpClient client(runtime);

        // 在IO调度器上运行测试协程
        auto* scheduler = runtime.getNextIOScheduler();
        scheduler->spawn(runTest(client, url, exitCode));

        // 等待测试完成
        std::this_thread::sleep_for(std::chrono::seconds(5));

        // 停止Runtime
        runtime.stop();
        std::cout << "Runtime stopped\n";

        printSeparator();
        if (exitCode == 0) {
            std::cout << "All tests completed successfully!\n";
        } else {
            std::cout << "Tests failed!\n";
        }
        printSeparator();

    } catch (const std::exception& e) {
        std::cerr << "Client error: " << e.what() << "\n";
        return 1;
    }

    return exitCode;
}
