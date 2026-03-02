#ifndef AUTH_SERVICE_TOKEN_STORE_H
#define AUTH_SERVICE_TOKEN_STORE_H

#include <cstdint>
#include <expected>
#include <optional>
#include <string>

struct AuthSessionInfo {
    std::uint64_t m_user_id = 0;
    std::string m_username;
    std::string m_access_token;
    std::string m_refresh_token;
};

class TokenStore {
public:
    AuthSessionInfo createSession(std::uint64_t user_id, const std::string& username);
    std::optional<AuthSessionInfo> findByAccessToken(const std::string& access_token);
    std::expected<AuthSessionInfo, std::string> refresh(const std::string& refresh_token);
    bool revokeByAccessToken(const std::string& access_token);
    void revokeByUserId(std::uint64_t user_id);

private:
    std::string generateToken() const;
};

#endif  // AUTH_SERVICE_TOKEN_STORE_H
