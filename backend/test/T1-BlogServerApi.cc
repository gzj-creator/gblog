/**
 * @file T1-BlogServerApi.cc
 * @brief 博客服务器 API 测试
 * @details 测试 API 接口的正确性
 */

#include "galay-http/kernel/http/HttpClient.h"
#include "galay-http/protoc/http/HttpRequest.h"
#include "galay-http/protoc/http/HttpResponse.h"
#include "galay-http/utils/Http1_1RequestBuilder.h"
#include "galay-kernel/kernel/Runtime.h"
#include "galay-kernel/common/Log.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>

using namespace galay::http;
using namespace galay::kernel;

// 测试结果写入
void writeTestResult(const std::string& testName, bool passed, const std::string& message) {
    std::ofstream file("test_results.txt", std::ios::app);
    file << "[" << (passed ? "PASS" : "FAIL") << "] " << testName << ": " << message << "\n";
    file.close();

    if (passed) {
        LogInfo("[PASS] {}: {}", testName, message);
    } else {
        LogError("[FAIL] {}: {}", testName, message);
    }
}

// 测试健康检查接口
Coroutine testHealthApi(Runtime& runtime) {
    LogInfo("Testing /api/health endpoint...");

    HttpClient client;
    auto connectResult = co_await client.connect("http://127.0.0.1:8080");

    if (!connectResult) {
        writeTestResult("Health API", false, "Failed to connect to server");
        co_return;
    }

    // 发送 GET 请求
    bool complete = false;
    while (!complete) {
        auto result = co_await client.get("/api/health");

        if (!result) {
            writeTestResult("Health API", false, "Request failed");
            co_await client.close();
            co_return;
        }

        if (!result.value()) {
            continue;  // 继续等待
        }

        auto response = result.value().value();
        auto statusCode = response.header().code();

        if (statusCode == HttpStatusCode::OK_200) {
            std::string body = response.getBodyStr();
            if (body.find("\"status\":\"ok\"") != std::string::npos) {
                writeTestResult("Health API", true, "Status OK, response valid");
            } else {
                writeTestResult("Health API", false, "Invalid response body: " + body);
            }
        } else {
            writeTestResult("Health API", false, "Unexpected status code");
        }

        complete = true;
    }

    co_await client.close();
    co_return;
}

// 测试项目列表接口
Coroutine testProjectsApi(Runtime& runtime) {
    LogInfo("Testing /api/projects endpoint...");

    HttpClient client;
    auto connectResult = co_await client.connect("http://127.0.0.1:8080");

    if (!connectResult) {
        writeTestResult("Projects API", false, "Failed to connect to server");
        co_return;
    }

    bool complete = false;
    while (!complete) {
        auto result = co_await client.get("/api/projects");

        if (!result) {
            writeTestResult("Projects API", false, "Request failed");
            co_await client.close();
            co_return;
        }

        if (!result.value()) {
            continue;
        }

        auto response = result.value().value();
        auto statusCode = response.header().code();

        if (statusCode == HttpStatusCode::OK_200) {
            std::string body = response.getBodyStr();
            // 检查是否包含预期的项目
            bool hasKernel = body.find("\"id\":\"kernel\"") != std::string::npos;
            bool hasHttp = body.find("\"id\":\"http\"") != std::string::npos;
            bool hasUtils = body.find("\"id\":\"utils\"") != std::string::npos;
            bool hasMcp = body.find("\"id\":\"mcp\"") != std::string::npos;

            if (hasKernel && hasHttp && hasUtils && hasMcp) {
                writeTestResult("Projects API", true, "All 4 projects found in response");
            } else {
                writeTestResult("Projects API", false, "Missing projects in response");
            }
        } else {
            writeTestResult("Projects API", false, "Unexpected status code");
        }

        complete = true;
    }

    co_await client.close();
    co_return;
}

// 测试单个项目详情接口
Coroutine testProjectDetailApi(Runtime& runtime) {
    LogInfo("Testing /api/projects/:id endpoint...");

    HttpClient client;
    auto connectResult = co_await client.connect("http://127.0.0.1:8080");

    if (!connectResult) {
        writeTestResult("Project Detail API", false, "Failed to connect to server");
        co_return;
    }

    bool complete = false;
    while (!complete) {
        auto result = co_await client.get("/api/projects/kernel");

        if (!result) {
            writeTestResult("Project Detail API", false, "Request failed");
            co_await client.close();
            co_return;
        }

        if (!result.value()) {
            continue;
        }

        auto response = result.value().value();
        auto statusCode = response.header().code();

        if (statusCode == HttpStatusCode::OK_200) {
            std::string body = response.getBodyStr();
            bool hasId = body.find("\"id\":\"kernel\"") != std::string::npos;
            bool hasName = body.find("\"name\":\"galay-kernel\"") != std::string::npos;
            bool hasFeatures = body.find("\"features\"") != std::string::npos;

            if (hasId && hasName && hasFeatures) {
                writeTestResult("Project Detail API", true, "Project detail response valid");
            } else {
                writeTestResult("Project Detail API", false, "Invalid project detail response");
            }
        } else {
            writeTestResult("Project Detail API", false, "Unexpected status code");
        }

        complete = true;
    }

    co_await client.close();
    co_return;
}

// 测试 404 响应
Coroutine testNotFoundApi(Runtime& runtime) {
    LogInfo("Testing 404 response...");

    HttpClient client;
    auto connectResult = co_await client.connect("http://127.0.0.1:8080");

    if (!connectResult) {
        writeTestResult("404 Response", false, "Failed to connect to server");
        co_return;
    }

    bool complete = false;
    while (!complete) {
        auto result = co_await client.get("/api/projects/nonexistent");

        if (!result) {
            writeTestResult("404 Response", false, "Request failed");
            co_await client.close();
            co_return;
        }

        if (!result.value()) {
            continue;
        }

        auto response = result.value().value();
        auto statusCode = response.header().code();

        if (statusCode == HttpStatusCode::NotFound_404) {
            writeTestResult("404 Response", true, "Correctly returned 404 for nonexistent project");
        } else {
            writeTestResult("404 Response", false, "Expected 404, got different status");
        }

        complete = true;
    }

    co_await client.close();
    co_return;
}

// 运行所有测试
Coroutine runAllTests(Runtime& runtime) {
    LogInfo("============================================");
    LogInfo("Starting Blog Server API Tests");
    LogInfo("============================================");

    // 清空测试结果文件
    std::ofstream file("test_results.txt", std::ios::trunc);
    file << "Blog Server API Test Results\n";
    file << "============================================\n";
    file.close();

    // 等待服务器启动
    std::this_thread::sleep_for(std::chrono::seconds(1));

    co_await testHealthApi(runtime);
    co_await testProjectsApi(runtime);
    co_await testProjectDetailApi(runtime);
    co_await testNotFoundApi(runtime);

    LogInfo("============================================");
    LogInfo("All tests completed. See test_results.txt");
    LogInfo("============================================");

    co_return;
}

int main() {
    LogInfo("Blog Server API Test Client");
    LogInfo("Make sure the server is running on port 8080");

    Runtime runtime(LoadBalanceStrategy::ROUND_ROBIN, 1, 1);
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(runAllTests(runtime));

    // 等待测试完成
    std::this_thread::sleep_for(std::chrono::seconds(10));

    runtime.stop();
    return 0;
}
