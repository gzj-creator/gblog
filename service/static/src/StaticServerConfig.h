#ifndef STATIC_SERVER_CONFIG_H
#define STATIC_SERVER_CONFIG_H

#include <cstdint>
#include <string>
#include <vector>

#include <galay-http/kernel/http/HttpRouter.h>

namespace static_server {

struct ProxyRouteConfig {
    std::string routePrefix = "/api";
    std::string upstreamHost = "127.0.0.1";
    std::uint16_t upstreamPort = 8080;
    galay::http::ProxyMode mode = galay::http::ProxyMode::Http;
};

struct AppConfig {
    std::string host = "0.0.0.0";
    std::uint16_t port = 80;
    std::string frontendRoot = "/app/frontend";
    std::string logDir = "/app/logs";
    std::string logFile = "static-server.log";
    bool proxyEnabled = true;
    std::vector<ProxyRouteConfig> proxyRoutes = {ProxyRouteConfig{}};
};

struct LoadedAppConfig {
    AppConfig config;
    std::string configPath;
    bool fileConfigLoaded = false;
};

LoadedAppConfig loadAppConfig();

}  // namespace static_server

#endif  // STATIC_SERVER_CONFIG_H
