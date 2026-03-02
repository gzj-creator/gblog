#ifndef AUTH_SERVICE_DB_HTTP_CLIENT_H
#define AUTH_SERVICE_DB_HTTP_CLIENT_H

#include <cstdint>
#include <expected>
#include <optional>
#include <string>

struct DbUserRecord {
    std::uint64_t m_id = 0;
    std::string m_username;
    std::string m_email;
    std::string m_display_name;
    std::string m_bio;
    std::string m_website;
    std::string m_github;
    std::string m_password_salt;
    std::string m_password_hash;
    bool m_email_notifications = true;
    bool m_new_post_notifications = true;
    bool m_comment_reply_notifications = true;
    bool m_release_notifications = true;
};

struct DbCreateUserInput {
    std::string m_username;
    std::string m_email;
    std::string m_display_name;
    std::string m_bio;
    std::string m_website;
    std::string m_github;
    std::string m_password_salt;
    std::string m_password_hash;
};

struct DbUpdateUserInput {
    std::optional<std::string> m_email;
    std::optional<std::string> m_display_name;
    std::optional<std::string> m_bio;
    std::optional<std::string> m_website;
    std::optional<std::string> m_github;
};

struct DbUpdatePasswordInput {
    std::string m_password_salt;
    std::string m_password_hash;
};

struct DbUpdateNotificationsInput {
    std::optional<bool> m_email_notifications;
    std::optional<bool> m_new_post_notifications;
    std::optional<bool> m_comment_reply_notifications;
    std::optional<bool> m_release_notifications;
};

class DbHttpClient {
public:
    DbHttpClient();

    const std::string& baseUrl() const;

    std::expected<DbUserRecord, std::string> createUser(const DbCreateUserInput& input);
    std::expected<DbUserRecord, std::string> getUserByUsername(const std::string& username);
    std::expected<DbUserRecord, std::string> getUserById(std::uint64_t user_id);
    std::expected<DbUserRecord, std::string> updateUser(std::uint64_t user_id,
                                                        const DbUpdateUserInput& input);
    std::expected<DbUserRecord, std::string> updatePassword(std::uint64_t user_id,
                                                            const DbUpdatePasswordInput& input);
    std::expected<DbUserRecord, std::string> updateNotifications(
        std::uint64_t user_id,
        const DbUpdateNotificationsInput& input);
    std::expected<bool, std::string> deleteUser(std::uint64_t user_id);

private:
    struct HttpResult {
        int m_status = 0;
        std::string m_body;
    };

    std::expected<HttpResult, std::string> request(const std::string& method,
                                                   const std::string& path,
                                                   const std::optional<std::string>& body = std::nullopt) const;

    std::string m_host;
    std::uint16_t m_port = 8082;
    std::string m_base_url;
};

#endif  // AUTH_SERVICE_DB_HTTP_CLIENT_H
