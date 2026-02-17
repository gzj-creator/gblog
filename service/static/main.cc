#include "galay-http/utils/HttpLogger.h"
#include <galay-http/kernel/http/HttpServer.h>
#include <galay-http/kernel/http/HttpRouter.h>
#include <galay-http/utils/Http1_1ResponseBuilder.h>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <thread>

using namespace galay::http;


namespace fs = std::filesystem;

static bool readFileToString(const fs::path& path, std::string& out) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        return false;
    }
    out.assign((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return true;
}

static void addNoCacheHeaders(Http1_1ResponseBuilder& builder) {
    builder
        .header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        .header("Pragma", "no-cache")
        .header("Expires", "0");
}

static Coroutine sendResponse(HttpConn& conn, HttpResponse response) {
    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
    co_return;
}

static Coroutine sendJson(HttpConn& conn, HttpStatusCode status, const std::string& body) {
    auto builder = Http1_1ResponseBuilder()
        .status(status)
        .header("Server", "Galay-Static/1.0")
        .header("Access-Control-Allow-Origin", "*")
        .json(body);
    addNoCacheHeaders(builder);

    auto response = builder.buildMove();
    co_await sendResponse(conn, std::move(response)).wait();
    co_return;
}

static Coroutine sendJsonFile(HttpConn& conn, const fs::path& path) {
    std::string body;
    if (!readFileToString(path, body)) {
        co_await sendJson(conn, HttpStatusCode::NotFound_404, R"({"error":"Not Found"})").wait();
        co_return;
    }
    co_await sendJson(conn, HttpStatusCode::OK_200, body).wait();
    co_return;
}

static std::string extractIdFromUri(const std::string& uri) {
    size_t lastSlash = uri.rfind('/');
    if (lastSlash == std::string::npos || lastSlash + 1 >= uri.size()) {
        return {};
    }
    std::string id = uri.substr(lastSlash + 1);
    size_t queryPos = id.find('?');
    if (queryPos != std::string::npos) {
        id = id.substr(0, queryPos);
    }
    return id;
}

int main()
{
    HttpServer server;
    HttpLogger::console();
    HttpRouter router;
    const fs::path dataRoot = "./frontend/data";

    router.addHandler<HttpMethod::GET>("/api/projects",
        [dataRoot](HttpConn& conn, HttpRequest req) -> Coroutine {
            (void)req;
            co_await sendJsonFile(conn, dataRoot / "projects.json").wait();
            co_return;
        });

    router.addHandler<HttpMethod::GET>("/api/posts",
        [dataRoot](HttpConn& conn, HttpRequest req) -> Coroutine {
            (void)req;
            co_await sendJsonFile(conn, dataRoot / "posts.json").wait();
            co_return;
        });

    router.addHandler<HttpMethod::GET>("/api/posts/:id",
        [dataRoot](HttpConn& conn, HttpRequest req) -> Coroutine {
            std::string postId = extractIdFromUri(req.header().uri());
            if (postId.empty()) {
                co_await sendJson(conn, HttpStatusCode::BadRequest_400, R"({"error":"Invalid id"})").wait();
                co_return;
            }
            co_await sendJsonFile(conn, dataRoot / "posts" / (postId + ".json")).wait();
            co_return;
        });

    StaticFileConfig staticConfig;
    staticConfig.setTransferMode(FileTransferMode::AUTO);
    staticConfig.setEnableETag(false);  // 开发模式：禁用 ETag 条件缓存
    router.mount("/", "./frontend", staticConfig);

    server.start(std::move(router));

    while(true) {
        std::this_thread::sleep_for(std::chrono::seconds(100));
    }

    return 0;
}
