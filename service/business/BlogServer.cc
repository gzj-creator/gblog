/**
 * @file BlogServer.cc
 * @brief Galay Blog 后端服务器
 * @details 使用 galay-http 框架实现的博客后端服务器，提供静态文件服务和 RESTful API
 */

#include "AuthService.h"
#include "DbService.h"

#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpLog.h"
#include "galay-http/protoc/http/HttpRequest.h"
#include "galay-http/protoc/http/HttpResponse.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"

#include <atomic>
#include <chrono>
#include <csignal>
#include <cctype>
#include <filesystem>
#include <iostream>
#include <optional>
#include <string>
#include <thread>

using namespace galay::http;
using namespace galay::kernel;

// ============================================
// 全局变量
// ============================================

static HttpServer* g_server = nullptr;
static std::atomic<bool> g_running{true};
static DbService g_db_service;
static AuthService g_auth_service;

// ============================================
// 信号处理
// ============================================

void signalHandler(int signum)
{
    HTTP_LOG_INFO("Received signal {}, shutting down...", signum);
    g_running = false;
    if (g_server) {
        g_server->stop();
    }
}

// ============================================
// JSON / 请求辅助函数
// ============================================

std::string escapeJson(const std::string& str)
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

std::string makeSuccessJson(const std::string& dataJson)
{
    return "{\"success\":true,\"data\":" + dataJson + "}";
}

std::string makeErrorJson(const std::string& message)
{
    return "{\"success\":false,\"error\":{\"message\":\"" + escapeJson(message) + "\"}}";
}

void skipSpaces(const std::string& source, size_t& pos)
{
    while (pos < source.size() && std::isspace(static_cast<unsigned char>(source[pos]))) {
        ++pos;
    }
}

std::optional<std::string> extractJsonStringField(const std::string& body, const std::string& key)
{
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

std::optional<bool> extractJsonBoolField(const std::string& body, const std::string& key)
{
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

std::string extractPathId(HttpRequest& req)
{
    std::string uri = req.header().uri();
    const size_t lastSlash = uri.rfind('/');
    std::string id = uri.substr(lastSlash + 1);

    const size_t queryPos = id.find('?');
    if (queryPos != std::string::npos) {
        id = id.substr(0, queryPos);
    }

    return id;
}

std::string extractAuthorizationHeader(HttpRequest& req)
{
    return req.header().headerPairs().getValue("Authorization");
}

void registerDbRoutes(HttpRouter& router);
void registerAuthRoutes(HttpRouter& router);

// ============================================
// API 处理器
// ============================================

Coroutine healthHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    const std::string body = R"({"status":"ok","server":"Galay-Blog","version":"1.0.0"})";

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

Coroutine getProjectsHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    const std::string body = g_db_service.allProjectsToJson();

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

Coroutine getProjectByIdHandler(HttpConn& conn, HttpRequest req)
{
    const std::string projectId = extractPathId(req);
    auto project = g_db_service.getProjectById(projectId);

    auto writer = conn.getWriter();
    if (!project.has_value()) {
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

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(g_db_service.projectToJson(*project))
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

Coroutine getPostsHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(g_db_service.allPostsToJson())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

Coroutine getPostByIdHandler(HttpConn& conn, HttpRequest req)
{
    const std::string postId = extractPathId(req);
    auto post = g_db_service.getPostById(postId);

    auto writer = conn.getWriter();
    if (!post.has_value()) {
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

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(g_db_service.postToJson(*post))
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

Coroutine getDocsHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(g_db_service.allDocsToJson())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

Coroutine getDocByIdHandler(HttpConn& conn, HttpRequest req)
{
    const std::string docId = extractPathId(req);
    auto doc = g_db_service.getDocById(docId);

    auto writer = conn.getWriter();
    if (!doc.has_value()) {
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

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(g_db_service.docToJson(*doc))
        .build();

    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

Coroutine authLoginHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("demo");
    const std::string password = extractJsonStringField(body, "password").value_or("");

    const AuthService::LoginResult result = g_auth_service.login(username, password);

    const std::string dataJson =
        "{\"access_token\":\"" + escapeJson(result.m_access_token) + "\","
        "\"refresh_token\":\"" + escapeJson(result.m_refresh_token) + "\","
        "\"user\":" + AuthService::userToJson(result.m_user) + "}";

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(dataJson))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authRegisterHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("demo");
    const std::string email = extractJsonStringField(body, "email").value_or("demo@example.com");
    const std::string password = extractJsonStringField(body, "password").value_or("demo123456");

    const AuthUser user = g_auth_service.registerUser(username, email, password);

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(AuthService::userToJson(user)))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authRefreshHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    const std::string refreshToken = extractJsonStringField(body, "refresh_token").value_or("");
    const auto accessToken = g_auth_service.refreshAccessToken(refreshToken);

    auto writer = conn.getWriter();
    if (!accessToken.has_value()) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("refresh token invalid"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    const std::string dataJson = "{\"access_token\":\"" + escapeJson(*accessToken) + "\"}";
    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(dataJson))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authLogoutHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    g_auth_service.logout();

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson("{}"))
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authMeHandler(HttpConn& conn, HttpRequest req)
{
    const auto user = g_auth_service.getCurrentUser(extractAuthorizationHeader(req));
    auto writer = conn.getWriter();

    if (!user.has_value()) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(AuthService::userToJson(*user)))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authUpdateProfileHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    AuthProfilePatch patch;
    patch.m_display_name = extractJsonStringField(body, "display_name");
    patch.m_email = extractJsonStringField(body, "email");
    patch.m_bio = extractJsonStringField(body, "bio");
    patch.m_website = extractJsonStringField(body, "website");
    patch.m_github = extractJsonStringField(body, "github");

    const auto user = g_auth_service.updateProfile(extractAuthorizationHeader(req), patch);
    auto writer = conn.getWriter();

    if (!user.has_value()) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(AuthService::userToJson(*user)))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authUpdatePasswordHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    const std::string oldPassword = extractJsonStringField(body, "old_password").value_or("");
    const std::string newPassword = extractJsonStringField(body, "new_password").value_or("");

    const PasswordUpdateStatus status =
        g_auth_service.updatePassword(extractAuthorizationHeader(req), oldPassword, newPassword);

    auto writer = conn.getWriter();
    if (status == PasswordUpdateStatus::kUnauthorized) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    if (status == PasswordUpdateStatus::kOldPasswordIncorrect) {
        auto response = Http1_1ResponseBuilder::badRequest()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("old password incorrect"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson("{}"))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authUpdateNotificationsHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    NotificationSettingsPatch patch;
    patch.m_email_notifications = extractJsonBoolField(body, "email_notifications");
    patch.m_new_post_notifications = extractJsonBoolField(body, "new_post_notifications");
    patch.m_comment_reply_notifications = extractJsonBoolField(body, "comment_reply_notifications");
    patch.m_release_notifications = extractJsonBoolField(body, "release_notifications");

    const auto settings = g_auth_service.updateNotifications(extractAuthorizationHeader(req), patch);
    auto writer = conn.getWriter();

    if (!settings.has_value()) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson(AuthService::notificationSettingsToJson(*settings)))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

Coroutine authDeleteAccountHandler(HttpConn& conn, HttpRequest req)
{
    const bool deleted = g_auth_service.deleteAccount(extractAuthorizationHeader(req));
    auto writer = conn.getWriter();

    if (!deleted) {
        auto response = Http1_1ResponseBuilder::unauthorized()
            .header("Server", "Galay-Blog/1.0")
            .header("Access-Control-Allow-Origin", "*")
            .json(makeErrorJson("unauthorized"))
            .build();
        while (true) {
            auto sendResult = co_await writer.sendResponse(response);
            if (!sendResult || sendResult.value()) break;
        }
        co_return;
    }

    auto response = Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Blog/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(makeSuccessJson("{}"))
        .build();

    while (true) {
        auto sendResult = co_await writer.sendResponse(response);
        if (!sendResult || sendResult.value()) break;
    }
    co_return;
}

// ============================================
// 路由注册（拆分为独立服务域）
// ============================================

std::string joinRoute(const std::string& prefix, const std::string& path)
{
    return prefix.empty() ? path : prefix + path;
}

void registerDbRoutes(HttpRouter& router)
{
    for (const std::string& prefix : {std::string("/api"), std::string("")}) {
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/health"), healthHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/projects"), getProjectsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/projects/:id"), getProjectByIdHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/posts"), getPostsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/posts/:id"), getPostByIdHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/docs"), getDocsHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(prefix, "/docs/:id"), getDocByIdHandler);
    }
}

void registerAuthRoutes(HttpRouter& router)
{
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
}

// ============================================
// 主函数
// ============================================

int main(int argc, char* argv[])
{
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

    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    HTTP_LOG_INFO("============================================");
    HTTP_LOG_INFO("       Galay Blog Server v1.0.0");
    HTTP_LOG_INFO("============================================");

    HttpRouter router;
    registerDbRoutes(router);
    registerAuthRoutes(router);

    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setSmallFileThreshold(64 * 1024);    // 64KB
    staticConfig.setLargeFileThreshold(1024 * 1024);  // 1MB

    if (!staticDir.empty()) {
        if (!std::filesystem::exists(staticDir) || !std::filesystem::is_directory(staticDir)) {
            HTTP_LOG_WARN("Static directory not found, static mount skipped: {}", staticDir);
        } else {
            router.mount("/", staticDir, staticConfig);
            HTTP_LOG_INFO("Static files: {}", staticDir);
        }
    } else {
        HTTP_LOG_INFO("Static files: disabled");
    }

    HTTP_LOG_INFO("Service split: AuthService + DbService");
    HTTP_LOG_INFO("API endpoints:");
    HTTP_LOG_INFO("  GET /health, /projects, /projects/:id, /posts, /posts/:id, /docs, /docs/:id");
    HTTP_LOG_INFO("  POST /auth/login, /auth/register, /auth/refresh, /auth/logout");
    HTTP_LOG_INFO("  GET /auth/me");
    HTTP_LOG_INFO("  PUT /auth/profile, /auth/password, /auth/notifications");
    HTTP_LOG_INFO("  DELETE /auth/account");
    HTTP_LOG_INFO("Starting server on {}:{}", host, port);
    HTTP_LOG_INFO("============================================");

    HttpServerConfig config;
    config.host = host;
    config.port = port;
    config.backlog = 128;
    config.io_scheduler_count = GALAY_RUNTIME_SCHEDULER_COUNT_AUTO;
    config.compute_scheduler_count = GALAY_RUNTIME_SCHEDULER_COUNT_AUTO;

    HttpServer server(config);
    g_server = &server;

    try {
        server.start(std::move(router));

        HTTP_LOG_INFO("Server started successfully!");
        HTTP_LOG_INFO("Open http://localhost:{} in your browser", port);
        HTTP_LOG_INFO("Press Ctrl+C to stop");

        while (g_running && server.isRunning()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        HTTP_LOG_ERROR("Server error: {}", e.what());
        return 1;
    }

    HTTP_LOG_INFO("Server stopped.");
    return 0;
}
