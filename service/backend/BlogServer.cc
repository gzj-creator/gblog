/**
 * @file BlogServer.cc
 * @brief Galay Blog 后端服务器
 * @details 使用 galay-http 框架实现的博客后端服务器，提供静态文件服务和 RESTful API
 */

#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/protoc/http/HttpRequest.h"
#include "galay-http/protoc/http/HttpResponse.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"
#include "galay-kernel/common/Log.h"
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <csignal>
#include <filesystem>
#include <optional>
#include <mutex>
#include <cctype>

using namespace galay::http;
using namespace galay::kernel;

// ============================================
// 全局变量
// ============================================

static HttpServer* g_server = nullptr;
static std::atomic<bool> g_running{true};

// ============================================
// 信号处理
// ============================================

void signalHandler(int signum) {
    LogInfo("Received signal {}, shutting down...", signum);
    g_running = false;
    if (g_server) {
        g_server->stop();
    }
}

// ============================================
// 数据结构
// ============================================

struct ProjectInfo {
    std::string m_id;
    std::string m_name;
    std::string m_description;
    std::string m_long_description;
    std::vector<std::string> m_features;
    std::string m_language;
    std::string m_license;
    std::string m_github;
};

struct BlogPost {
    std::string m_id;
    std::string m_title;
    std::string m_excerpt;
    std::string m_content;
    std::string m_date;
    std::string m_category;
    std::string m_category_name;
    std::vector<std::string> m_tags;
    std::string m_reading_time;
    bool m_featured;
};

struct DocItem {
    std::string m_id;
    std::string m_title;
    std::string m_description;
    std::string m_category;
    std::string m_content;
    int m_order;
};

struct AuthUser {
    std::string m_username = "demo";
    std::string m_display_name = "Demo User";
    std::string m_email = "demo@example.com";
    std::string m_bio;
    std::string m_website;
    std::string m_github;
    std::string m_password = "demo123456";
};

struct NotificationSettings {
    bool m_email_notifications = true;
    bool m_new_post_notifications = true;
    bool m_comment_reply_notifications = true;
    bool m_release_notifications = true;
};

// ============================================
// 数据存储
// ============================================

static std::map<std::string, ProjectInfo> g_projects = {
    {"kernel", {
        "kernel",
        "galay-kernel",
        "高性能 C++20 协程网络库，基于 kqueue/epoll/io_uring 实现异步 IO",
        "galay-kernel 是整个 Galay 框架的核心，提供了基于 C++20 协程的高性能异步 IO 运行时。",
        {"极致性能：单线程 31.3 万 QPS", "协程驱动：基于 C++20 标准协程", "跨平台：支持 macOS/Linux", "异步文件 IO"},
        "C++20",
        "MIT",
        "https://github.com/gzj-creator/galay-kernel"
    }},
    {"http", {
        "http",
        "galay-http",
        "现代化高性能异步 HTTP/WebSocket 库",
        "galay-http 是构建于 galay-kernel 之上的 HTTP/WebSocket 协议库。",
        {"高性能路由：O(1) 精确匹配", "静态文件服务：支持多种传输模式", "Range 请求：断点续传", "WebSocket：RFC 6455 标准"},
        "C++20/23",
        "MIT",
        "https://github.com/gzj-creator/galay-http"
    }},
    {"utils", {
        "utils",
        "galay-utils",
        "现代化 C++20 工具库",
        "galay-utils 是一个纯头文件的 C++20 工具库，提供了构建高性能应用所需的各种实用组件。",
        {"线程池", "一致性哈希", "熔断器", "负载均衡"},
        "C++20",
        "MIT",
        "https://github.com/gzj-creator/galay-utils"
    }},
    {"mcp", {
        "mcp",
        "galay-mcp",
        "MCP (Model Context Protocol) 协议库，支持 AI 工具调用",
        "galay-mcp 实现了 Anthropic 的 Model Context Protocol (MCP) 协议。",
        {"JSON-RPC 通信", "工具注册 API", "类型安全", "标准兼容"},
        "C++23",
        "MIT",
        "https://github.com/gzj-creator/galay-mcp"
    }}
};

static std::vector<BlogPost> g_posts = {
    {
        "galay-http-router",
        "Galay-HTTP 路由系统设计与实现",
        "深入解析 Galay-HTTP 的混合路由策略，如何实现 O(1) 精确匹配和 O(k) 模糊匹配的完美结合。",
        "",
        "2024-01-20",
        "tech",
        "技术分享",
        {"HTTP", "路由", "算法"},
        "15 分钟",
        true
    },
    {
        "cpp20-coroutine",
        "C++20 协程在网络编程中的应用",
        "探索如何使用 C++20 协程构建高性能异步网络库，从原理到实践的完整指南。",
        "",
        "2024-01-15",
        "tutorial",
        "教程",
        {"C++20", "协程", "异步"},
        "20 分钟",
        false
    },
    {
        "coroutine-io-tuning",
        "协程 IO 调优实践",
        "分享 Galay-Kernel 性能优化的经验，包括零拷贝、内存池、事件驱动等关键技术。",
        "",
        "2024-01-10",
        "performance",
        "性能优化",
        {"性能", "优化", "压测"},
        "18 分钟",
        false
    },
    {
        "static-file-transfer",
        "静态文件传输的四种模式详解",
        "详细介绍 Galay-HTTP 支持的 MEMORY、CHUNK、SENDFILE、AUTO 四种文件传输模式。",
        "",
        "2024-01-05",
        "tech",
        "技术分享",
        {"HTTP", "文件传输", "sendfile"},
        "12 分钟",
        false
    },
    {
        "galay-mcp-intro",
        "Galay-MCP：让 C++ 应用接入 AI 工具调用",
        "介绍 Galay-MCP 项目，如何使用 Model Context Protocol 让你的 C++ 应用与 AI 模型进行工具调用交互。",
        "",
        "2024-01-01",
        "tutorial",
        "教程",
        {"MCP", "AI", "JSON-RPC"},
        "10 分钟",
        false
    },
    {
        "websocket-implementation",
        "WebSocket 协议实现：从握手到心跳",
        "完整解析 WebSocket 协议的实现过程，包括 HTTP 升级握手、帧解析、掩码处理、心跳保活等核心功能。",
        "",
        "2023-12-25",
        "tech",
        "技术分享",
        {"WebSocket", "协议", "网络"},
        "16 分钟",
        false
    },
    {
        "galay-v1-release",
        "Galay Framework v1.0 正式发布",
        "经过数月的开发和测试，Galay Framework v1.0 正式发布！本文介绍新版本的主要特性、改进和升级指南。",
        "",
        "2023-12-20",
        "release",
        "版本发布",
        {"发布", "v1.0"},
        "5 分钟",
        false
    },
    {
        "consistent-hash",
        "一致性哈希算法在 Galay-Utils 中的实现",
        "深入讲解一致性哈希算法的原理和实现，以及在分布式系统中的应用场景。",
        "",
        "2023-12-15",
        "tech",
        "技术分享",
        {"算法", "分布式", "哈希"},
        "14 分钟",
        false
    }
};

static std::vector<DocItem> g_docs = {
    {"quick-start", "快速开始", "5 分钟内搭建你的第一个 Galay 应用", "getting-started", "", 1},
    {"installation", "安装指南", "详细的安装和配置说明", "getting-started", "", 2},
    {"http-server", "HTTP 服务器", "使用 HttpServer 创建 Web 服务", "guide", "", 3},
    {"http-router", "路由系统", "HttpRouter 的使用方法和路由匹配规则", "guide", "", 4},
    {"static-files", "静态文件服务", "配置静态文件服务和传输模式", "guide", "", 5},
    {"websocket", "WebSocket", "WebSocket 服务器和客户端的使用", "guide", "", 6},
    {"coroutine", "协程基础", "C++20 协程在 Galay 中的应用", "advanced", "", 7},
    {"performance", "性能优化", "性能调优和最佳实践", "advanced", "", 8},
    {"api-httpserver", "HttpServer API", "HttpServer 类的完整 API 参考", "api", "", 9},
    {"api-httprouter", "HttpRouter API", "HttpRouter 类的完整 API 参考", "api", "", 10}
};

static AuthUser g_auth_user;
static NotificationSettings g_notification_settings;
static std::string g_access_token = "galay-access-token";
static std::string g_refresh_token = "galay-refresh-token";
static std::mutex g_auth_mutex;

// ============================================
// JSON 序列化辅助函数
// ============================================

std::string escapeJson(const std::string& str) {
    std::string result;
    result.reserve(str.size() + 10);
    for (char c : str) {
        switch (c) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default: result += c; break;
        }
    }
    return result;
}

std::string vectorToJsonArray(const std::vector<std::string>& vec) {
    std::string json = "[";
    for (size_t i = 0; i < vec.size(); ++i) {
        if (i > 0) json += ",";
        json += "\"" + escapeJson(vec[i]) + "\"";
    }
    json += "]";
    return json;
}

std::string projectToJson(const ProjectInfo& project) {
    std::string json = "{";
    json += "\"id\":\"" + escapeJson(project.m_id) + "\",";
    json += "\"name\":\"" + escapeJson(project.m_name) + "\",";
    json += "\"description\":\"" + escapeJson(project.m_description) + "\",";
    json += "\"longDescription\":\"" + escapeJson(project.m_long_description) + "\",";
    json += "\"features\":" + vectorToJsonArray(project.m_features) + ",";
    json += "\"language\":\"" + escapeJson(project.m_language) + "\",";
    json += "\"license\":\"" + escapeJson(project.m_license) + "\",";
    json += "\"github\":\"" + escapeJson(project.m_github) + "\"";
    json += "}";
    return json;
}

std::string allProjectsToJson() {
    std::string json = "[";
    bool first = true;
    for (const auto& [id, project] : g_projects) {
        if (!first) json += ",";
        first = false;
        json += "{";
        json += "\"id\":\"" + escapeJson(project.m_id) + "\",";
        json += "\"name\":\"" + escapeJson(project.m_name) + "\",";
        json += "\"description\":\"" + escapeJson(project.m_description) + "\",";
        json += "\"language\":\"" + escapeJson(project.m_language) + "\",";
        json += "\"license\":\"" + escapeJson(project.m_license) + "\"";
        json += "}";
    }
    json += "]";
    return json;
}

std::string postToJson(const BlogPost& post) {
    std::string json = "{";
    json += "\"id\":\"" + escapeJson(post.m_id) + "\",";
    json += "\"title\":\"" + escapeJson(post.m_title) + "\",";
    json += "\"excerpt\":\"" + escapeJson(post.m_excerpt) + "\",";
    json += "\"date\":\"" + escapeJson(post.m_date) + "\",";
    json += "\"category\":\"" + escapeJson(post.m_category) + "\",";
    json += "\"categoryName\":\"" + escapeJson(post.m_category_name) + "\",";
    json += "\"tags\":" + vectorToJsonArray(post.m_tags) + ",";
    json += "\"readingTime\":\"" + escapeJson(post.m_reading_time) + "\",";
    json += "\"featured\":" + std::string(post.m_featured ? "true" : "false");
    json += "}";
    return json;
}

std::string allPostsToJson() {
    std::string json = "[";
    for (size_t i = 0; i < g_posts.size(); ++i) {
        if (i > 0) json += ",";
        json += postToJson(g_posts[i]);
    }
    json += "]";
    return json;
}

std::string docToJson(const DocItem& doc) {
    std::string json = "{";
    json += "\"id\":\"" + escapeJson(doc.m_id) + "\",";
    json += "\"title\":\"" + escapeJson(doc.m_title) + "\",";
    json += "\"description\":\"" + escapeJson(doc.m_description) + "\",";
    json += "\"category\":\"" + escapeJson(doc.m_category) + "\",";
    json += "\"order\":" + std::to_string(doc.m_order);
    json += "}";
    return json;
}

std::string allDocsToJson() {
    std::string json = "[";
    for (size_t i = 0; i < g_docs.size(); ++i) {
        if (i > 0) json += ",";
        json += docToJson(g_docs[i]);
    }
    json += "]";
    return json;
}

std::string makeSuccessJson(const std::string& dataJson) {
    return "{\"success\":true,\"data\":" + dataJson + "}";
}

std::string makeErrorJson(const std::string& message) {
    return "{\"success\":false,\"error\":{\"message\":\"" + escapeJson(message) + "\"}}";
}

std::string authUserToJson(const AuthUser& user) {
    std::string json = "{";
    json += "\"username\":\"" + escapeJson(user.m_username) + "\",";
    json += "\"display_name\":\"" + escapeJson(user.m_display_name) + "\",";
    json += "\"email\":\"" + escapeJson(user.m_email) + "\",";
    json += "\"bio\":\"" + escapeJson(user.m_bio) + "\",";
    json += "\"website\":\"" + escapeJson(user.m_website) + "\",";
    json += "\"github\":\"" + escapeJson(user.m_github) + "\"";
    json += "}";
    return json;
}

std::string notificationSettingsToJson(const NotificationSettings& settings) {
    std::string json = "{";
    json += "\"email_notifications\":" + std::string(settings.m_email_notifications ? "true" : "false") + ",";
    json += "\"new_post_notifications\":" + std::string(settings.m_new_post_notifications ? "true" : "false") + ",";
    json += "\"comment_reply_notifications\":" + std::string(settings.m_comment_reply_notifications ? "true" : "false") + ",";
    json += "\"release_notifications\":" + std::string(settings.m_release_notifications ? "true" : "false");
    json += "}";
    return json;
}

void skipSpaces(const std::string& source, size_t& pos) {
    while (pos < source.size() && std::isspace(static_cast<unsigned char>(source[pos]))) {
        ++pos;
    }
}

std::optional<std::string> extractJsonStringField(const std::string& body, const std::string& key) {
    const std::string pattern = "\"" + key + "\"";
    const size_t keyPos = body.find(pattern);
    if (keyPos == std::string::npos) {
        return std::nullopt;
    }

    const size_t colonPos = body.find(':', keyPos + pattern.size());
    if (colonPos == std::string::npos) {
        return std::nullopt;
    }

    size_t valuePos = colonPos + 1;
    skipSpaces(body, valuePos);
    if (valuePos >= body.size() || body[valuePos] != '"') {
        return std::nullopt;
    }
    ++valuePos;

    std::string out;
    out.reserve(64);
    while (valuePos < body.size()) {
        const char ch = body[valuePos];
        if (ch == '\\' && valuePos + 1 < body.size()) {
            out.push_back(body[valuePos + 1]);
            valuePos += 2;
            continue;
        }
        if (ch == '"') {
            return out;
        }
        out.push_back(ch);
        ++valuePos;
    }
    return std::nullopt;
}

std::optional<bool> extractJsonBoolField(const std::string& body, const std::string& key) {
    const std::string pattern = "\"" + key + "\"";
    const size_t keyPos = body.find(pattern);
    if (keyPos == std::string::npos) {
        return std::nullopt;
    }

    const size_t colonPos = body.find(':', keyPos + pattern.size());
    if (colonPos == std::string::npos) {
        return std::nullopt;
    }

    size_t valuePos = colonPos + 1;
    skipSpaces(body, valuePos);
    if (valuePos >= body.size()) {
        return std::nullopt;
    }

    if (body.compare(valuePos, 4, "true") == 0) {
        return true;
    }
    if (body.compare(valuePos, 5, "false") == 0) {
        return false;
    }
    return std::nullopt;
}

bool hasValidBearerToken(HttpRequest& req) {
    const std::string auth = req.header().headerPairs().getValue("Authorization");
    constexpr std::string_view kPrefix = "Bearer ";
    if (auth.rfind(kPrefix.data(), 0) != 0) {
        return false;
    }

    const std::string token = auth.substr(kPrefix.size());
    std::lock_guard<std::mutex> lock(g_auth_mutex);
    return !g_access_token.empty() && token == g_access_token;
}

// ============================================
// API 处理器
// ============================================

/**
 * @brief 健康检查接口
 */
Coroutine healthHandler(HttpConn& conn, HttpRequest req) {
    std::string body = R"({"status":"ok","server":"Galay-Blog","version":"1.0.0"})";

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取所有项目列表
 */
Coroutine getProjectsHandler(HttpConn& conn, HttpRequest req) {
    std::string body = allProjectsToJson();

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取单个项目详情
 */
Coroutine getProjectByIdHandler(HttpConn& conn, HttpRequest req) {
    std::string uri = req.header().uri();
    size_t lastSlash = uri.rfind('/');
    std::string projectId = uri.substr(lastSlash + 1);

    size_t queryPos = projectId.find('?');
    if (queryPos != std::string::npos) {
        projectId = projectId.substr(0, queryPos);
    }

    auto writer = conn.getWriter();

    auto it = g_projects.find(projectId);
    if (it == g_projects.end()) {
        auto response = Http1_1ResponseBuilder::notFound()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(R"({"error":"Project not found"})")
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    std::string body = projectToJson(it->second);

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取所有博客文章列表
 */
Coroutine getPostsHandler(HttpConn& conn, HttpRequest req) {
    std::string body = allPostsToJson();

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取单篇博客文章
 */
Coroutine getPostByIdHandler(HttpConn& conn, HttpRequest req) {
    std::string uri = req.header().uri();
    size_t lastSlash = uri.rfind('/');
    std::string postId = uri.substr(lastSlash + 1);

    size_t queryPos = postId.find('?');
    if (queryPos != std::string::npos) {
        postId = postId.substr(0, queryPos);
    }

    auto writer = conn.getWriter();

    // 查找文章
    const BlogPost* foundPost = nullptr;
    for (const auto& post : g_posts) {
        if (post.m_id == postId) {
            foundPost = &post;
            break;
        }
    }

    if (!foundPost) {
        auto response = Http1_1ResponseBuilder::notFound()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(R"({"error":"Post not found"})")
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    std::string body = postToJson(*foundPost);

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取所有文档列表
 */
Coroutine getDocsHandler(HttpConn& conn, HttpRequest req) {
    std::string body = allDocsToJson();

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取单个文档
 */
Coroutine getDocByIdHandler(HttpConn& conn, HttpRequest req) {
    std::string uri = req.header().uri();
    size_t lastSlash = uri.rfind('/');
    std::string docId = uri.substr(lastSlash + 1);

    size_t queryPos = docId.find('?');
    if (queryPos != std::string::npos) {
        docId = docId.substr(0, queryPos);
    }

    auto writer = conn.getWriter();

    // 查找文档
    const DocItem* foundDoc = nullptr;
    for (const auto& doc : g_docs) {
        if (doc.m_id == docId) {
            foundDoc = &doc;
            break;
        }
    }

    if (!foundDoc) {
        auto response = Http1_1ResponseBuilder::notFound()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(R"({"error":"Document not found"})")
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    std::string body = docToJson(*foundDoc);

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 用户登录
 */
Coroutine authLoginHandler(HttpConn& conn, HttpRequest req) {
    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("demo");
    const std::string password = extractJsonStringField(body, "password").value_or("");

    AuthUser userSnapshot;
    std::string accessToken;
    std::string refreshToken;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        if (!username.empty()) {
            g_auth_user.m_username = username;
            if (g_auth_user.m_display_name.empty()) {
                g_auth_user.m_display_name = username;
            }
        }
        if (!password.empty()) {
            g_auth_user.m_password = password;
        }
        accessToken = g_access_token;
        refreshToken = g_refresh_token;
        userSnapshot = g_auth_user;
    }

    const std::string dataJson =
        "{\"access_token\":\"" + escapeJson(accessToken) + "\","
        "\"refresh_token\":\"" + escapeJson(refreshToken) + "\","
        "\"user\":" + authUserToJson(userSnapshot) + "}";

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(dataJson))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 用户注册
 */
Coroutine authRegisterHandler(HttpConn& conn, HttpRequest req) {
    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("demo");
    const std::string email = extractJsonStringField(body, "email").value_or("demo@example.com");
    const std::string password = extractJsonStringField(body, "password").value_or("demo123456");

    AuthUser userSnapshot;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        g_auth_user.m_username = username;
        g_auth_user.m_display_name = username;
        g_auth_user.m_email = email;
        g_auth_user.m_password = password;
        userSnapshot = g_auth_user;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(authUserToJson(userSnapshot)))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 刷新 access token
 */
Coroutine authRefreshHandler(HttpConn& conn, HttpRequest req) {
    const std::string body = req.bodyStr();
    const std::string refreshToken = extractJsonStringField(body, "refresh_token").value_or("");

    std::string currentAccessToken;
    bool tokenMatched = false;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        tokenMatched = (!refreshToken.empty() && refreshToken == g_refresh_token);
        currentAccessToken = g_access_token;
    }

    auto writer = conn.getWriter();
    if (!tokenMatched) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("refresh token invalid"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    const std::string dataJson = "{\"access_token\":\"" + escapeJson(currentAccessToken) + "\"}";
    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(dataJson))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 登出
 */
Coroutine authLogoutHandler(HttpConn& conn, HttpRequest req) {
    (void)req;
    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson("{}"))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 获取当前用户信息
 */
Coroutine authMeHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    if (!hasValidBearerToken(req)) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    AuthUser userSnapshot;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        userSnapshot = g_auth_user;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(authUserToJson(userSnapshot)))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 更新个人资料
 */
Coroutine authUpdateProfileHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    if (!hasValidBearerToken(req)) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    const std::string body = req.bodyStr();
    AuthUser userSnapshot;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        if (const auto v = extractJsonStringField(body, "display_name"); v.has_value()) g_auth_user.m_display_name = *v;
        if (const auto v = extractJsonStringField(body, "email"); v.has_value()) g_auth_user.m_email = *v;
        if (const auto v = extractJsonStringField(body, "bio"); v.has_value()) g_auth_user.m_bio = *v;
        if (const auto v = extractJsonStringField(body, "website"); v.has_value()) g_auth_user.m_website = *v;
        if (const auto v = extractJsonStringField(body, "github"); v.has_value()) g_auth_user.m_github = *v;
        userSnapshot = g_auth_user;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(authUserToJson(userSnapshot)))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 修改密码
 */
Coroutine authUpdatePasswordHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    if (!hasValidBearerToken(req)) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    const std::string body = req.bodyStr();
    const std::string oldPassword = extractJsonStringField(body, "old_password").value_or("");
    const std::string newPassword = extractJsonStringField(body, "new_password").value_or("");

    bool oldPasswordValid = true;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        oldPasswordValid = (oldPassword.empty() || oldPassword == g_auth_user.m_password);
        if (oldPasswordValid && !newPassword.empty()) {
            g_auth_user.m_password = newPassword;
        }
    }

    if (!oldPasswordValid) {
        auto response = Http1_1ResponseBuilder::badRequest()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("old password incorrect"))
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
        .json(makeSuccessJson("{}"))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 更新通知设置
 */
Coroutine authUpdateNotificationsHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    if (!hasValidBearerToken(req)) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    const std::string body = req.bodyStr();
    NotificationSettings settingsSnapshot;
    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        if (const auto v = extractJsonBoolField(body, "email_notifications"); v.has_value()) g_notification_settings.m_email_notifications = *v;
        if (const auto v = extractJsonBoolField(body, "new_post_notifications"); v.has_value()) g_notification_settings.m_new_post_notifications = *v;
        if (const auto v = extractJsonBoolField(body, "comment_reply_notifications"); v.has_value()) g_notification_settings.m_comment_reply_notifications = *v;
        if (const auto v = extractJsonBoolField(body, "release_notifications"); v.has_value()) g_notification_settings.m_release_notifications = *v;
        settingsSnapshot = g_notification_settings;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(notificationSettingsToJson(settingsSnapshot)))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

/**
 * @brief 删除账号
 */
Coroutine authDeleteAccountHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    if (!hasValidBearerToken(req)) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto result = co_await writer.sendResponse(response);
            if (!result || result.value()) break;
        }
        co_return;
    }

    {
        std::lock_guard<std::mutex> lock(g_auth_mutex);
        g_access_token.clear();
        g_refresh_token.clear();
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson("{}"))
        .build();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

// ============================================
// 主函数
// ============================================

int main(int argc, char* argv[]) {
    // 解析命令行参数
    std::string host = "0.0.0.0";
    uint16_t port = 8080;
    std::string staticDir;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if ((arg == "-h" || arg == "--host") && i + 1 < argc) {
            host = argv[++i];
        } else if ((arg == "-p" || arg == "--port") && i + 1 < argc) {
            port = static_cast<uint16_t>(std::stoi(argv[++i]));
        } else if ((arg == "-s" || arg == "--static") && i + 1 < argc) {
            staticDir = argv[++i];
        } else if (arg == "--help") {
            std::cout << "Galay Blog Server\n"
                      << "Usage: " << argv[0] << " [options]\n"
                      << "Options:\n"
                      << "  -h, --host <host>    Server host (default: 0.0.0.0)\n"
                      << "  -p, --port <port>    Server port (default: 8080)\n"
                      << "  -s, --static <dir>   Static files directory (default: disabled)\n"
                      << "  --help               Show this help message\n";
            return 0;
        }
    }

    // 设置信号处理
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    LogInfo("============================================");
    LogInfo("       Galay Blog Server v1.0.0");
    LogInfo("============================================");

    // 创建路由器
    HttpRouter router;

    const auto joinRoute = [](const std::string& prefix, const std::string& path) {
        return prefix.empty() ? path : prefix + path;
    };

    // 博客 API：兼容直连 (/api/...) 与 static 去前缀转发 (/...)
    for (const std::string& prefix : {std::string("/api"), std::string("")}) {
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/health"), healthHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/projects"), getProjectsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/projects/:id"), getProjectByIdHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/posts"), getPostsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/posts/:id"), getPostByIdHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/docs"), getDocsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/docs/:id"), getDocByIdHandler);
    }

    // 认证接口：
    // 1) /api/auth/... 直连
    // 2) /auth/...     经过 static 的 /api 前缀转发后
    // 3) /...          经过 static 的 /auth 前缀转发后
    for (const std::string& authPrefix : {std::string("/api/auth"), std::string("/auth"), std::string("")}) {
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/login"), authLoginHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/register"), authRegisterHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/refresh"), authRefreshHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/logout"), authLogoutHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(authPrefix, "/me"), authMeHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/profile"), authUpdateProfileHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/password"), authUpdatePasswordHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/notifications"), authUpdateNotificationsHandler);
        router.addHandler<HttpMethod::DELETE>(joinRoute(authPrefix, "/account"), authDeleteAccountHandler);
    }

    // 静态文件服务配置
    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setSmallFileThreshold(64 * 1024);    // 64KB
    staticConfig.setLargeFileThreshold(1024 * 1024);  // 1MB

    // 可选：仅当指定目录时挂载静态文件
    if (!staticDir.empty()) {
        if (!std::filesystem::exists(staticDir) || !std::filesystem::is_directory(staticDir)) {
            LogWarn("Static directory not found, static mount skipped: {}", staticDir);
        } else {
            router.mount("/", staticDir, staticConfig);
            LogInfo("Static files: {}", staticDir);
        }
    } else {
        LogInfo("Static files: disabled");
    }
    LogInfo("API endpoints:");
    LogInfo("  GET /health, /projects, /projects/:id, /posts, /posts/:id, /docs, /docs/:id");
    LogInfo("  POST /auth/login, /auth/register, /auth/refresh, /auth/logout");
    LogInfo("  GET /auth/me");
    LogInfo("  PUT /auth/profile, /auth/password, /auth/notifications");
    LogInfo("  DELETE /auth/account");
    LogInfo("Starting server on {}:{}", host, port);
    LogInfo("============================================");

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

        LogInfo("Server started successfully!");
        LogInfo("Open http://localhost:{} in your browser", port);
        LogInfo("Press Ctrl+C to stop");

        // 保持运行
        while (g_running && server.isRunning()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        LogError("Server error: {}", e.what());
        return 1;
    }

    LogInfo("Server stopped.");
    return 0;
}
