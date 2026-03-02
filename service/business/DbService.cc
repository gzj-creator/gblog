#include "DbService.h"

DbService::DbService()
{
    m_projects = {
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

    m_posts = {
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

    m_docs = {
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
}

std::string DbService::escapeJson(const std::string& str)
{
    std::string result;
    result.reserve(str.size() + 10);
    for (const char c : str) {
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

std::string DbService::vectorToJsonArray(const std::vector<std::string>& vec)
{
    std::string json = "[";
    for (size_t i = 0; i < vec.size(); ++i) {
        if (i > 0) json += ",";
        json += "\"" + escapeJson(vec[i]) + "\"";
    }
    json += "]";
    return json;
}

std::string DbService::projectToJson(const ProjectInfo& project) const
{
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

std::string DbService::allProjectsToJson() const
{
    std::string json = "[";
    bool first = true;
    for (const auto& [id, project] : m_projects) {
        (void)id;
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

std::optional<ProjectInfo> DbService::getProjectById(const std::string& id) const
{
    const auto it = m_projects.find(id);
    if (it == m_projects.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::string DbService::postToJson(const BlogPost& post) const
{
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

std::string DbService::allPostsToJson() const
{
    std::string json = "[";
    for (size_t i = 0; i < m_posts.size(); ++i) {
        if (i > 0) json += ",";
        json += postToJson(m_posts[i]);
    }
    json += "]";
    return json;
}

std::optional<BlogPost> DbService::getPostById(const std::string& id) const
{
    for (const auto& post : m_posts) {
        if (post.m_id == id) {
            return post;
        }
    }
    return std::nullopt;
}

std::string DbService::docToJson(const DocItem& doc) const
{
    std::string json = "{";
    json += "\"id\":\"" + escapeJson(doc.m_id) + "\",";
    json += "\"title\":\"" + escapeJson(doc.m_title) + "\",";
    json += "\"description\":\"" + escapeJson(doc.m_description) + "\",";
    json += "\"category\":\"" + escapeJson(doc.m_category) + "\",";
    json += "\"order\":" + std::to_string(doc.m_order);
    json += "}";
    return json;
}

std::string DbService::allDocsToJson() const
{
    std::string json = "[";
    for (size_t i = 0; i < m_docs.size(); ++i) {
        if (i > 0) json += ",";
        json += docToJson(m_docs[i]);
    }
    json += "]";
    return json;
}

std::optional<DocItem> DbService::getDocById(const std::string& id) const
{
    for (const auto& doc : m_docs) {
        if (doc.m_id == id) {
            return doc;
        }
    }
    return std::nullopt;
}
