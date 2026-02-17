/**
 * Galay Blog Backend Server
 *
 * 使用 galay-http 框架实现的博客后端服务器
 * - 静态文件服务（前端页面）
 * - RESTful API（项目信息）
 */

#include <galay-http/kernel/http/HttpServer.h>
#include <galay-http/kernel/http/HttpRouter.h>
#include <galay-http/utils/Http1_1ResponseBuilder.h>
#include <nlohmann/json.hpp>
#include <iostream>
#include <csignal>

using namespace galay::http;
using namespace galay::kernel;
using json = nlohmann::json;

// 全局服务器指针，用于信号处理
HttpServer* g_server = nullptr;

// 信号处理函数
void signalHandler(int signum) {
    std::cout << "\n[INFO] Received signal " << signum << ", shutting down..." << std::endl;
    if (g_server) {
        g_server->stop();
    }
}

// ============================================
// API Handlers
// ============================================

// 获取所有项目信息
Coroutine getProjectsHandler(HttpConn& conn, HttpRequest req) {
    json projects = json::array({
        {
            {"id", "kernel"},
            {"name", "galay-kernel"},
            {"description", "高性能 C++20 协程网络库，基于 kqueue/epoll/io_uring 实现异步 IO"},
            {"features", json::array({"313K QPS", "153 MB/s", "跨平台", "零拷贝"})},
            {"language", "C++20"},
            {"license", "MIT"}
        },
        {
            {"id", "http"},
            {"name", "galay-http"},
            {"description", "现代化高性能异步 HTTP/WebSocket 库"},
            {"features", json::array({"O(1) 路由", "静态文件服务", "Range 请求", "WebSocket"})},
            {"language", "C++20/23"},
            {"license", "MIT"}
        },
        {
            {"id", "utils"},
            {"name", "galay-utils"},
            {"description", "现代化 C++20 工具库"},
            {"features", json::array({"线程池", "一致性哈希", "熔断器", "负载均衡"})},
            {"language", "C++20"},
            {"license", "MIT"}
        },
        {
            {"id", "mcp"},
            {"name", "galay-mcp"},
            {"description", "MCP (Model Context Protocol) 协议库，支持 AI 工具调用"},
            {"features", json::array({"JSON-RPC", "工具注册", "类型安全", "标准兼容"})},
            {"language", "C++23"},
            {"license", "MIT"}
        }
    });

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(projects.dump())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

// 获取单个项目信息
Coroutine getProjectHandler(HttpConn& conn, HttpRequest req, const std::string& projectId) {
    // 项目数据
    std::map<std::string, json> projectsMap = {
        {"kernel", {
            {"id", "kernel"},
            {"name", "galay-kernel"},
            {"description", "高性能 C++20 协程网络库，基于 kqueue/epoll/io_uring 实现异步 IO"},
            {"longDescription", "galay-kernel 是整个 Galay 框架的核心，提供了基于 C++20 协程的高性能异步 IO 运行时。它在 macOS 上使用 kqueue，在 Linux 上支持 epoll 和 io_uring，实现了真正的跨平台异步编程。"},
            {"features", json::array({"极致性能：单线程 31.3 万 QPS", "协程驱动：基于 C++20 标准协程", "跨平台：支持 macOS/Linux", "异步文件 IO"})},
            {"benchmarks", {
                {"qps_100", 279569},
                {"qps_500", 275722},
                {"qps_1000", 263878},
                {"throughput", "130+ MB/s"}
            }},
            {"language", "C++20"},
            {"license", "MIT"},
            {"github", "https://github.com/gzj-creator/galay-kernel"}
        }},
        {"http", {
            {"id", "http"},
            {"name", "galay-http"},
            {"description", "现代化高性能异步 HTTP/WebSocket 库"},
            {"longDescription", "galay-http 是构建于 galay-kernel 之上的 HTTP/WebSocket 协议库。它提供了完整的 HTTP/1.1 支持，包括路由系统、静态文件服务、Range 请求、ETag 缓存验证等功能。"},
            {"features", json::array({"高性能路由：O(1) 精确匹配", "静态文件服务：支持多种传输模式", "Range 请求：断点续传", "WebSocket：RFC 6455 标准"})},
            {"transferModes", json::array({"MEMORY", "CHUNK", "SENDFILE", "AUTO"})},
            {"language", "C++20/23"},
            {"license", "MIT"},
            {"github", "https://github.com/gzj-creator/galay-http"}
        }},
        {"utils", {
            {"id", "utils"},
            {"name", "galay-utils"},
            {"description", "现代化 C++20 工具库"},
            {"longDescription", "galay-utils 是一个纯头文件的 C++20 工具库，提供了构建高性能应用所需的各种实用组件。"},
            {"modules", {
                {"core", json::array({"String", "Random", "System"})},
                {"dataStructures", json::array({"TrieTree", "ConsistentHash", "Mvcc"})},
                {"concurrency", json::array({"Thread", "Pool"})},
                {"distributed", json::array({"RateLimiter", "CircuitBreaker", "Balancer"})}
            }},
            {"language", "C++20"},
            {"license", "MIT"},
            {"github", "https://github.com/gzj-creator/galay-utils"}
        }},
        {"mcp", {
            {"id", "mcp"},
            {"name", "galay-mcp"},
            {"description", "MCP (Model Context Protocol) 协议库"},
            {"longDescription", "galay-mcp 实现了 Anthropic 的 Model Context Protocol (MCP) 协议，让你的 C++ 应用能够与 AI 模型进行工具调用交互。"},
            {"features", json::array({"标准输入输出通信", "简洁的工具注册 API", "C++23 std::expected 错误处理", "MCP 2024-11-05 规范兼容"})},
            {"language", "C++23"},
            {"license", "MIT"},
            {"github", "https://github.com/gzj-creator/galay-mcp"}
        }}
    };

    auto writer = conn.getWriter();

    auto it = projectsMap.find(projectId);
    if (it == projectsMap.end()) {
        auto response = Http1_1ResponseBuilder::notFound()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(R"({"error": "Project not found"})")
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(it->second.dump())
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

// 健康检查
Coroutine healthHandler(HttpConn& conn, HttpRequest req) {
    json health = {
        {"status", "ok"},
        {"server", "Galay-Blog"},
        {"version", "1.0.0"}
    };

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .json(health.dump())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

// ============================================
// Main
// ============================================

int main(int argc, char* argv[]) {
    // 解析命令行参数
    std::string host = "0.0.0.0";
    uint16_t port = 8080;
    std::string staticDir = "../frontend";

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--host") {
            if (i + 1 < argc) host = argv[++i];
        } else if (arg == "-p" || arg == "--port") {
            if (i + 1 < argc) port = static_cast<uint16_t>(std::stoi(argv[++i]));
        } else if (arg == "-s" || arg == "--static") {
            if (i + 1 < argc) staticDir = argv[++i];
        } else if (arg == "--help") {
            std::cout << "Galay Blog Server\n"
                      << "Usage: " << argv[0] << " [options]\n"
                      << "Options:\n"
                      << "  -h, --host <host>    Server host (default: 0.0.0.0)\n"
                      << "  -p, --port <port>    Server port (default: 8080)\n"
                      << "  -s, --static <dir>   Static files directory (default: ../frontend)\n"
                      << "  --help               Show this help message\n";
            return 0;
        }
    }

    // 设置信号处理
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    std::cout << "============================================\n";
    std::cout << "       Galay Blog Server v1.0.0\n";
    std::cout << "============================================\n";

    // 创建路由器
    HttpRouter router;

    // API 路由
    router.addHandler<HttpMethod::GET>("/api/health", healthHandler);
    router.addHandler<HttpMethod::GET>("/api/projects", getProjectsHandler);

    // 项目详情路由（使用路径参数）
    router.addHandler<HttpMethod::GET>("/api/projects/:id",
        [](HttpConn& conn, HttpRequest req) -> Coroutine {
            // 从 URL 中提取项目 ID
            std::string uri = req.header().uri();
            size_t lastSlash = uri.rfind('/');
            std::string projectId = uri.substr(lastSlash + 1);

            // 移除查询参数
            size_t queryPos = projectId.find('?');
            if (queryPos != std::string::npos) {
                projectId = projectId.substr(0, queryPos);
            }

            co_await getProjectHandler(conn, std::move(req), projectId);
            co_return;
        }
    );

    // 静态文件服务配置
    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setSmallFileThreshold(64 * 1024);    // 64KB
    staticConfig.setLargeFileThreshold(1024 * 1024);  // 1MB

    // 挂载静态文件目录
    if (!router.mount("/", staticDir, staticConfig)) {
        std::cerr << "[ERROR] Failed to mount static directory: " << staticDir << std::endl;
        std::cerr << "[INFO] Make sure the frontend directory exists.\n";
        return 1;
    }

    std::cout << "[INFO] Static files: " << staticDir << "\n";
    std::cout << "[INFO] API endpoints:\n";
    std::cout << "       GET /api/health\n";
    std::cout << "       GET /api/projects\n";
    std::cout << "       GET /api/projects/:id\n";
    std::cout << "[INFO] Starting server on " << host << ":" << port << "\n";
    std::cout << "============================================\n";

    // 配置服务器
    HttpServerConfig config;
    config.host = host;
    config.port = port;
    config.backlog = 128;
    config.io_scheduler_count = 0;      // 自动
    config.compute_scheduler_count = 0; // 自动

    // 创建并启动服务器
    HttpServer server(config);
    g_server = &server;

    try {
        server.start(std::move(router));

        std::cout << "[INFO] Server started successfully!\n";
        std::cout << "[INFO] Open http://localhost:" << port << " in your browser\n";
        std::cout << "[INFO] Press Ctrl+C to stop\n";

        // 保持运行
        while (server.isRunning()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Server error: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "[INFO] Server stopped.\n";
    return 0;
}
