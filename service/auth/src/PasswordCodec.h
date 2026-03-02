#ifndef AUTH_SERVICE_PASSWORD_CODEC_H
#define AUTH_SERVICE_PASSWORD_CODEC_H

#include <expected>
#include <string>

struct PasswordHashResult {
    std::string m_salt;
    std::string m_hash;
};

class PasswordCodec {
public:
    static std::expected<std::string, std::string> decodeBase64Password(const std::string& password_b64);
    static PasswordHashResult hashWithNewSalt(const std::string& plain_password);
    static std::string hashWithSalt(const std::string& plain_password, const std::string& salt);
    static bool verify(const std::string& plain_password,
                       const std::string& salt,
                       const std::string& expected_hash);
};

#endif  // AUTH_SERVICE_PASSWORD_CODEC_H
