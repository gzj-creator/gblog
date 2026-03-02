#include "src/DbProvider.h"
#include "src/MySqlDbProvider.h"

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
#include <vector>

using namespace galay::http;
using namespace galay::kernel;

static std::atomic<bool> g_running{true};
static HttpServer* g_server = nullptr;
static std::unique_ptr<DbProvider> g_db_provider;

void signalHandler(int signum)
{
    LogInfo("db-server received signal {}, shutting down", signum);
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
        .header("Server", "Galay-DB/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeBadRequestResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::badRequest()
        .header("Server", "Galay-DB/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body)
        .build();
}

HttpResponse makeNotFoundResponse(const std::string& body)
{
    return Http1_1ResponseBuilder::notFound()
        .header("Server", "Galay-DB/1.0")
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

std::optional<std::uint64_t> extractJsonUint64Field(const std::string& body, const std::string& key)
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

    size_t end = value_pos;
    while (end < body.size() && std::isdigit(static_cast<unsigned char>(body[end]))) {
        ++end;
    }
    if (end == value_pos) {
        return std::nullopt;
    }

    try {
        return static_cast<std::uint64_t>(std::stoull(body.substr(value_pos, end - value_pos)));
    } catch (...) {
        return std::nullopt;
    }
}

std::optional<std::uint64_t> parseUint64(const std::string& raw)
{
    try {
        return static_cast<std::uint64_t>(std::stoull(raw));
    } catch (...) {
        return std::nullopt;
    }
}

std::string extractPathTail(HttpRequest& req)
{
    std::string uri = req.header().uri();
    const size_t q = uri.find('?');
    if (q != std::string::npos) {
        uri = uri.substr(0, q);
    }

    const size_t slash = uri.rfind('/');
    if (slash == std::string::npos || slash + 1 >= uri.size()) {
        return "";
    }
    return uri.substr(slash + 1);
}

std::optional<std::string> extractQueryParam(HttpRequest& req, const std::string& key)
{
    std::string uri = req.header().uri();
    const size_t q = uri.find('?');
    if (q == std::string::npos || q + 1 >= uri.size()) {
        return std::nullopt;
    }

    const std::string query = uri.substr(q + 1);
    size_t start = 0;
    while (start <= query.size()) {
        const size_t amp = query.find('&', start);
        const size_t end = (amp == std::string::npos) ? query.size() : amp;
        const std::string pair = query.substr(start, end - start);
        const size_t eq = pair.find('=');

        std::string k;
        std::string v;
        if (eq == std::string::npos) {
            k = pair;
            v = "";
        } else {
            k = pair.substr(0, eq);
            v = pair.substr(eq + 1);
        }

        if (k == key) {
            return v;
        }

        if (amp == std::string::npos) {
            break;
        }
        start = amp + 1;
    }

    return std::nullopt;
}

bool parseBoolValue(const std::string& raw, bool fallback)
{
    if (raw == "1" || raw == "true" || raw == "yes" || raw == "on") {
        return true;
    }
    if (raw == "0" || raw == "false" || raw == "no" || raw == "off") {
        return false;
    }
    return fallback;
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
    json += "\"password_salt\":\"" + escapeJson(user.m_password_salt) + "\",";
    json += "\"password_hash\":\"" + escapeJson(user.m_password_hash) + "\",";
    json += "\"notifications\":{";
    json += "\"email_notifications\":" + std::string(user.m_email_notifications ? "true" : "false") + ",";
    json += "\"new_post_notifications\":" +
            std::string(user.m_new_post_notifications ? "true" : "false") + ",";
    json += "\"comment_reply_notifications\":" +
            std::string(user.m_comment_reply_notifications ? "true" : "false") + ",";
    json += "\"release_notifications\":" + std::string(user.m_release_notifications ? "true" : "false");
    json += "}}";
    return json;
}

std::string documentToJson(const DbDocumentRecord& doc)
{
    std::string json = "{";
    json += "\"id\":" + std::to_string(doc.m_id) + ",";
    json += "\"project\":\"" + escapeJson(doc.m_project) + "\",";
    json += "\"relative_path\":\"" + escapeJson(doc.m_relative_path) + "\",";
    json += "\"sha256\":\"" + escapeJson(doc.m_sha256) + "\",";
    json += "\"size_bytes\":" + std::to_string(doc.m_size_bytes) + ",";
    json += "\"doc_version\":" + std::to_string(doc.m_doc_version) + ",";
    json += "\"is_deleted\":" + std::string(doc.m_is_deleted ? "true" : "false") + ",";
    json += "\"created_at\":\"" + escapeJson(doc.m_created_at) + "\",";
    json += "\"updated_at\":\"" + escapeJson(doc.m_updated_at) + "\"";
    json += "}";
    return json;
}

std::string documentsToJson(const std::vector<DbDocumentRecord>& docs)
{
    std::string json = "[";
    for (size_t i = 0; i < docs.size(); ++i) {
        if (i != 0) {
            json += ",";
        }
        json += documentToJson(docs[i]);
    }
    json += "]";
    return json;
}

std::string indexJobToJson(const DbIndexJobRecord& job)
{
    std::string json = "{";
    json += "\"id\":" + std::to_string(job.m_id) + ",";
    json += "\"job_type\":\"" + escapeJson(job.m_job_type) + "\",";
    json += "\"project\":\"" + escapeJson(job.m_project) + "\",";
    json += "\"relative_path\":\"" + escapeJson(job.m_relative_path) + "\",";
    if (job.m_document_id.has_value()) {
        json += "\"document_id\":" + std::to_string(*job.m_document_id) + ",";
    } else {
        json += "\"document_id\":null,";
    }
    json += "\"status\":\"" + escapeJson(job.m_status) + "\",";
    json += "\"attempts\":" + std::to_string(job.m_attempts) + ",";
    json += "\"trigger_source\":\"" + escapeJson(job.m_trigger_source) + "\",";
    json += "\"payload_json\":" + job.m_payload_json + ",";
    json += "\"error_message\":\"" + escapeJson(job.m_error_message) + "\",";
    json += "\"created_at\":\"" + escapeJson(job.m_created_at) + "\",";
    json += "\"updated_at\":\"" + escapeJson(job.m_updated_at) + "\",";
    json += "\"started_at\":\"" + escapeJson(job.m_started_at) + "\",";
    json += "\"finished_at\":\"" + escapeJson(job.m_finished_at) + "\"";
    json += "}";
    return json;
}

std::string indexStateToJson(const DbIndexStateRecord& state)
{
    std::string json = "{";
    json += "\"current_version\":" + std::to_string(state.m_current_version) + ",";
    if (state.m_last_success_job_id.has_value()) {
        json += "\"last_success_job_id\":" + std::to_string(*state.m_last_success_job_id) + ",";
    } else {
        json += "\"last_success_job_id\":null,";
    }
    json += "\"updated_at\":\"" + escapeJson(state.m_updated_at) + "\"";
    json += "}";
    return json;
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
    RETURN_RESPONSE(makeOkResponse(R"({"status":"ok","service":"db","version":"1.0.0"})"));
}

Coroutine createUserHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    DbCreateUserInput input;
    input.m_username = extractJsonStringField(body, "username").value_or("");
    input.m_email = extractJsonStringField(body, "email").value_or("");
    input.m_display_name = extractJsonStringField(body, "display_name").value_or(input.m_username);
    input.m_bio = extractJsonStringField(body, "bio").value_or("");
    input.m_website = extractJsonStringField(body, "website").value_or("");
    input.m_github = extractJsonStringField(body, "github").value_or("");
    input.m_password_salt = extractJsonStringField(body, "password_salt").value_or("");
    input.m_password_hash = extractJsonStringField(body, "password_hash").value_or("");

    if (input.m_username.empty() || input.m_email.empty() || input.m_password_salt.empty() ||
        input.m_password_hash.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(
            "username/email/password_salt/password_hash required")));
    }

    const auto result = g_db_provider->createUser(input);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine getUserByUsernameHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string username = extractPathTail(req);
    if (username.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("username required")));
    }

    const auto result = g_db_provider->getUserByUsername(username);
    if (!result) {
        if (result.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine getUserByIdHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto userId = parseUint64(extractPathTail(req));
    if (!userId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid user id")));
    }

    const auto result = g_db_provider->getUserById(*userId);
    if (!result) {
        if (result.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine updateUserHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto userId = parseUint64(extractPathTail(req));
    if (!userId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid user id")));
    }

    const std::string body = req.bodyStr();
    DbUpdateUserInput input;
    input.m_email = extractJsonStringField(body, "email");
    input.m_display_name = extractJsonStringField(body, "display_name");
    input.m_bio = extractJsonStringField(body, "bio");
    input.m_website = extractJsonStringField(body, "website");
    input.m_github = extractJsonStringField(body, "github");

    const auto result = g_db_provider->updateUser(*userId, input);
    if (!result) {
        if (result.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine updatePasswordHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto userId = parseUint64(extractPathTail(req));
    if (!userId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid user id")));
    }

    const std::string body = req.bodyStr();
    DbUpdatePasswordInput input;
    input.m_password_salt = extractJsonStringField(body, "password_salt").value_or("");
    input.m_password_hash = extractJsonStringField(body, "password_hash").value_or("");

    if (input.m_password_salt.empty() || input.m_password_hash.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("password_salt/password_hash required")));
    }

    const auto result = g_db_provider->updatePassword(*userId, input);
    if (!result) {
        if (result.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine updateNotificationsHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto userId = parseUint64(extractPathTail(req));
    if (!userId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid user id")));
    }

    const std::string body = req.bodyStr();
    DbUpdateNotificationsInput input;
    input.m_email_notifications = extractJsonBoolField(body, "email_notifications");
    input.m_new_post_notifications = extractJsonBoolField(body, "new_post_notifications");
    input.m_comment_reply_notifications = extractJsonBoolField(body, "comment_reply_notifications");
    input.m_release_notifications = extractJsonBoolField(body, "release_notifications");

    const auto result = g_db_provider->updateNotifications(*userId, input);
    if (!result) {
        if (result.error() == "user not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(userToJson(*result))));
}

Coroutine deleteUserHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto userId = parseUint64(extractPathTail(req));
    if (!userId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid user id")));
    }

    const auto result = g_db_provider->deleteUser(*userId);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson("{}")));
}

Coroutine upsertDocumentHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    DbUpsertDocumentInput input;
    input.m_project = extractJsonStringField(body, "project").value_or("");
    input.m_relative_path = extractJsonStringField(body, "relative_path").value_or("");
    input.m_sha256 = extractJsonStringField(body, "sha256").value_or("");
    input.m_size_bytes = extractJsonUint64Field(body, "size_bytes").value_or(0);
    input.m_doc_version = extractJsonUint64Field(body, "doc_version");
    input.m_is_deleted = extractJsonBoolField(body, "is_deleted");

    if (input.m_project.empty() || input.m_relative_path.empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("project/relative_path required")));
    }

    const auto result = g_db_provider->upsertDocument(input);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(documentToJson(*result))));
}

Coroutine getDocumentHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    std::optional<std::string> project = extractJsonStringField(body, "project");
    std::optional<std::string> relativePath = extractJsonStringField(body, "relative_path");

    if (!project.has_value() || project->empty()) {
        project = extractQueryParam(req, "project");
    }
    if (!relativePath.has_value() || relativePath->empty()) {
        relativePath = extractQueryParam(req, "relative_path");
    }

    if (!project.has_value() || project->empty() || !relativePath.has_value() || relativePath->empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("project/relative_path required")));
    }

    const auto result = g_db_provider->getDocument(*project, *relativePath);
    if (!result) {
        if (result.error() == "document not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(documentToJson(*result))));
}

Coroutine listDocumentsHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    DbListDocumentsInput input;

    const auto projectFromBody = extractJsonStringField(body, "project");
    if (projectFromBody.has_value() && !projectFromBody->empty()) {
        input.m_project = *projectFromBody;
    } else {
        const auto projectFromQuery = extractQueryParam(req, "project");
        if (projectFromQuery.has_value() && !projectFromQuery->empty()) {
            input.m_project = *projectFromQuery;
        }
    }

    const auto includeDeletedFromBody = extractJsonBoolField(body, "include_deleted");
    if (includeDeletedFromBody.has_value()) {
        input.m_include_deleted = *includeDeletedFromBody;
    } else {
        const auto includeDeletedFromQuery = extractQueryParam(req, "include_deleted");
        if (includeDeletedFromQuery.has_value()) {
            input.m_include_deleted = parseBoolValue(*includeDeletedFromQuery, false);
        }
    }

    const auto result = g_db_provider->listDocuments(input);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(documentsToJson(*result))));
}

Coroutine deleteDocumentHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    std::optional<std::string> project = extractJsonStringField(body, "project");
    std::optional<std::string> relativePath = extractJsonStringField(body, "relative_path");

    if (!project.has_value() || project->empty()) {
        project = extractQueryParam(req, "project");
    }
    if (!relativePath.has_value() || relativePath->empty()) {
        relativePath = extractQueryParam(req, "relative_path");
    }

    if (!project.has_value() || project->empty() || !relativePath.has_value() || relativePath->empty()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("project/relative_path required")));
    }

    const auto result = g_db_provider->markDocumentDeleted(*project, *relativePath);
    if (!result) {
        if (result.error() == "document not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(documentToJson(*result))));
}

Coroutine createIndexJobHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    DbCreateIndexJobInput input;
    input.m_job_type = extractJsonStringField(body, "job_type").value_or("reindex");
    input.m_project = extractJsonStringField(body, "project").value_or("");
    input.m_relative_path = extractJsonStringField(body, "relative_path").value_or("");
    input.m_document_id = extractJsonUint64Field(body, "document_id");
    input.m_trigger_source = extractJsonStringField(body, "trigger_source").value_or("admin");
    input.m_payload_json = extractJsonStringField(body, "payload_json").value_or("{}");

    const auto result = g_db_provider->createIndexJob(input);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(indexJobToJson(*result))));
}

Coroutine fetchNextIndexJobHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto result = g_db_provider->fetchNextPendingIndexJob();
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    if (!result->has_value()) {
        RETURN_RESPONSE(makeOkResponse(makeSuccessJson("null")));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(indexJobToJson(**result))));
}

Coroutine getIndexJobHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto jobId = parseUint64(extractPathTail(req));
    if (!jobId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("invalid job id")));
    }

    const auto result = g_db_provider->getIndexJobById(*jobId);
    if (!result) {
        if (result.error() == "index job not found") {
            RETURN_RESPONSE(makeNotFoundResponse(makeErrorJson(result.error())));
        }
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(indexJobToJson(*result))));
}

Coroutine finishIndexJobSuccessHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    const auto jobId = extractJsonUint64Field(body, "job_id");
    if (!jobId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("job_id required")));
    }

    const auto jobResult = g_db_provider->finishIndexJobSuccess(*jobId);
    if (!jobResult) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(jobResult.error())));
    }

    const auto stateResult = g_db_provider->getIndexState();
    if (!stateResult) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(stateResult.error())));
    }

    const std::string payload = "{\"job\":" + indexJobToJson(*jobResult) +
                                ",\"index_state\":" + indexStateToJson(*stateResult) + "}";
    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(payload)));
}

Coroutine finishIndexJobFailedHandler(HttpConn& conn, HttpRequest req)
{
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const std::string body = req.bodyStr();
    const auto jobId = extractJsonUint64Field(body, "job_id");
    const std::string errorMessage = extractJsonStringField(body, "error_message").value_or("index failed");
    if (!jobId.has_value()) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("job_id required")));
    }

    const auto result = g_db_provider->finishIndexJobFailed(*jobId, errorMessage);
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(indexJobToJson(*result))));
}

Coroutine getIndexStateHandler(HttpConn& conn, HttpRequest req)
{
    (void)req;
    if (!g_db_provider) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson("db provider unavailable")));
    }

    const auto result = g_db_provider->getIndexState();
    if (!result) {
        RETURN_RESPONSE(makeBadRequestResponse(makeErrorJson(result.error())));
    }

    RETURN_RESPONSE(makeOkResponse(makeSuccessJson(indexStateToJson(*result))));
}

int main(int argc, char* argv[])
{
    std::string host = "0.0.0.0";
    std::uint16_t port = 8082;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if ((arg == "-h" || arg == "--host") && i + 1 < argc) {
            host = argv[++i];
        } else if ((arg == "-p" || arg == "--port") && i + 1 < argc) {
            port = static_cast<std::uint16_t>(std::stoi(argv[++i]));
        } else if (arg == "--help") {
            std::cout << "DB Service\n"
                      << "Usage: " << argv[0] << " [options]\n"
                      << "Options:\n"
                      << "  -h, --host <host>    Server host (default: 0.0.0.0)\n"
                      << "  -p, --port <port>    Server port (default: 8082)\n"
                      << "  --help               Show this help\n";
            return 0;
        }
    }

    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    g_db_provider = std::make_unique<MySqlDbProvider>();

    HttpRouter router;
    router.addHandler<HttpMethod::GET>("/health", healthHandler);

    router.addHandler<HttpMethod::POST>("/api/v1/db/users/create", createUserHandler);
    router.addHandler<HttpMethod::GET>("/api/v1/db/users/get-by-username/:username", getUserByUsernameHandler);
    router.addHandler<HttpMethod::GET>("/api/v1/db/users/get/:id", getUserByIdHandler);
    router.addHandler<HttpMethod::PATCH>("/api/v1/db/users/update/:id", updateUserHandler);
    router.addHandler<HttpMethod::PUT>("/api/v1/db/users/update-password/:id", updatePasswordHandler);
    router.addHandler<HttpMethod::PUT>("/api/v1/db/users/update-notifications/:id", updateNotificationsHandler);
    router.addHandler<HttpMethod::DELETE>("/api/v1/db/users/delete/:id", deleteUserHandler);

    router.addHandler<HttpMethod::POST>("/api/v1/db/documents/upsert", upsertDocumentHandler);
    router.addHandler<HttpMethod::GET>("/api/v1/db/documents/get", getDocumentHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/documents/get", getDocumentHandler);
    router.addHandler<HttpMethod::GET>("/api/v1/db/documents/list", listDocumentsHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/documents/list", listDocumentsHandler);
    router.addHandler<HttpMethod::DELETE>("/api/v1/db/documents/delete", deleteDocumentHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/documents/delete", deleteDocumentHandler);

    router.addHandler<HttpMethod::POST>("/api/v1/db/index-jobs/create", createIndexJobHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/index-jobs/fetch-next", fetchNextIndexJobHandler);
    router.addHandler<HttpMethod::GET>("/api/v1/db/index-jobs/get/:id", getIndexJobHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/index-jobs/finish-success", finishIndexJobSuccessHandler);
    router.addHandler<HttpMethod::POST>("/api/v1/db/index-jobs/finish-failed", finishIndexJobFailedHandler);

    router.addHandler<HttpMethod::GET>("/api/v1/db/index/state", getIndexStateHandler);

    HttpServerConfig config;
    config.host = host;
    config.port = port;
    config.backlog = 128;

    HttpServer server(config);
    g_server = &server;

    try {
        server.start(std::move(router));
        LogInfo("db-server listening on {}:{}", host, port);

        while (g_running && server.isRunning()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        LogError("db-server failed: {}", e.what());
        return 1;
    }

    return 0;
}
