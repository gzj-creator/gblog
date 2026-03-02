#include "DbHttpClient.h"

#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include <cerrno>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <optional>
#include <sstream>
#include <string>

namespace {

std::string getEnvOrDefault(const char* key, const std::string& fallback)
{
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return fallback;
    }
    const std::string value(raw);
    return value.empty() ? fallback : value;
}

std::uint16_t getPortFromEnv(const char* key, std::uint16_t fallback)
{
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return fallback;
    }

    try {
        const int parsed = std::stoi(raw);
        if (parsed <= 0 || parsed > 65535) {
            return fallback;
        }
        return static_cast<std::uint16_t>(parsed);
    } catch (...) {
        return fallback;
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
    const std::string pattern = "\"" + key + "\":";
    const size_t key_pos = body.find(pattern);
    if (key_pos == std::string::npos) {
        return std::nullopt;
    }

    size_t value_pos = key_pos + pattern.size();
    skipSpaces(body, value_pos);
    if (value_pos >= body.size()) {
        return std::nullopt;
    }

    size_t end_pos = value_pos;
    while (end_pos < body.size() && std::isdigit(static_cast<unsigned char>(body[end_pos]))) {
        ++end_pos;
    }
    if (end_pos == value_pos) {
        return std::nullopt;
    }

    try {
        return static_cast<std::uint64_t>(std::stoull(body.substr(value_pos, end_pos - value_pos)));
    } catch (...) {
        return std::nullopt;
    }
}

std::string toLowerCopy(const std::string& input)
{
    std::string out = input;
    for (char& ch : out) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return out;
}

std::string trimCopy(const std::string& input)
{
    size_t begin = 0;
    while (begin < input.size() && std::isspace(static_cast<unsigned char>(input[begin]))) {
        ++begin;
    }

    size_t end = input.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }

    return input.substr(begin, end - begin);
}

std::optional<size_t> parseContentLength(const std::string& headers)
{
    std::istringstream iss(headers);
    std::string line;
    while (std::getline(iss, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        const std::string lower = toLowerCopy(line);
        constexpr const char* kPrefix = "content-length:";
        if (lower.rfind(kPrefix, 0) == 0) {
            const std::string value = trimCopy(line.substr(std::strlen(kPrefix)));
            if (value.empty()) {
                return std::nullopt;
            }
            try {
                return static_cast<size_t>(std::stoull(value));
            } catch (...) {
                return std::nullopt;
            }
        }
    }

    return std::nullopt;
}

std::optional<int> parseStatusCode(const std::string& headers)
{
    const size_t first_line_end = headers.find("\r\n");
    const std::string first_line = headers.substr(0, first_line_end);

    std::istringstream iss(first_line);
    std::string version;
    int code = 0;
    iss >> version >> code;
    if (version.empty() || code <= 0) {
        return std::nullopt;
    }
    return code;
}

std::string extractDbErrorMessage(const std::string& body)
{
    if (const auto message = extractJsonStringField(body, "message"); message.has_value()) {
        return *message;
    }
    return body.empty() ? "db response error" : body;
}

std::string encodePathSegment(const std::string& value)
{
    auto isUnreserved = [](unsigned char c) {
        return std::isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~';
    };

    static const char kHex[] = "0123456789ABCDEF";

    std::string out;
    out.reserve(value.size() * 3);
    for (const unsigned char c : value) {
        if (isUnreserved(c)) {
            out.push_back(static_cast<char>(c));
            continue;
        }
        out.push_back('%');
        out.push_back(kHex[(c >> 4) & 0x0F]);
        out.push_back(kHex[c & 0x0F]);
    }

    return out;
}

std::expected<DbUserRecord, std::string> parseDbUserFromBody(const std::string& body)
{
    if (body.find("\"success\":true") == std::string::npos) {
        return std::unexpected(extractDbErrorMessage(body));
    }

    DbUserRecord user;
    const auto user_id = extractJsonUint64Field(body, "id");
    if (!user_id.has_value()) {
        return std::unexpected("db response missing user id");
    }

    user.m_id = *user_id;
    user.m_username = extractJsonStringField(body, "username").value_or("");
    user.m_email = extractJsonStringField(body, "email").value_or("");
    user.m_display_name = extractJsonStringField(body, "display_name").value_or("");
    user.m_bio = extractJsonStringField(body, "bio").value_or("");
    user.m_website = extractJsonStringField(body, "website").value_or("");
    user.m_github = extractJsonStringField(body, "github").value_or("");
    user.m_password_salt = extractJsonStringField(body, "password_salt").value_or("");
    user.m_password_hash = extractJsonStringField(body, "password_hash").value_or("");
    user.m_email_notifications = extractJsonBoolField(body, "email_notifications").value_or(true);
    user.m_new_post_notifications = extractJsonBoolField(body, "new_post_notifications").value_or(true);
    user.m_comment_reply_notifications =
        extractJsonBoolField(body, "comment_reply_notifications").value_or(true);
    user.m_release_notifications = extractJsonBoolField(body, "release_notifications").value_or(true);

    return user;
}

void appendJsonStringField(std::string& json,
                           bool& first,
                           const std::string& key,
                           const std::optional<std::string>& value)
{
    if (!value.has_value()) {
        return;
    }

    if (!first) {
        json += ",";
    }
    first = false;
    json += "\"" + key + "\":\"" + escapeJson(*value) + "\"";
}

void appendJsonBoolField(std::string& json,
                         bool& first,
                         const std::string& key,
                         const std::optional<bool>& value)
{
    if (!value.has_value()) {
        return;
    }

    if (!first) {
        json += ",";
    }
    first = false;
    json += "\"" + key + "\":" + std::string(*value ? "true" : "false");
}

}  // namespace

DbHttpClient::DbHttpClient()
{
    m_host = getEnvOrDefault("DB_SERVICE_HOST", "127.0.0.1");
    m_port = getPortFromEnv("DB_SERVICE_PORT", 8082);
    m_base_url = "http://" + m_host + ":" + std::to_string(m_port);
}

const std::string& DbHttpClient::baseUrl() const
{
    return m_base_url;
}

std::expected<DbHttpClient::HttpResult, std::string> DbHttpClient::request(
    const std::string& method,
    const std::string& path,
    const std::optional<std::string>& body) const
{
    addrinfo hints {};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* result = nullptr;
    const std::string service = std::to_string(m_port);
    const int gai_ret = getaddrinfo(m_host.c_str(), service.c_str(), &hints, &result);
    if (gai_ret != 0) {
        return std::unexpected("db getaddrinfo failed: " + std::string(gai_strerror(gai_ret)));
    }

    int sock_fd = -1;
    for (addrinfo* rp = result; rp != nullptr; rp = rp->ai_next) {
        sock_fd = ::socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (sock_fd == -1) {
            continue;
        }

        timeval timeout {};
        timeout.tv_sec = 5;
        timeout.tv_usec = 0;
        ::setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        ::setsockopt(sock_fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

        if (::connect(sock_fd, rp->ai_addr, rp->ai_addrlen) == 0) {
            break;
        }

        ::close(sock_fd);
        sock_fd = -1;
    }

    freeaddrinfo(result);

    if (sock_fd == -1) {
        return std::unexpected("db connect failed to " + m_host + ":" + std::to_string(m_port));
    }

    std::string req;
    req += method + " " + path + " HTTP/1.1\r\n";
    req += "Host: " + m_host + ":" + std::to_string(m_port) + "\r\n";
    req += "User-Agent: galay-auth-db-client/1.0\r\n";
    req += "Accept: application/json\r\n";
    req += "Connection: close\r\n";
    if (body.has_value()) {
        req += "Content-Type: application/json\r\n";
        req += "Content-Length: " + std::to_string(body->size()) + "\r\n";
    }
    req += "\r\n";
    if (body.has_value()) {
        req += *body;
    }

    size_t sent = 0;
    while (sent < req.size()) {
        const ssize_t wrote = ::send(sock_fd, req.data() + sent, req.size() - sent, 0);
        if (wrote <= 0) {
            ::close(sock_fd);
            return std::unexpected("db send failed: " + std::string(std::strerror(errno)));
        }
        sent += static_cast<size_t>(wrote);
    }

    std::string raw;
    raw.reserve(4096);

    size_t header_end_pos = std::string::npos;
    std::optional<size_t> content_length;

    char buffer[4096];
    while (true) {
        const ssize_t received = ::recv(sock_fd, buffer, sizeof(buffer), 0);
        if (received == 0) {
            break;
        }
        if (received < 0) {
            if (errno == EWOULDBLOCK || errno == EAGAIN) {
                break;
            }
            ::close(sock_fd);
            return std::unexpected("db recv failed: " + std::string(std::strerror(errno)));
        }

        raw.append(buffer, static_cast<size_t>(received));

        if (header_end_pos == std::string::npos) {
            header_end_pos = raw.find("\r\n\r\n");
            if (header_end_pos != std::string::npos) {
                const std::string headers = raw.substr(0, header_end_pos + 4);
                content_length = parseContentLength(headers);
            }
        }

        if (header_end_pos != std::string::npos && content_length.has_value()) {
            const size_t body_start = header_end_pos + 4;
            if (raw.size() >= body_start + *content_length) {
                break;
            }
        }
    }

    ::close(sock_fd);

    if (header_end_pos == std::string::npos) {
        return std::unexpected("db invalid http response (header incomplete)");
    }

    const std::string headers = raw.substr(0, header_end_pos + 4);
    const auto status_code = parseStatusCode(headers);
    if (!status_code.has_value()) {
        return std::unexpected("db invalid http response status line");
    }

    std::string response_body = raw.substr(header_end_pos + 4);
    if (content_length.has_value() && response_body.size() > *content_length) {
        response_body.resize(*content_length);
    }

    return HttpResult{*status_code, response_body};
}

std::expected<DbUserRecord, std::string> DbHttpClient::createUser(const DbCreateUserInput& input)
{
    std::string payload = "{";
    payload += "\"username\":\"" + escapeJson(input.m_username) + "\",";
    payload += "\"email\":\"" + escapeJson(input.m_email) + "\",";
    payload += "\"display_name\":\"" + escapeJson(input.m_display_name) + "\",";
    payload += "\"bio\":\"" + escapeJson(input.m_bio) + "\",";
    payload += "\"website\":\"" + escapeJson(input.m_website) + "\",";
    payload += "\"github\":\"" + escapeJson(input.m_github) + "\",";
    payload += "\"password_salt\":\"" + escapeJson(input.m_password_salt) + "\",";
    payload += "\"password_hash\":\"" + escapeJson(input.m_password_hash) + "\"";
    payload += "}";

    const auto resp = request("POST", "/api/v1/db/users/create", payload);
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<DbUserRecord, std::string> DbHttpClient::getUserByUsername(const std::string& username)
{
    const auto resp = request("GET", "/api/v1/db/users/get-by-username/" + encodePathSegment(username));
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status == 404) {
        return std::unexpected("user not found");
    }
    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<DbUserRecord, std::string> DbHttpClient::getUserById(std::uint64_t user_id)
{
    const auto resp = request("GET", "/api/v1/db/users/get/" + std::to_string(user_id));
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status == 404) {
        return std::unexpected("user not found");
    }
    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<DbUserRecord, std::string> DbHttpClient::updateUser(std::uint64_t user_id,
                                                                  const DbUpdateUserInput& input)
{
    std::string payload = "{";
    bool first = true;
    appendJsonStringField(payload, first, "email", input.m_email);
    appendJsonStringField(payload, first, "display_name", input.m_display_name);
    appendJsonStringField(payload, first, "bio", input.m_bio);
    appendJsonStringField(payload, first, "website", input.m_website);
    appendJsonStringField(payload, first, "github", input.m_github);
    payload += "}";

    const auto resp = request("PATCH", "/api/v1/db/users/update/" + std::to_string(user_id), payload);
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status == 404) {
        return std::unexpected("user not found");
    }
    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<DbUserRecord, std::string> DbHttpClient::updatePassword(
    std::uint64_t user_id,
    const DbUpdatePasswordInput& input)
{
    std::string payload = "{";
    payload += "\"password_salt\":\"" + escapeJson(input.m_password_salt) + "\",";
    payload += "\"password_hash\":\"" + escapeJson(input.m_password_hash) + "\"";
    payload += "}";

    const auto resp = request(
        "PUT",
        "/api/v1/db/users/update-password/" + std::to_string(user_id),
        payload);
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status == 404) {
        return std::unexpected("user not found");
    }
    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<DbUserRecord, std::string> DbHttpClient::updateNotifications(
    std::uint64_t user_id,
    const DbUpdateNotificationsInput& input)
{
    std::string payload = "{";
    bool first = true;
    appendJsonBoolField(payload, first, "email_notifications", input.m_email_notifications);
    appendJsonBoolField(payload, first, "new_post_notifications", input.m_new_post_notifications);
    appendJsonBoolField(payload, first, "comment_reply_notifications", input.m_comment_reply_notifications);
    appendJsonBoolField(payload, first, "release_notifications", input.m_release_notifications);
    payload += "}";

    const auto resp = request(
        "PUT",
        "/api/v1/db/users/update-notifications/" + std::to_string(user_id),
        payload);
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status == 404) {
        return std::unexpected("user not found");
    }
    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return parseDbUserFromBody(resp->m_body);
}

std::expected<bool, std::string> DbHttpClient::deleteUser(std::uint64_t user_id)
{
    const auto resp = request("DELETE", "/api/v1/db/users/delete/" + std::to_string(user_id));
    if (!resp) {
        return std::unexpected(resp.error());
    }

    if (resp->m_status != 200) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }
    if (resp->m_body.find("\"success\":true") == std::string::npos) {
        return std::unexpected(extractDbErrorMessage(resp->m_body));
    }

    return true;
}
