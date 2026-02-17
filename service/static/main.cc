#include "galay-http/utils/HttpLogger.h"
#include <galay-http/kernel/http/HttpServer.h>
#include <galay-http/kernel/http/HttpRouter.h>
#include <chrono>
#include <cstdlib>
#include <string>
#include <thread>

using namespace galay::http;

static std::string getEnvOrDefault(const char* key, const std::string& fallback) {
    const char* value = std::getenv(key);
    if (value == nullptr || *value == '\0') {
        return fallback;
    }
    return value;
}

static uint16_t getPortFromEnv(const char* key, uint16_t fallback) {
    const char* value = std::getenv(key);
    if (value == nullptr || *value == '\0') {
        return fallback;
    }

    try {
        const int port = std::stoi(value);
        if (port <= 0 || port > 65535) {
            return fallback;
        }
        return static_cast<uint16_t>(port);
    } catch (...) {
        return fallback;
    }
}

int main()
{
    HttpLogger::console();

    const std::string host = getEnvOrDefault("STATIC_HOST", "0.0.0.0");
    const uint16_t port = getPortFromEnv("STATIC_PORT", 8080);
    const std::string frontendRoot = getEnvOrDefault("STATIC_FRONTEND_ROOT", "./frontend");
    const std::string apiUpstreamHost = getEnvOrDefault("API_PROXY_UPSTREAM_HOST", "127.0.0.1");
    const uint16_t apiUpstreamPort = getPortFromEnv("API_PROXY_UPSTREAM_PORT", 8081);

    HttpServerConfig config;
    config.host = host;
    config.port = port;

    HttpServer server(config);
    HttpRouter router;

    // /api/xxx -> upstream /xxx（Raw proxy 模式）
    router.proxy("/api", apiUpstreamHost, apiUpstreamPort, ProxyMode::Raw);

    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setEnableETag(false);  // 开发模式：禁用 ETag 条件缓存
    router.mount("/", frontendRoot, staticConfig);

    server.start(std::move(router));

    while (server.isRunning()) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}
