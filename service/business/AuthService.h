#ifndef BLOG_AUTH_SERVICE_H
#define BLOG_AUTH_SERVICE_H

#include <mutex>
#include <optional>
#include <string>

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

struct AuthProfilePatch {
    std::optional<std::string> m_display_name;
    std::optional<std::string> m_email;
    std::optional<std::string> m_bio;
    std::optional<std::string> m_website;
    std::optional<std::string> m_github;
};

struct NotificationSettingsPatch {
    std::optional<bool> m_email_notifications;
    std::optional<bool> m_new_post_notifications;
    std::optional<bool> m_comment_reply_notifications;
    std::optional<bool> m_release_notifications;
};

enum class PasswordUpdateStatus {
    kSuccess,
    kUnauthorized,
    kOldPasswordIncorrect
};

class AuthService {
public:
    struct LoginResult {
        std::string m_access_token;
        std::string m_refresh_token;
        AuthUser m_user;
    };

    AuthService();

    bool hasValidBearerToken(const std::string& authorization_header) const;

    LoginResult login(const std::string& username, const std::string& password);
    AuthUser registerUser(const std::string& username,
                          const std::string& email,
                          const std::string& password);
    std::optional<std::string> refreshAccessToken(const std::string& refresh_token) const;
    void logout();
    std::optional<AuthUser> getCurrentUser(const std::string& authorization_header) const;
    std::optional<AuthUser> updateProfile(const std::string& authorization_header,
                                          const AuthProfilePatch& patch);
    PasswordUpdateStatus updatePassword(const std::string& authorization_header,
                                        const std::string& old_password,
                                        const std::string& new_password);
    std::optional<NotificationSettings> updateNotifications(const std::string& authorization_header,
                                                            const NotificationSettingsPatch& patch);
    bool deleteAccount(const std::string& authorization_header);

    static std::string userToJson(const AuthUser& user);
    static std::string notificationSettingsToJson(const NotificationSettings& settings);

private:
    static std::string escapeJson(const std::string& str);
    bool hasValidBearerTokenLocked(const std::string& authorization_header) const;

    mutable std::mutex m_mutex;
    AuthUser m_user;
    NotificationSettings m_notification_settings;
    std::string m_access_token;
    std::string m_refresh_token;
};

#endif  // BLOG_AUTH_SERVICE_H
