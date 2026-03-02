#include "src/DbHttpClient.h"
#include "src/PasswordCodec.h"
#include "src/TokenStore.h"

#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/protoc/http/HttpRequest.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"
#include "galay-kernel/common/Log.h"

#include <atomic>
#include <chrono>
#include <csignal>
#include <cctype>
#include <cstdint>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <thread>

using namespace galay::http;
using namespace galay::kernel;

static std::atomic<bool> g_running{true};
static HttpServer* g_server = nullptr;
static std::unique_ptr<DbHttpClient> g_db_client;
static TokenStore g_token_store;

void signalHandler(int signum)
{
    LogInfo("auth-server received signal {}, shutting down", signum);
    g_running = false;
    if (g_server) {
        g_server->stop();
    }
}

std::string escapeJson(const std::string& str)
{
    std::string result;
    result.reserve(str.size() + 8);
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

std::string makeSuccessJson(const std::string& data_json)
{
    return "{\"success\":true,\"data\":" + data_json + "}";
}

std::string makeErrorJson(const std::string& message)
{
    return "{\"success\":false,\"error\":{\"message\":\"" + escapeJson(message) + "\"}}";
}

HttpResponse makeOkResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::ok()
        .header("Server", "Galay-Auth/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeBadRequestResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::badRequest()
        .header("Server", "Galay-Auth/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeUnauthorizedResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::unauthorized()
        .header("Server", "Galay-Auth/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeNotFoundResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::notFound()
        .header("Server", "Galay-Auth/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeInternalErrorResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::internalServerError()
        .header("Server", "Galay-Auth/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
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
    const size_t key_pos = body.find(pattern);
    if (key_pos == std::string::npos) {
        return std::nullopt;
    }

    const size_t colon_pos = body.find(':', key_pos + pattern.size());
    if (colon_pos == std::string::npos) {
        return std::nullopt;
    }

    size_t value_pos = colon_pos + 1;
    skipSpaces(body, value_pos);
    if (value_pos >= body.size() || body[value_pos] != '"') {
        return std::nullopt;
    }
    ++value_pos;

    std::string out;
    while (value_pos < body.size()) {
        const char ch = body[value_pos];
        if (ch == '\\' && value_pos + 1 < body.size()) {
            out.push_back(body[value_pos + 1]);
            value_pos += 2;
            continue;
        }
        if (ch == '"') {
            return out;
        }
        out.push_back(ch);
        ++value_pos;
    }

    return std::nullopt;
}

std::optional<bool> extractJsonBoolField(const std::string& body, const std::string& key)
{
    const std::string pattern = "\"" + key + "\"";
    const size_t key_pos = body.find(pattern);
    if (key_pos == std::string::npos) {
        return std::nullopt;
    }

    const size_t colon_pos = body.find(':', key_pos + pattern.size());
    if (colon_pos == std::string::npos) {
        return std::nullopt;
    }

    size_t value_pos = colon_pos + 1;
    skipSpaces(body, value_pos);
    if (value_pos >= body.size()) {
        return std::nullopt;
    }

    if (body.compare(value_pos, 4, "true") == 0) {
        return true;
    }
    if (body.compare(value_pos, 5, "false") == 0) {
        return false;
    }

    return std::nullopt;
}

std::string userToJson(const DbUserRecord& user)
{
    std::string json = "{";
    json += "\"id\":" + std::to_string(user.m_id) + ",";
    json += "\"username\":\"" + escapeJson(user.m_username) + "\",";
    json += "\"email\":\"" + escapeJson(user.m_email) + "\",";
    json += "\"display_name\":\"" + escapeJson(user.m_display_name) + "\",";
    json += "\"bio\":\"" + escapeJson(user.m_bio) + "\",";
    json += "\"website\":\"" + escapeJson(user.m_website) + "\",";
    json += "\"github\":\"" + escapeJson(user.m_github) + "\",";
    json += "\"notifications\":{";
    json += "\"email_notifications\":" + std::string(user.m_email_notifications ? "true" : "false") + ",";
    json += "\"new_post_notifications\":" + std::string(user.m_new_post_notifications ? "true" : "false") + ",";
    json += "\"comment_reply_notifications\":" +
            std::string(user.m_comment_reply_notifications ? "true" : "false") + ",";
    json += "\"release_notifications\":" + std::string(user.m_release_notifications ? "true" : "false");
    json += "}}";
    return json;
}

std::string notificationsToJson(const DbUserRecord& user)
{
    std::string json = "{";
    json += "\"email_notifications\":" + std::string(user.m_email_notifications ? "true" : "false") + ",";
    json += "\"new_post_notifications\":" + std::string(user.m_new_post_notifications ? "true" : "false") + ",";
    json += "\"comment_reply_notifications\":" +
            std::string(user.m_comment_reply_notifications ? "true" : "false") + ",";
    json += "\"release_notifications\":" + std::string(user.m_release_notifications ? "true" : "false");
    json += "}";
    return json;
}

std::optional<std::string> extractBearerToken(HttpRequest& req)
{
    const std::string auth = req.header().headerPairs().getValue("Authorization");
    constexpr std::string_view kPrefix = "Bearer ";
    if (auth.rfind(kPrefix.data(), 0) != 0) {
        return std::nullopt;
    }

    const std::string token = auth.substr(kPrefix.size());
    if (token.empty()) {
        return std::nullopt;
    }
    return token;
}

#define RETURN_RESPONSE(RESPONSE_EXPR)                                                      \
    do {                                                                                    \
        auto writer = conn.getWriter();                                                     \
        auto response = (RESPONSE_EXPR);                                                    \
        while (true) {                                                                      \
            auto result = co_await writer.sendResponse(response);                           \
            if (!result || result.value()) {                                                \
                break;                                                                      \
            }                                                                               \
        }                                                                                   \
        co_return;                                                                          \
    } while (false)

Coroutine healthHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    RETURN_RESPONSE(makeOkResponse(R"({"status":"ok","service":"auth","version":"1.0.0"})"));
}

Coroutine authRegisterHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("");
    const std::string email = extractJsonStringField(body, "email").value_or("");
    const std::string display_name = extractJsonStringField(body, "display_name").value_or(username);
    const std::string password_b64 = extractJsonStringField(body, "password_b64").value_or("");

    if (username.empty() || email.empty() || password_b64.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("username/email/password_b64 required")));
    }

    const auto plain_password = PasswordCodec::decodeBase64Password(password_b64);
    if (!plain_password) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(plain_password.error())));
    }

    const auto hashed = PasswordCodec::hashWithNewSalt(*plain_password);

    DbCreateUserInput input;
    input.m_username = username;
    input.m_email = email;
    input.m_display_name = display_name;
    input.m_bio = extractJsonStringField(body, "bio").value_or("");
    input.m_website = extractJsonStringField(body, "website").value_or("");
    input.m_github = extractJsonStringField(body, "github").value_or("");
    input.m_password_salt = hashed.m_salt;
    input.m_password_hash = hashed.m_hash;

    const auto created_user = g_db_client->createUser(input);
    if (!created_user) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(created_user.error())));
    }

    const AuthSessionInfo session = g_token_store.createSession(created_user->m_id, created_user->m_username);
    const std::string data_json =
        "{\"access_token\":\"" + escapeJson(session.m_access_token) + "\"," +
        "\"refresh_token\":\"" + escapeJson(session.m_refresh_token) + "\"," +
        "\"user\":" + userToJson(*created_user) + "}";

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(data_json)));
}

Coroutine authLoginHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const std::string body = req.bodyStr();
    const std::string username = extractJsonStringField(body, "username").value_or("");
    const std::string password_b64 = extractJsonStringField(body, "password_b64").value_or("");

    if (username.empty() || password_b64.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("username/password_b64 required")));
    }

    const auto db_user = g_db_client->getUserByUsername(username);
    if (!db_user) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("username or password invalid")));
    }

    const auto plain_password = PasswordCodec::decodeBase64Password(password_b64);
    if (!plain_password) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(plain_password.error())));
    }

    if (!PasswordCodec::verify(*plain_password, db_user->m_password_salt, db_user->m_password_hash)) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("username or password invalid")));
    }

    const AuthSessionInfo session = g_token_store.createSession(db_user->m_id, db_user->m_username);
    const std::string data_json =
        "{\"access_token\":\"" + escapeJson(session.m_access_token) + "\"," +
        "\"refresh_token\":\"" + escapeJson(session.m_refresh_token) + "\"," +
        "\"user\":" + userToJson(*db_user) + "}";

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(data_json)));
}

Coroutine authRefreshHandler(HttpConn& conn, HttpRequest req)
{
    const std::string body = req.bodyStr();
    const std::string refresh_token = extractJsonStringField(body, "refresh_token").value_or("");

    const auto refreshed = g_token_store.refresh(refresh_token);
    if (!refreshed) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson(refreshed.error())));
    }

    const std::string data_json =
        "{\"access_token\":\"" + escapeJson(refreshed->m_access_token) + "\"}";
    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(data_json)));
}

Coroutine authLogoutHandler(HttpConn& conn, HttpRequest req)
{
    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    g_token_store.revokeByAccessToken(*access_token);
    RETURN_RESPONSE(makeOkResponse(makeSuccessJson("{}")));
}

Coroutine authMeHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto session = g_token_store.findByAccessToken(*access_token);
    if (!session.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto db_user = g_db_client->getUserById(session->m_user_id);
    if (!db_user) {
        if (db_user.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(db_user.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(db_user.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*db_user))));
}

Coroutine authUpdateProfileHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto session = g_token_store.findByAccessToken(*access_token);
    if (!session.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const std::string body = req.bodyStr();
    DbUpdateUserInput input;
    input.m_email = extractJsonStringField(body, "email");
    input.m_display_name = extractJsonStringField(body, "display_name");
    input.m_bio = extractJsonStringField(body, "bio");
    input.m_website = extractJsonStringField(body, "website");
    input.m_github = extractJsonStringField(body, "github");

    const auto updated_user = g_db_client->updateUser(session->m_user_id, input);
    if (!updated_user) {
        if (updated_user.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(updated_user.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(updated_user.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*updated_user))));
}

Coroutine authUpdatePasswordHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto session = g_token_store.findByAccessToken(*access_token);
    if (!session.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const std::string body = req.bodyStr();
    const std::string old_password_b64 = extractJsonStringField(body, "old_password_b64").value_or("");
    const std::string new_password_b64 = extractJsonStringField(body, "new_password_b64").value_or("");
    if (new_password_b64.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("new_password_b64 required")));
    }

    const auto db_user = g_db_client->getUserById(session->m_user_id);
    if (!db_user) {
        if (db_user.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(db_user.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(db_user.error())));
    }

    if (!old_password_b64.empty()) {
        const auto old_password = PasswordCodec::decodeBase64Password(old_password_b64);
        if (!old_password) {
            RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(old_password.error())));
        }
        if (!PasswordCodec::verify(*old_password, db_user->m_password_salt, db_user->m_password_hash)) {
            RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("old password invalid")));
        }
    }

    const auto new_password = PasswordCodec::decodeBase64Password(new_password_b64);
    if (!new_password) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(new_password.error())));
    }

    const auto hashed = PasswordCodec::hashWithNewSalt(*new_password);
    DbUpdatePasswordInput input;
    input.m_password_salt = hashed.m_salt;
    input.m_password_hash = hashed.m_hash;

    const auto updated_user = g_db_client->updatePassword(session->m_user_id, input);
    if (!updated_user) {
        if (updated_user.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(updated_user.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(updated_user.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson("{}")));
}

Coroutine authUpdateNotificationsHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto session = g_token_store.findByAccessToken(*access_token);
    if (!session.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const std::string body = req.bodyStr();
    DbUpdateNotificationsInput input;
    input.m_email_notifications = extractJsonBoolField(body, "email_notifications");
    input.m_new_post_notifications = extractJsonBoolField(body, "new_post_notifications");
    input.m_comment_reply_notifications = extractJsonBoolField(body, "comment_reply_notifications");
    input.m_release_notifications = extractJsonBoolField(body, "release_notifications");

    const auto updated_user = g_db_client->updateNotifications(session->m_user_id, input);
    if (!updated_user) {
        if (updated_user.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(updated_user.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(updated_user.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(notificationsToJson(*updated_user))));
}

Coroutine authDeleteAccountHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_client) {
        RETURN_RESPONSE(makeInternalErrorResponse(makeErrorJson("db client unavailable")));
    }

    const auto access_token = extractBearerToken(req);
    if (!access_token.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto session = g_token_store.findByAccessToken(*access_token);
    if (!session.has_value()) {
        RETURN_RESPONSE(makeUnauthorizedResponse(makeErrorJson("unauthorized")));
    }

    const auto deleted = g_db_client->deleteUser(session->m_user_id);
    if (!deleted) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(deleted.error())));
    }

    g_token_store.revokeByUserId(session->m_user_id);
    RETURN_RESPONSE(makeOkResponse(makeSuccessJson("{}")));
}

int main(int argc, char* argv[])
{
    std::string host = "0.0.0.0";
    std::uint16_t port = 8081;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if ((arg == "-h" || arg == "--host") && i + 1 < argc) {
            host = argv[++i];
        } else if ((arg == "-p" || arg == "--port") && i + 1 < argc) {
            port = static_cast<std::uint16_t>(std::stoi(argv[++i]));
        } else if (arg == "--help") {
            std::cout << "Auth Service\n"
                      << "Usage: " << argv[0] << " [options]\n"
                      << "Options:\n"
                      << "  -h, --host <host>    Server host (default: 0.0.0.0)\n"
                      << "  -p, --port <port>    Server port (default: 8081)\n"
                      << "  --help               Show this help\n";
            return 0;
        }
    }

    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    g_db_client = std::make_unique<DbHttpClient>();
    LogInfo("auth-server db upstream base url: {}", g_db_client->baseUrl());

    HttpRouter router;
    router.addHandler<HttpMethod::GET>("/health", healthHandler);

    const auto joinRoute = [](const std::string& prefix, const std::string& path) {
        return prefix.empty() ? path : prefix + path;
    };

    for (const std::string& authPrefix : {std::string("/api/v1/auth"), std::string("/auth"), std::string("")}) {
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/register"), authRegisterHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/login"), authLoginHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/refresh"), authRefreshHandler);
        router.addHandler<HttpMethod::POST>(joinRoute(authPrefix, "/logout"), authLogoutHandler);
        router.addHandler<HttpMethod::GET>(joinRoute(authPrefix, "/me"), authMeHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/profile"), authUpdateProfileHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/password"), authUpdatePasswordHandler);
        router.addHandler<HttpMethod::PUT>(joinRoute(authPrefix, "/notifications"), authUpdateNotificationsHandler);
        router.addHandler<HttpMethod::DELETE>(joinRoute(authPrefix, "/account"), authDeleteAccountHandler);
    }

    HttpServerConfig config;
    config.host = host;
    config.port = port;
    config.backlog = 128;

    HttpServer server(config);
    g_server = &server;

    try {
        server.start(std::move(router));
        LogInfo("auth-server listening on {}:{}", host, port);

        while (g_running && server.isRunning()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        LogError("auth-server failed: {}", e.what());
        return 1;
    }

    return 0;
}
