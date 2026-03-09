#include "TokenStore.h"

#include <chrono>
#include <galay-utils/algorithm/Salt.hpp>

#include <unordered_map>
#include <unordered_set>

namespace {

std::unordered_map<std::string, AuthSessionInfo> g_access_index;
std::unordered_map<std::string, std::string> g_refresh_to_access;

}  // namespace

AuthSessionInfo TokenStore::createSession(std::uint64_t user_id, const std::string& username)
{
    AuthSessionInfo session;
    session.m_user_id = user_id;
    session.m_username = username;
    session.m_access_token = generateToken();
    session.m_refresh_token = generateToken();

    g_access_index[session.m_access_token] = session;
    g_refresh_to_access[session.m_refresh_token] = session.m_access_token;
    return session;
}

std::optional<AuthSessionInfo> TokenStore::findByAccessToken(const std::string& access_token)
{
    const auto it = g_access_index.find(access_token);
    if (it == g_access_index.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::expected<AuthSessionInfo, std::string> TokenStore::refresh(const std::string& refresh_token)
{
    if (refresh_token.empty()) {
        return std::unexpected("refresh_token required");
    }

    const auto map_it = g_refresh_to_access.find(refresh_token);
    if (map_it == g_refresh_to_access.end()) {
        return std::unexpected("refresh token invalid");
    }

    const auto access_it = g_access_index.find(map_it->second);
    if (access_it == g_access_index.end()) {
        g_refresh_to_access.erase(map_it);
        return std::unexpected("refresh token invalid");
    }

    AuthSessionInfo next = access_it->second;
    g_access_index.erase(access_it);

    next.m_access_token = generateToken();
    g_access_index[next.m_access_token] = next;
    map_it->second = next.m_access_token;
    return next;
}

bool TokenStore::revokeByAccessToken(const std::string& access_token)
{
    if (access_token.empty()) {
        return false;
    }

    const auto it = g_access_index.find(access_token);
    if (it == g_access_index.end()) {
        return false;
    }

    g_refresh_to_access.erase(it->second.m_refresh_token);
    g_access_index.erase(it);
    return true;
}

void TokenStore::revokeByUserId(std::uint64_t user_id)
{
    std::unordered_set<std::string> revoked_refresh_tokens;
    for (auto it = g_access_index.begin(); it != g_access_index.end();) {
        if (it->second.m_user_id == user_id) {
            revoked_refresh_tokens.insert(it->second.m_refresh_token);
            it = g_access_index.erase(it);
            continue;
        }
        ++it;
    }

    for (const auto& refresh_token : revoked_refresh_tokens) {
        g_refresh_to_access.erase(refresh_token);
    }
}

std::string TokenStore::generateToken() const
{
    return galay::utils::SaltGenerator::generateSecureBase64(24);
}
