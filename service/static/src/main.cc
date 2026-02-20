#include "StaticServerConfig.h"
#include <galay-http/kernel/http/HttpLog.h>
#include <galay-http/kernel/http/HttpServer.h>
#include <galay-http/kernel/http/HttpRouter.h>
#include <chrono>
#include <filesystem>
#include <thread>
#include <spdlog/spdlog.h>
#include "galay-http/utils/HttpLogger.h"

using namespace galay::http;

int main()
{
    const static_server::LoadedAppConfig loaded = static_server::loadAppConfig();
    const static_server::AppConfig& appConfig = loaded.config;

    const std::filesystem::path logPath = std::filesystem::path(appConfig.logDir) / appConfig.logFile;

    try {
        const auto parent = logPath.parent_path();
        if (!parent.empty()) {
            std::filesystem::create_directories(parent);
        }
        HttpLogger::file(logPath.string());
        if (auto logger = HttpLogger::getInstance()->getSpdlogger(); logger) {
            // File sink uses async logger; force flush on info to make tail -f timely.
            logger->flush_on(spdlog::level::info);
        }
    } catch (...) {
        HttpLogger::console();
    }

#if defined(USE_EPOLL)
    constexpr const char* kKernelBackend = "epoll";
#elif defined(USE_IOURING)
    constexpr const char* kKernelBackend = "io_uring";
#elif defined(USE_KQUEUE)
    constexpr const char* kKernelBackend = "kqueue";
#else
    constexpr const char* kKernelBackend = "unknown";
#endif
    HTTP_LOG_INFO("[build] [kernel-backend] [{}]", kKernelBackend);
    HTTP_LOG_INFO("[config] [path] [{}] [{}]", loaded.configPath, loaded.fileConfigLoaded ? "loaded" : "default-or-env");
    HTTP_LOG_INFO("[log] [path] [{}]", logPath.string());

    HttpServerConfig config;
    config.host = appConfig.host;
    config.port = appConfig.port;

    HttpServer server(config);
    HttpRouter router;

    if (appConfig.proxyEnabled) {
        if (appConfig.proxyRoutes.empty()) {
            HTTP_LOG_WARN("[proxy] [config] [enabled] [routes=0] [skip]");
        } else {
            for (const auto& route : appConfig.proxyRoutes) {
                router.proxy(route.routePrefix, route.upstreamHost, route.upstreamPort, route.mode);
                HTTP_LOG_INFO("[proxy] [config] [enabled] [prefix={}] [upstream={}:{}] [mode={}]",
                              route.routePrefix,
                              route.upstreamHost,
                              route.upstreamPort,
                              route.mode == ProxyMode::Raw ? "raw" : "http");
            }
        }
    } else {
        HTTP_LOG_INFO("[proxy] [config] [disabled]");
    }

    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setEnableETag(false);  // 开发模式：禁用 ETag 条件缓存
    router.mount("/", appConfig.frontendRoot, staticConfig);

    server.start(std::move(router));

    while (server.isRunning()) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}
