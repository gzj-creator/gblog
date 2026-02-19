#include "StaticServerConfig.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace static_server {
namespace {

constexpr const char* kDefaultConfigPath = "/app/config/static-server.conf";

struct IndexedRouteFields {
    std::optional<std::string> prefix;
    std::optional<std::string> upstreamHost;
    std::optional<std::uint16_t> upstreamPort;
    std::optional<galay::http::ProxyMode> mode;
};

std::string trimCopy(const std::string_view input)
{
    size_t begin = 0;
    while (begin < input.size() && std::isspace(static_cast<unsigned char>(input[begin]))) {
        ++begin;
    }

    size_t end = input.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }
    return std::string(input.substr(begin, end - begin));
}

std::string toLowerCopy(const std::string_view input)
{
    std::string out(input);
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return out;
}

bool startsWith(const std::string_view value, const std::string_view prefix)
{
    return value.size() >= prefix.size() && value.compare(0, prefix.size(), prefix) == 0;
}

std::vector<std::string> split(const std::string_view value, const char delimiter)
{
    std::vector<std::string> fields;
    size_t start = 0;
    while (start <= value.size()) {
        const size_t pos = value.find(delimiter, start);
        if (pos == std::string_view::npos) {
            fields.emplace_back(trimCopy(value.substr(start)));
            break;
        }
        fields.emplace_back(trimCopy(value.substr(start, pos - start)));
        start = pos + 1;
    }
    return fields;
}

std::optional<std::string> getEnvString(const char* key)
{
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return std::nullopt;
    }

    std::string value = trimCopy(raw);
    if (value.empty()) {
        return std::nullopt;
    }
    return value;
}

std::optional<std::uint16_t> parsePort(const std::string_view raw)
{
    const std::string value = trimCopy(raw);
    if (value.empty()) {
        return std::nullopt;
    }

    char* end = nullptr;
    const unsigned long parsed = std::strtoul(value.c_str(), &end, 10);
    if (end == value.c_str() || *end != '\0') {
        return std::nullopt;
    }
    if (parsed == 0 || parsed > std::numeric_limits<std::uint16_t>::max()) {
        return std::nullopt;
    }
    return static_cast<std::uint16_t>(parsed);
}

bool parseBool(const std::string_view raw, const bool fallback)
{
    const std::string value = toLowerCopy(trimCopy(raw));
    if (value == "1" || value == "true" || value == "yes" || value == "on") {
        return true;
    }
    if (value == "0" || value == "false" || value == "no" || value == "off") {
        return false;
    }
    return fallback;
}

void normalizeRoutePrefix(std::string& routePrefix)
{
    if (routePrefix.empty()) {
        routePrefix = "/";
        return;
    }
    if (routePrefix.front() != '/') {
        routePrefix.insert(routePrefix.begin(), '/');
    }
    while (routePrefix.size() > 1 && routePrefix.back() == '/') {
        routePrefix.pop_back();
    }
}

galay::http::ProxyMode parseProxyMode(const std::string_view raw,
                                      const galay::http::ProxyMode fallback = galay::http::ProxyMode::Http)
{
    const std::string value = toLowerCopy(trimCopy(raw));
    if (value == "raw") {
        return galay::http::ProxyMode::Raw;
    }
    if (value == "http" || value.empty()) {
        return galay::http::ProxyMode::Http;
    }
    return fallback;
}

std::optional<ProxyRouteConfig> parseRouteSpec(const std::string_view raw)
{
    const auto fields = split(raw, ',');
    if (fields.size() < 3) {
        return std::nullopt;
    }

    ProxyRouteConfig route;
    route.routePrefix = fields[0];
    route.upstreamHost = fields[1];

    const auto parsedPort = parsePort(fields[2]);
    if (!parsedPort.has_value()) {
        return std::nullopt;
    }
    route.upstreamPort = *parsedPort;

    if (fields.size() >= 4) {
        route.mode = parseProxyMode(fields[3], galay::http::ProxyMode::Http);
    }

    if (route.upstreamHost.empty()) {
        route.upstreamHost = "127.0.0.1";
    }
    normalizeRoutePrefix(route.routePrefix);
    return route;
}

std::vector<std::pair<std::string, std::string>> loadConfigEntries(const std::string& configPath,
                                                                    bool& loaded)
{
    std::ifstream input(configPath);
    if (!input.is_open()) {
        loaded = false;
        return {};
    }

    loaded = true;
    std::vector<std::pair<std::string, std::string>> entries;
    std::string line;

    while (std::getline(input, line)) {
        const std::string trimmed = trimCopy(line);
        if (trimmed.empty() || trimmed.front() == '#') {
            continue;
        }

        const size_t equalPos = trimmed.find('=');
        if (equalPos == std::string::npos) {
            continue;
        }

        std::string key = trimCopy(std::string_view(trimmed).substr(0, equalPos));
        std::string value = trimCopy(std::string_view(trimmed).substr(equalPos + 1));
        if (!key.empty()) {
            entries.emplace_back(std::move(key), std::move(value));
        }
    }
    return entries;
}

void applyFileConfig(AppConfig& config, const std::vector<std::pair<std::string, std::string>>& entries)
{
    std::vector<ProxyRouteConfig> routeList;
    std::unordered_map<std::string, IndexedRouteFields> indexedRouteFields;

    for (const auto& [key, value] : entries) {
        if (key == "server.host") {
            if (!value.empty()) {
                config.host = value;
            }
            continue;
        }

        if (key == "server.port") {
            if (const auto parsed = parsePort(value); parsed.has_value()) {
                config.port = *parsed;
            }
            continue;
        }

        if (key == "static.frontend_root") {
            if (!value.empty()) {
                config.frontendRoot = value;
            }
            continue;
        }

        if (key == "log.dir") {
            if (!value.empty()) {
                config.logDir = value;
            }
            continue;
        }

        if (key == "log.file") {
            if (!value.empty()) {
                config.logFile = value;
            }
            continue;
        }

        if (key == "proxy.enabled") {
            config.proxyEnabled = parseBool(value, config.proxyEnabled);
            continue;
        }

        if (key == "proxy.route") {
            if (const auto route = parseRouteSpec(value); route.has_value()) {
                routeList.push_back(*route);
            }
            continue;
        }

        constexpr std::string_view indexedPrefix = "proxy.route.";
        if (!startsWith(key, indexedPrefix)) {
            continue;
        }

        const std::string tail = key.substr(indexedPrefix.size());
        const size_t dotPos = tail.find('.');
        if (dotPos == std::string::npos || dotPos == 0 || dotPos + 1 >= tail.size()) {
            continue;
        }

        const std::string routeId = tail.substr(0, dotPos);
        const std::string field = tail.substr(dotPos + 1);
        IndexedRouteFields& current = indexedRouteFields[routeId];

        if (field == "prefix") {
            if (!value.empty()) {
                current.prefix = value;
            }
            continue;
        }
        if (field == "upstream_host") {
            if (!value.empty()) {
                current.upstreamHost = value;
            }
            continue;
        }
        if (field == "upstream_port") {
            if (const auto parsed = parsePort(value); parsed.has_value()) {
                current.upstreamPort = *parsed;
            }
            continue;
        }
        if (field == "mode") {
            current.mode = parseProxyMode(value, galay::http::ProxyMode::Http);
            continue;
        }
    }

    if (!indexedRouteFields.empty()) {
        std::vector<std::string> ids;
        ids.reserve(indexedRouteFields.size());
        for (const auto& [id, _] : indexedRouteFields) {
            ids.push_back(id);
        }
        std::sort(ids.begin(), ids.end());

        for (const auto& id : ids) {
            const IndexedRouteFields& fields = indexedRouteFields.at(id);
            ProxyRouteConfig route;
            if (fields.prefix.has_value()) {
                route.routePrefix = *fields.prefix;
            }
            if (fields.upstreamHost.has_value()) {
                route.upstreamHost = *fields.upstreamHost;
            }
            if (fields.upstreamPort.has_value()) {
                route.upstreamPort = *fields.upstreamPort;
            }
            if (fields.mode.has_value()) {
                route.mode = *fields.mode;
            }
            normalizeRoutePrefix(route.routePrefix);
            routeList.push_back(std::move(route));
        }
    }

    if (!routeList.empty()) {
        config.proxyRoutes = std::move(routeList);
    }
}

std::vector<ProxyRouteConfig> parseRouteListEnv(const std::string_view raw)
{
    std::vector<ProxyRouteConfig> routes;
    const auto specs = split(raw, ';');
    routes.reserve(specs.size());

    for (const auto& spec : specs) {
        if (spec.empty()) {
            continue;
        }
        const auto route = parseRouteSpec(spec);
        if (route.has_value()) {
            routes.push_back(*route);
        }
    }
    return routes;
}

void applyEnvOverrides(AppConfig& config)
{
    if (const auto value = getEnvString("STATIC_HOST"); value.has_value()) {
        config.host = *value;
    }

    if (const auto value = getEnvString("STATIC_PORT"); value.has_value()) {
        if (const auto parsed = parsePort(*value); parsed.has_value()) {
            config.port = *parsed;
        }
    }

    if (const auto value = getEnvString("STATIC_FRONTEND_ROOT"); value.has_value()) {
        config.frontendRoot = *value;
    }

    if (const auto value = getEnvString("STATIC_LOG_DIR"); value.has_value()) {
        config.logDir = *value;
    }

    if (const auto value = getEnvString("STATIC_LOG_FILE"); value.has_value()) {
        config.logFile = *value;
    }

    if (const auto value = getEnvString("API_PROXY_ENABLED"); value.has_value()) {
        config.proxyEnabled = parseBool(*value, config.proxyEnabled);
    }

    if (const auto value = getEnvString("API_PROXY_ROUTES"); value.has_value()) {
        const auto routes = parseRouteListEnv(*value);
        if (!routes.empty()) {
            config.proxyRoutes = routes;
        }
        return;
    }

    const auto prefix = getEnvString("API_PROXY_ROUTE_PREFIX");
    const auto host = getEnvString("API_PROXY_UPSTREAM_HOST");
    const auto port = getEnvString("API_PROXY_UPSTREAM_PORT");
    const auto mode = getEnvString("API_PROXY_MODE");

    if (!prefix.has_value() && !host.has_value() && !port.has_value() && !mode.has_value()) {
        return;
    }

    ProxyRouteConfig route;
    if (!config.proxyRoutes.empty()) {
        route = config.proxyRoutes.front();
    }
    if (prefix.has_value()) {
        route.routePrefix = *prefix;
    }
    if (host.has_value()) {
        route.upstreamHost = *host;
    }
    if (port.has_value()) {
        if (const auto parsed = parsePort(*port); parsed.has_value()) {
            route.upstreamPort = *parsed;
        }
    }
    if (mode.has_value()) {
        route.mode = parseProxyMode(*mode, route.mode);
    }
    normalizeRoutePrefix(route.routePrefix);

    config.proxyRoutes.clear();
    config.proxyRoutes.push_back(std::move(route));
}

}  // namespace

LoadedAppConfig loadAppConfig()
{
    LoadedAppConfig loaded;
    loaded.configPath = getEnvString("STATIC_CONFIG_PATH").value_or(kDefaultConfigPath);

    const auto entries = loadConfigEntries(loaded.configPath, loaded.fileConfigLoaded);
    if (loaded.fileConfigLoaded) {
        applyFileConfig(loaded.config, entries);
    }
    applyEnvOverrides(loaded.config);
    return loaded;
}

}  // namespace static_server
