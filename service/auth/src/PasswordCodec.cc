#include "PasswordCodec.h"

#include <galay-utils/algorithm/Base64.hpp>
#include <galay-utils/algorithm/Salt.hpp>

#include <openssl/sha.h>

#include <cctype>
#include <iomanip>
#include <sstream>

namespace {

std::string sha256Hex(const std::string& input)
{
    unsigned char digest[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(input.data()), input.size(), digest);

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (unsigned char byte : digest) {
        oss << std::setw(2) << static_cast<int>(byte);
    }
    return oss.str();
}

}  // namespace

std::expected<std::string, std::string> PasswordCodec::decodeBase64Password(const std::string& password_b64)
{
    if (password_b64.empty()) {
        return std::unexpected("password_b64 required");
    }

    // Basic shape guard before decode.
    for (const char ch : password_b64) {
        if (std::isalnum(static_cast<unsigned char>(ch)) || ch == '+' || ch == '/' || ch == '=') {
            continue;
        }
        return std::unexpected("password_b64 invalid");
    }

    const std::string decoded = galay::utils::Base64Util::Base64Decode(password_b64);
    if (decoded.empty()) {
        return std::unexpected("password_b64 decode failed");
    }

    return decoded;
}

PasswordHashResult PasswordCodec::hashWithNewSalt(const std::string& plain_password)
{
    PasswordHashResult out;
    out.m_salt = galay::utils::SaltGenerator::generateSecureBase64(16);
    out.m_hash = hashWithSalt(plain_password, out.m_salt);
    return out;
}

std::string PasswordCodec::hashWithSalt(const std::string& plain_password, const std::string& salt)
{
    return sha256Hex(salt + plain_password);
}

bool PasswordCodec::verify(const std::string& plain_password,
                           const std::string& salt,
                           const std::string& expected_hash)
{
    if (salt.empty() || expected_hash.empty()) {
        return false;
    }
    return hashWithSalt(plain_password, salt) == expected_hash;
}
