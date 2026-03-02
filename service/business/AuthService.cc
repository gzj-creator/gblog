#include "AuthService.h"

#include <string_view>

namespace {
constexpr std::string_view kBearerPrefix = "Bearer ";
}

AuthService::AuthService()
    : m_access_token("galay-access-token"), m_refresh_token("galay-refresh-token")
{
}

std::string AuthService::escapeJson(const std::string& str)
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

std::string AuthService::userToJson(const AuthUser& user)
{
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

std::string AuthService::notificationSettingsToJson(const NotificationSettings& settings)
{
    std::string json = "{";
    json += "\"email_notifications\":" + std::string(settings.m_email_notifications ? "true" : "false") + ",";
    json += "\"new_post_notifications\":" + std::string(settings.m_new_post_notifications ? "true" : "false") + ",";
    json += "\"comment_reply_notifications\":" + std::string(settings.m_comment_reply_notifications ? "true" : "false") + ",";
    json += "\"release_notifications\":" + std::string(settings.m_release_notifications ? "true" : "false");
    json += "}";
    return json;
}

bool AuthService::hasValidBearerTokenLocked(const std::string& authorization_header) const
{
    if (authorization_header.rfind(kBearerPrefix, 0) != 0) {
        return false;
    }

    const std::string token = authorization_header.substr(kBearerPrefix.size());
    return !m_access_token.empty() && token == m_access_token;
}

bool AuthService::hasValidBearerToken(const std::string& authorization_header) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return hasValidBearerTokenLocked(authorization_header);
}

AuthService::LoginResult AuthService::login(const std::string& username, const std::string& password)
{
    std::lock_guard<std::mutex> lock(m_mutex);

    if (!username.empty()) {
        m_user.m_username = username;
        if (m_user.m_display_name.empty()) {
            m_user.m_display_name = username;
        }
    }

    if (!password.empty()) {
        m_user.m_password = password;
    }

    return LoginResult{m_access_token, m_refresh_token, m_user};
}

AuthUser AuthService::registerUser(const std::string& username,
                                   const std::string& email,
                                   const std::string& password)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_user.m_username = username;
    m_user.m_display_name = username;
    m_user.m_email = email;
    m_user.m_password = password;
    return m_user;
}

std::optional<std::string> AuthService::refreshAccessToken(const std::string& refresh_token) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (refresh_token.empty() || refresh_token != m_refresh_token) {
        return std::nullopt;
    }
    return m_access_token;
}

void AuthService::logout()
{
    // Keep existing behavior: logout is idempotent and does not revoke tokens.
}

std::optional<AuthUser> AuthService::getCurrentUser(const std::string& authorization_header) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (!hasValidBearerTokenLocked(authorization_header)) {
        return std::nullopt;
    }
    return m_user;
}

std::optional<AuthUser> AuthService::updateProfile(const std::string& authorization_header,
                                                   const AuthProfilePatch& patch)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (!hasValidBearerTokenLocked(authorization_header)) {
        return std::nullopt;
    }

    if (patch.m_display_name.has_value()) m_user.m_display_name = *patch.m_display_name;
    if (patch.m_email.has_value()) m_user.m_email = *patch.m_email;
    if (patch.m_bio.has_value()) m_user.m_bio = *patch.m_bio;
    if (patch.m_website.has_value()) m_user.m_website = *patch.m_website;
    if (patch.m_github.has_value()) m_user.m_github = *patch.m_github;

    return m_user;
}

PasswordUpdateStatus AuthService::updatePassword(const std::string& authorization_header,
                                                 const std::string& old_password,
                                                 const std::string& new_password)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (!hasValidBearerTokenLocked(authorization_header)) {
        return PasswordUpdateStatus::kUnauthorized;
    }

    const bool old_password_valid = old_password.empty() || old_password == m_user.m_password;
    if (!old_password_valid) {
        return PasswordUpdateStatus::kOldPasswordIncorrect;
    }

    if (!new_password.empty()) {
        m_user.m_password = new_password;
    }

    return PasswordUpdateStatus::kSuccess;
}

std::optional<NotificationSettings> AuthService::updateNotifications(
    const std::string& authorization_header,
    const NotificationSettingsPatch& patch)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (!hasValidBearerTokenLocked(authorization_header)) {
        return std::nullopt;
    }

    if (patch.m_email_notifications.has_value()) {
        m_notification_settings.m_email_notifications = *patch.m_email_notifications;
    }
    if (patch.m_new_post_notifications.has_value()) {
        m_notification_settings.m_new_post_notifications = *patch.m_new_post_notifications;
    }
    if (patch.m_comment_reply_notifications.has_value()) {
        m_notification_settings.m_comment_reply_notifications = *patch.m_comment_reply_notifications;
    }
    if (patch.m_release_notifications.has_value()) {
        m_notification_settings.m_release_notifications = *patch.m_release_notifications;
    }

    return m_notification_settings;
}

bool AuthService::deleteAccount(const std::string& authorization_header)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    if (!hasValidBearerTokenLocked(authorization_header)) {
        return false;
    }

    m_access_token.clear();
    m_refresh_token.clear();
    return true;
}
