/* ============================================
   PROJECTS PAGE - JavaScript
   ============================================ */

// API 基础路径（可选：后端有项目数据时启用）
const API_BASE = '/api';

// 模块化项目描述向量（vector）
const PROJECTS_VECTOR = [
    {
        id: 'kernel',
        name: 'galay-kernel',
        icon: '⚡',
        tagline: '协程调度与异步 IO 运行时内核',
        indexDescription: '调度器 / IO 后端 / 高并发基础',
        summary: '提供协程调度与跨平台异步 IO 能力，作为 Galay 全栈组件的运行时底座。',
        badges: ['C++23', 'MIT', 'Core'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-kernel',
            docs: 'docs/galay-kernel.html'
        },
        stats: {
            '平台': 'macOS / Linux',
            '后端': 'kqueue / epoll / io_uring',
            '方向': 'Runtime / Async IO'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-kernel 是 Galay 体系的运行时内核，负责协程调度、事件循环与异步 IO 抽象。',
                    '它聚焦高并发网络与文件 IO 的执行层能力，不直接提供上层协议语义。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/kernel-performance.json'
            },
            {
                type: 'code',
                title: '示例',
                defaultVariant: 'include',
                variants: [
                    {
                        id: 'include',
                        label: 'Include',
                        filename: 'echo_server.cpp',
                        code: `#include "galay-kernel/kernel/Coroutine.h"
#include "galay-kernel/kernel/ComputeScheduler.h"

using namespace galay::kernel;

Coroutine simpleTask(int id) {
    (void)id;
    co_return;
}

int main() {
    ComputeScheduler scheduler;
    scheduler.start();
    scheduler.spawn(simpleTask(1));
    scheduler.stop();
    return 0;
}`
                    },
                    {
                        id: 'module',
                        label: 'Module',
                        filename: 'echo_server.module.cpp',
                        code: `import galay.kernel;

using namespace galay::kernel;

Coroutine simpleTask(int id) {
    (void)id;
    co_return;
}

int main() {
    ComputeScheduler scheduler;
    scheduler.start();
    scheduler.spawn(simpleTask(1));
    scheduler.stop();
    return 0;
}`
                    }
                ]
            }
        ]
    },
    {
        id: 'ssl',
        name: 'galay-ssl',
        icon: '🔒',
        tagline: '协程友好的 TLS 传输层',
        indexDescription: '握手 / 证书验证 / SNI',
        summary: '提供异步 TLS 握手与加密收发能力，作为 HTTPS 与加密 RPC 的安全传输层。',
        badges: ['C++23', 'OpenSSL', 'TLS'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-ssl',
            docs: 'docs/galay-ssl.html'
        },
        stats: {
            'TLS': '1.2 / 1.3',
            '后端': 'epoll / io_uring',
            '模式': 'Client / Server'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-ssl 在 kernel 之上提供异步 TLS 封装，统一握手、加密收发与证书校验流程。',
                    '它定位为安全传输层组件，主要解决链路加密，不承担业务协议路由与应用逻辑。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/ssl-performance.json'
            },
            {
                type: 'code',
                title: '示例',
                defaultVariant: 'include',
                variants: [
                    {
                        id: 'include',
                        label: 'Include',
                        filename: 'ssl_server.cpp',
                        code: `#include "galay-ssl/async/SslSocket.h"
#include "galay-ssl/ssl/SslContext.h"
#include <galay-kernel/kernel/Coroutine.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <string>
#include <thread>

#ifdef USE_KQUEUE
#include <galay-kernel/kernel/KqueueScheduler.h>
using IOSchedulerType = galay::kernel::KqueueScheduler;
#elif defined(USE_EPOLL)
#include <galay-kernel/kernel/EpollScheduler.h>
using IOSchedulerType = galay::kernel::EpollScheduler;
#elif defined(USE_IOURING)
#include <galay-kernel/kernel/IOUringScheduler.h>
using IOSchedulerType = galay::kernel::IOUringScheduler;
#endif

using namespace galay::ssl;
using namespace galay::kernel;

std::atomic<bool> g_running{true};

void signalHandler(int) {
    g_running = false;
}

Coroutine handleClient(SslContext* ctx, GHandle handle) {
    SslSocket client(ctx, handle);
    client.option().handleNonBlock();

    while (!client.isHandshakeCompleted()) {
        auto hs = co_await client.handshake();
        if (!hs) {
            co_await client.close();
            co_return;
        }
    }

    char buffer[4096];
    auto recvResult = co_await client.recv(buffer, sizeof(buffer));
    if (recvResult && recvResult.value().size() > 0) {
        auto& bytes = recvResult.value();
        co_await client.send(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    }

    co_await client.shutdown();
    co_await client.close();
}

Coroutine sslEchoServer(IOSchedulerType* scheduler, SslContext* ctx, uint16_t port) {
    SslSocket listener(ctx);
    listener.option().handleReuseAddr();
    listener.option().handleNonBlock();

    if (!listener.bind(Host(IPType::IPV4, "0.0.0.0", port))) {
        co_return;
    }
    if (!listener.listen(128)) {
        co_return;
    }

    while (g_running) {
        Host clientHost;
        auto accepted = co_await listener.accept(&clientHost);
        if (!accepted) {
            continue;
        }
        scheduler->spawn(handleClient(ctx, accepted.value()));
    }

    co_await listener.close();
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        return 1;
    }

    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGPIPE, SIG_IGN);

    uint16_t port = static_cast<uint16_t>(std::stoi(argv[1]));
    SslContext ctx(SslMethod::TLS_Server);
    if (!ctx.isValid()) {
        return 1;
    }
    if (!ctx.loadCertificate(argv[2])) {
        return 1;
    }
    if (!ctx.loadPrivateKey(argv[3])) {
        return 1;
    }

    IOSchedulerType scheduler;
    scheduler.start();
    scheduler.spawn(sslEchoServer(&scheduler, &ctx, port));

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    scheduler.stop();
    return 0;
}`
                    },
                    {
                        id: 'module',
                        label: 'Module',
                        filename: 'ssl_server.module.cpp',
                        code: `import galay.ssl;
#include <galay-kernel/kernel/Coroutine.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <string>
#include <thread>

#ifdef USE_KQUEUE
#include <galay-kernel/kernel/KqueueScheduler.h>
using IOSchedulerType = galay::kernel::KqueueScheduler;
#elif defined(USE_EPOLL)
#include <galay-kernel/kernel/EpollScheduler.h>
using IOSchedulerType = galay::kernel::EpollScheduler;
#elif defined(USE_IOURING)
#include <galay-kernel/kernel/IOUringScheduler.h>
using IOSchedulerType = galay::kernel::IOUringScheduler;
#endif

using namespace galay::ssl;
using namespace galay::kernel;

std::atomic<bool> g_running{true};

void signalHandler(int) {
    g_running = false;
}

Coroutine handleClient(SslContext* ctx, GHandle handle) {
    SslSocket client(ctx, handle);
    client.option().handleNonBlock();

    while (!client.isHandshakeCompleted()) {
        auto hs = co_await client.handshake();
        if (!hs) {
            co_await client.close();
            co_return;
        }
    }

    char buffer[4096];
    auto recvResult = co_await client.recv(buffer, sizeof(buffer));
    if (recvResult && recvResult.value().size() > 0) {
        auto& bytes = recvResult.value();
        co_await client.send(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    }

    co_await client.shutdown();
    co_await client.close();
}

Coroutine sslEchoServer(IOSchedulerType* scheduler, SslContext* ctx, uint16_t port) {
    SslSocket listener(ctx);
    listener.option().handleReuseAddr();
    listener.option().handleNonBlock();

    if (!listener.bind(Host(IPType::IPV4, "0.0.0.0", port))) {
        co_return;
    }
    if (!listener.listen(128)) {
        co_return;
    }

    while (g_running) {
        Host clientHost;
        auto accepted = co_await listener.accept(&clientHost);
        if (!accepted) {
            continue;
        }
        scheduler->spawn(handleClient(ctx, accepted.value()));
    }

    co_await listener.close();
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        return 1;
    }

    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGPIPE, SIG_IGN);

    uint16_t port = static_cast<uint16_t>(std::stoi(argv[1]));
    SslContext ctx(SslMethod::TLS_Server);
    if (!ctx.isValid()) {
        return 1;
    }
    if (!ctx.loadCertificate(argv[2])) {
        return 1;
    }
    if (!ctx.loadPrivateKey(argv[3])) {
        return 1;
    }

    IOSchedulerType scheduler;
    scheduler.start();
    scheduler.spawn(sslEchoServer(&scheduler, &ctx, port));

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    scheduler.stop();
    return 0;
}`
                    }
                ]
            }
        ]
    },
    {
        id: 'http',
        name: 'galay-http',
        icon: '🌐',
        tagline: 'HTTP/1.1 + HTTP/2 + WebSocket 协议层',
        indexDescription: '路由 / 静态文件 / WS',
        summary: '提供 HTTP/1.1、HTTP/2 与 WebSocket 协议能力，覆盖路由、静态文件与缓存协商。',
        badges: ['C++23', 'HTTP', 'WebSocket'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-http',
            docs: 'docs/galay-http.html'
        },
        stats: {
            '协议': 'HTTP/1.1 / 2',
            '能力': 'WebSocket / 静态文件',
            '安全': '可选 galay-ssl'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-http 提供 HTTP/1.1、HTTP/2 与 WebSocket 的服务端协议能力，内置路由和静态文件支持。',
                    '它聚焦协议处理与传输效率，业务数据模型、权限体系等需在上层应用实现。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/http-performance.json'
            },
            {
                type: 'code-switch',
                title: '示例',
                switchLabel: '协议',
                defaultTab: 'http',
                tabs: [
                    {
                        id: 'http',
                        label: 'HTTP',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'http_server.cpp',
                                code: `#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"

using namespace galay::http;

Coroutine echoHandler(HttpConn& conn, HttpRequest req) {
    auto response = Http1_1ResponseBuilder::ok()
        .text("Echo: " + req.getBodyStr())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) {
            break;
        }
    }

    co_return;
}

int main() {
    HttpRouter router;
    router.addHandler<HttpMethod::POST>("/echo", echoHandler);
    router.mount("/static", "./html");

    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'http_server.module.cpp',
                                code: `import galay.http;
#include <string>

using namespace galay::http;

Coroutine echoHandler(HttpConn& conn, HttpRequest req) {
    auto response = Http1_1ResponseBuilder::ok()
        .text("Echo: " + req.getBodyStr())
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) {
            break;
        }
    }

    co_return;
}

int main() {
    HttpRouter router;
    router.addHandler<HttpMethod::POST>("/echo", echoHandler);
    router.mount("/static", "./html");

    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'websocket',
                        label: 'WebSocket',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'websocket_server.cpp',
                                code: `#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"
#include "galay-http/kernel/websocket/WsUpgrade.h"
#include "galay-http/kernel/websocket/WsConn.h"
#include "galay-http/kernel/websocket/WsWriterSetting.h"
#include "galay-http/utils/Http1_1ResponseBuilder.h"
#include <string>

using namespace galay::http;
using namespace galay::websocket;

Coroutine handleWs(WsConn& wsConn) {
    auto reader = wsConn.getReader();
    auto writer = wsConn.getWriter(WsWriterSetting::byServer());

    while (true) {
        std::string message;
        WsOpcode opcode;
        auto result = co_await reader.getMessage(message, opcode);
        if (!result || !result.value() || opcode == WsOpcode::Close) {
            break;
        }
        co_await writer.sendText("Echo: " + message);
    }

    co_await wsConn.close();
    co_return;
}

Coroutine wsHandler(HttpConn& conn, HttpRequest req) {
    auto upgrade = WsUpgrade::handleUpgrade(req);
    auto writer = conn.getWriter();
    co_await writer.sendResponse(upgrade.response);
    if (!upgrade.success) {
        co_await conn.close();
        co_return;
    }

    WsConn wsConn = WsConn::from(std::move(conn), true);
    co_await handleWs(wsConn).wait();
    co_return;
}

Coroutine indexHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    auto response = Http1_1ResponseBuilder::ok().text("Use ws://localhost:8080/ws").build();
    co_await writer.sendResponse(response);
    co_await conn.close();
    co_return;
}

int main() {
    HttpRouter router;
    router.addHandler<HttpMethod::GET>("/ws", wsHandler);
    router.addHandler<HttpMethod::GET>("/", indexHandler);

    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'websocket_server.module.cpp',
                                code: `import galay.http;
import galay.websocket;
#include <string>

using namespace galay::http;
using namespace galay::websocket;

Coroutine handleWs(WsConn& wsConn) {
    auto reader = wsConn.getReader();
    auto writer = wsConn.getWriter(WsWriterSetting::byServer());

    while (true) {
        std::string message;
        WsOpcode opcode;
        auto result = co_await reader.getMessage(message, opcode);
        if (!result || !result.value() || opcode == WsOpcode::Close) {
            break;
        }
        co_await writer.sendText("Echo: " + message);
    }

    co_await wsConn.close();
    co_return;
}

Coroutine wsHandler(HttpConn& conn, HttpRequest req) {
    auto upgrade = WsUpgrade::handleUpgrade(req);
    auto writer = conn.getWriter();
    co_await writer.sendResponse(upgrade.response);
    if (!upgrade.success) {
        co_await conn.close();
        co_return;
    }

    WsConn wsConn = WsConn::from(std::move(conn), true);
    co_await handleWs(wsConn).wait();
    co_return;
}

Coroutine indexHandler(HttpConn& conn, HttpRequest req) {
    auto writer = conn.getWriter();
    auto response = Http1_1ResponseBuilder::ok().text("Use ws://localhost:8080/ws").build();
    co_await writer.sendResponse(response);
    co_await conn.close();
    co_return;
}

int main() {
    HttpRouter router;
    router.addHandler<HttpMethod::GET>("/ws", wsHandler);
    router.addHandler<HttpMethod::GET>("/", indexHandler);

    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'http2',
                        label: 'HTTP2',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'h2c_echo_server.cpp',
                                code: `#include "galay-http/kernel/http2/Http2Server.h"
#include <atomic>
#include <chrono>
#include <csignal>
#include <thread>

using namespace galay::http2;

std::atomic<bool> g_running{true};

void signalHandler(int) {
    g_running = false;
}

Coroutine handleStream(Http2Stream::ptr stream) {
    co_await stream->readRequest().wait();
    auto& req = stream->request();

    co_await stream->replyAndWait(
        Http2Headers().status(200).contentType("text/plain").contentLength(req.body.size()),
        req.body
    ).wait();
}

int main() {
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    H2cServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    H2cServer server(config);
    server.start(handleStream);

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    server.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'h2c_echo_server.module.cpp',
                                code: `import galay.http;
#include <atomic>
#include <chrono>
#include <csignal>
#include <thread>

using namespace galay::http2;

std::atomic<bool> g_running{true};

void signalHandler(int) {
    g_running = false;
}

Coroutine handleStream(Http2Stream::ptr stream) {
    co_await stream->readRequest().wait();
    auto& req = stream->request();

    co_await stream->replyAndWait(
        Http2Headers().status(200).contentType("text/plain").contentLength(req.body.size()),
        req.body
    ).wait();
}

int main() {
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    H2cServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;

    H2cServer server(config);
    server.start(handleStream);

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    server.stop();
    return 0;
}`
                            }
                        ]
                    }
                ]
            }
        ]
    },
    {
        id: 'rpc',
        name: 'galay-rpc',
        icon: '📡',
        tagline: '面向服务通信的协程 RPC 框架',
        indexDescription: '服务注册 / 调用 / 超时控制',
        summary: '提供服务注册、远程调用与超时控制能力，用于构建低延迟服务间通信。',
        badges: ['C++23', 'RPC', 'Service'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-rpc',
            docs: 'docs/galay-rpc.html'
        },
        stats: {
            '协议': '二进制协议',
            '发现': '可扩展注册中心',
            '模式': 'Client / Server'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-rpc 提供协程化的服务注册与远程调用框架，用于构建服务间通信链路。',
                    '它负责调用语义、连接管理与超时控制，服务治理策略可按业务自行扩展。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/rpc-performance.json'
            },
            {
                type: 'code',
                title: '示例',
                defaultVariant: 'include',
                variants: [
                    {
                        id: 'include',
                        label: 'Include',
                        filename: 'rpc_server.cpp',
                        code: `#include "galay-rpc/kernel/RpcServer.h"
#include "galay-rpc/kernel/RpcService.h"
#include <memory>

using namespace galay::rpc;

class EchoService : public RpcService {
public:
    EchoService() : RpcService("EchoService") {
        registerMethod("echo", &EchoService::echo);
    }

    Coroutine echo(RpcContext& ctx) {
        ctx.setPayload(ctx.request().payloadView());
        co_return;
    }
};

int main() {
    auto service = std::make_shared<EchoService>();

    RpcServerConfig config;
    config.host = "0.0.0.0";
    config.port = 9000;

    RpcServer server(config);
    server.registerService(service);
    server.start();
    return 0;
}`
                    },
                    {
                        id: 'module',
                        label: 'Module',
                        filename: 'rpc_server.module.cpp',
                        code: `import galay.rpc;
#include <memory>

using namespace galay::rpc;

class EchoService : public RpcService {
public:
    EchoService() : RpcService("EchoService") {
        registerMethod("echo", &EchoService::echo);
    }

    Coroutine echo(RpcContext& ctx) {
        ctx.setPayload(ctx.request().payloadView());
        co_return;
    }
};

int main() {
    auto service = std::make_shared<EchoService>();

    RpcServerConfig config;
    config.host = "0.0.0.0";
    config.port = 9000;

    RpcServer server(config);
    server.registerService(service);
    server.start();
    return 0;
}`
                    }
                ]
            }
        ]
    },
    {
        id: 'redis',
        name: 'galay-redis',
        icon: '🧱',
        tagline: '同步 + 协程化 Redis 客户端',
        indexDescription: 'RESP / Pipeline / Timeout',
        summary: '提供 Sync/Async 两套 Redis 访问方式，覆盖命令执行、超时控制与 Pipeline 能力。',
        badges: ['C++23', 'Redis', 'Cache'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-redis',
            docs: 'docs/galay-redis.html'
        },
        stats: {
            '协议': 'RESP',
            '能力': 'Pipeline / Timeout',
            '模式': 'Sync / Async',
            '依赖': 'kernel / utils'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-redis 封装 RESP 协议并提供协程化命令接口，适合高并发缓存访问。',
                    '它聚焦客户端通信与 Pipeline 性能，不包含 Redis 服务端管理或数据建模能力。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/redis-performance.json'
            },
            {
                type: 'code-switch',
                title: '示例',
                switchLabel: '运行模式',
                defaultTab: 'sync',
                tabs: [
                    {
                        id: 'sync',
                        label: 'Sync',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'redis_sync.cpp',
                                code: `#include "galay-redis/sync/RedisSession.h"
#include "galay-redis/base/RedisConfig.h"
#include <iostream>

using namespace galay::redis;

int main() {
    RedisConfig config;
    RedisSession session(config);

    auto conn = session.connect("127.0.0.1", 6379, "", "", 0, 2);
    if (!conn) {
        std::cerr << "connect failed: " << conn.error().message() << "\\n";
        return 1;
    }

    auto setRes = session.set("demo:key", "demo:value");
    if (!setRes) {
        std::cerr << "set failed: " << setRes.error().message() << "\\n";
        return 1;
    }

    auto getRes = session.get("demo:key");
    if (!getRes) {
        std::cerr << "get failed: " << getRes.error().message() << "\\n";
        return 1;
    }

    session.disconnect();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'redis_sync.module.cpp',
                                code: `import galay.redis;
#include <iostream>

using namespace galay::redis;

int main() {
    RedisConfig config;
    RedisSession session(config);

    auto conn = session.connect("127.0.0.1", 6379, "", "", 0, 2);
    if (!conn) {
        std::cerr << "connect failed: " << conn.error().message() << "\\n";
        return 1;
    }

    auto setRes = session.set("demo:key", "demo:value");
    if (!setRes) {
        std::cerr << "set failed: " << setRes.error().message() << "\\n";
        return 1;
    }

    auto getRes = session.get("demo:key");
    if (!getRes) {
        std::cerr << "get failed: " << getRes.error().message() << "\\n";
        return 1;
    }

    session.disconnect();
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'async',
                        label: 'Async',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'redis_async_pipeline.cpp',
                                code: `#include "galay-redis/async/RedisClient.h"
#include <galay-kernel/kernel/Runtime.h>
#include <chrono>
#include <string>
#include <vector>

using namespace galay::redis;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    RedisClient client(scheduler);
    co_await client.connect("127.0.0.1", 6379);

    std::vector<std::vector<std::string>> commands = {
        {"SET", "k1", "v1"},
        {"SET", "k2", "v2"},
        {"MGET", "k1", "k2"}
    };

    auto result = co_await client.pipeline(commands).timeout(std::chrono::seconds(10));
    (void)result;
    co_await client.close();
    co_return;
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    runtime.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'redis_async_pipeline.module.cpp',
                                code: `import galay.redis;
import galay.kernel;
#include <chrono>
#include <string>
#include <vector>

using namespace galay::redis;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    RedisClient client(scheduler);
    co_await client.connect("127.0.0.1", 6379);

    std::vector<std::vector<std::string>> commands = {
        {"SET", "k1", "v1"},
        {"SET", "k2", "v2"},
        {"MGET", "k1", "k2"}
    };

    auto result = co_await client.pipeline(commands).timeout(std::chrono::seconds(10));
    (void)result;
    co_await client.close();
    co_return;
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    runtime.stop();
    return 0;
}`
                            }
                        ]
                    }
                ]
            }
        ]
    },
    {
        id: 'mysql',
        name: 'galay-mysql',
        icon: '🐬',
        tagline: '覆盖协议细节的 MySQL 客户端',
        indexDescription: '握手认证 / 预处理 / 事务',
        summary: '提供 MySQL 协议连接、查询与事务能力，支持同步/异步与预处理语句。',
        badges: ['C++23', 'MySQL', 'Database'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-mysql',
            docs: 'docs/galay-mysql.html'
        },
        stats: {
            '协议': 'MySQL Protocol',
            '认证': 'native / sha2 / sha256',
            '能力': 'Prepared / Transaction'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-mysql 实现 MySQL 客户端协议流程，提供同步与异步两套查询接口。',
                    '它覆盖连接认证、预处理与事务控制，但 SQL 设计与 ORM 能力由业务层负责。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/mysql-performance.json'
            },
            {
                type: 'code-switch',
                title: '示例',
                switchLabel: '运行模式',
                defaultTab: 'sync',
                tabs: [
                    {
                        id: 'sync',
                        label: 'Sync',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'mysql_sync_query.cpp',
                                code: `#include "galay-mysql/sync/MysqlClient.h"
#include <iostream>

using namespace galay::mysql;

int main() {
    MysqlClient session;
    auto conn = session.connect("127.0.0.1", 3306, "root", "password", "test");
    if (!conn) {
        std::cerr << "connect failed: " << conn.error().message() << "\\n";
        return 1;
    }

    auto res = session.query("SELECT NOW()");
    if (!res) {
        std::cerr << "query failed: " << res.error().message() << "\\n";
        session.close();
        return 1;
    }

    session.close();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'mysql_sync_query.module.cpp',
                                code: `import galay.mysql;
#include <iostream>

using namespace galay::mysql;

int main() {
    MysqlClient session;
    auto conn = session.connect("127.0.0.1", 3306, "root", "password", "test");
    if (!conn) {
        std::cerr << "connect failed: " << conn.error().message() << "\\n";
        return 1;
    }

    auto res = session.query("SELECT NOW()");
    if (!res) {
        std::cerr << "query failed: " << res.error().message() << "\\n";
        session.close();
        return 1;
    }

    session.close();
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'async',
                        label: 'Async',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'mysql_async_query.cpp',
                                code: `#include "galay-mysql/async/AsyncMysqlClient.h"
#include <galay-kernel/kernel/Runtime.h>
#include <expected>
#include <optional>
#include <thread>

using namespace galay::mysql;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    AsyncMysqlClient client(scheduler);

    auto& connAw = client.connect("127.0.0.1", 3306, "root", "password", "test");
    std::expected<std::optional<bool>, MysqlError> conn;
    do {
        conn = co_await connAw;
        if (!conn) co_return;
    } while (!conn->has_value());

    auto& queryAw = client.query("SELECT 1");
    std::expected<std::optional<MysqlResultSet>, MysqlError> query;
    do {
        query = co_await queryAw;
        if (!query) co_return;
    } while (!query->has_value());

    co_await client.close();
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'mysql_async_query.module.cpp',
                                code: `import galay.mysql;
import galay.kernel;
#include <expected>
#include <optional>
#include <thread>

using namespace galay::mysql;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    AsyncMysqlClient client(scheduler);

    auto& connAw = client.connect("127.0.0.1", 3306, "root", "password", "test");
    std::expected<std::optional<bool>, MysqlError> conn;
    do {
        conn = co_await connAw;
        if (!conn) co_return;
    } while (!conn->has_value());

    auto& queryAw = client.query("SELECT 1");
    std::expected<std::optional<MysqlResultSet>, MysqlError> query;
    do {
        query = co_await queryAw;
        if (!query) co_return;
    } while (!query->has_value());

    co_await client.close();
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            }
                        ]
                    }
                ]
            }
        ]
    },
    {
        id: 'mongo',
        name: 'galay-mongo',
        icon: '🍃',
        tagline: '支持 OP_MSG 与 BSON 的 MongoDB 客户端',
        indexDescription: '协议编解码 / 认证 / Pipeline',
        summary: '提供 MongoDB OP_MSG/BSON 通信与认证能力，支持同步/异步及 Pipeline 请求。',
        badges: ['C++23', 'MongoDB', 'Database'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-mongo',
            docs: 'docs/galay-mongo.html'
        },
        stats: {
            '协议': 'OP_MSG / BSON',
            '认证': 'SCRAM-SHA-256',
            '能力': 'Pipeline / Async'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-mongo 提供 MongoDB OP_MSG 与 BSON 编解码能力，支持同步和异步调用模型。',
                    '它聚焦协议通信与并发请求处理，不内置文档结构约束或高级查询封装。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/mongo-performance.json'
            },
            {
                type: 'code-switch',
                title: '示例',
                switchLabel: '运行模式',
                defaultTab: 'sync',
                tabs: [
                    {
                        id: 'sync',
                        label: 'Sync',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'mongo_sync_ping.cpp',
                                code: `#include "galay-mongo/sync/MongoClient.h"
#include <iostream>

using namespace galay::mongo;

int main() {
    MongoClient session;

    MongoConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 27017;
    cfg.database = "admin";

    auto connected = session.connect(cfg);
    if (!connected) {
        std::cerr << "connect failed: " << connected.error().message() << "\\n";
        return 1;
    }

    auto ping = session.ping(cfg.database);
    if (!ping) {
        std::cerr << "ping failed: " << ping.error().message() << "\\n";
        return 1;
    }

    session.close();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'mongo_sync_ping.module.cpp',
                                code: `import galay.mongo;
#include <iostream>

using namespace galay::mongo;

int main() {
    MongoClient session;

    MongoConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 27017;
    cfg.database = "admin";

    auto connected = session.connect(cfg);
    if (!connected) {
        std::cerr << "connect failed: " << connected.error().message() << "\\n";
        return 1;
    }

    auto ping = session.ping(cfg.database);
    if (!ping) {
        std::cerr << "ping failed: " << ping.error().message() << "\\n";
        return 1;
    }

    session.close();
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'async',
                        label: 'Async',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'mongo_async_ping.cpp',
                                code: `#include "galay-mongo/async/AsyncMongoClient.h"
#include <galay-kernel/kernel/Runtime.h>
#include <atomic>
#include <chrono>
#include <thread>

using namespace galay::mongo;
using namespace galay::kernel;

struct RunState {
    std::atomic<bool> done{false};
};

Coroutine run(IOScheduler* scheduler, RunState* state) {
    MongoConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 27017;
    cfg.database = "admin";

    AsyncMongoConfig asyncCfg;
    AsyncMongoClient client(scheduler, asyncCfg);

    auto conn = co_await client.connect(cfg);
    if (!conn) {
        state->done.store(true);
        co_return;
    }

    auto ping = co_await client.ping(cfg.database);
    (void)ping;

    co_await client.close();
    state->done.store(true);
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    RunState state;
    scheduler->spawn(run(scheduler, &state));

    while (!state.done.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    runtime.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'mongo_async_ping.module.cpp',
                                code: `import galay.mongo;
import galay.kernel;
#include <atomic>
#include <chrono>
#include <thread>

using namespace galay::mongo;
using namespace galay::kernel;

struct RunState {
    std::atomic<bool> done{false};
};

Coroutine run(IOScheduler* scheduler, RunState* state) {
    MongoConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 27017;
    cfg.database = "admin";

    AsyncMongoConfig asyncCfg;
    AsyncMongoClient client(scheduler, asyncCfg);

    auto conn = co_await client.connect(cfg);
    if (!conn) {
        state->done.store(true);
        co_return;
    }

    auto ping = co_await client.ping(cfg.database);
    (void)ping;

    co_await client.close();
    state->done.store(true);
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    RunState state;
    scheduler->spawn(run(scheduler, &state));

    while (!state.done.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    runtime.stop();
    return 0;
}`
                            }
                        ]
                    }
                ]
            }
        ]
    },
    {
        id: 'etcd',
        name: 'galay-etcd',
        icon: '🔑',
        tagline: 'etcd v3 协程客户端',
        indexDescription: 'KV / Lease / Prefix 查询',
        summary: '提供 etcd v3 的 Sync 包装与 Async 原生客户端，覆盖 KV、租约、前缀查询与 Pipeline。',
        badges: ['C++23', 'etcd', 'Service Discovery'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-etcd',
            docs: 'docs/galay-etcd.html'
        },
        stats: {
            '协议': 'etcd v3 HTTP/JSON',
            '传输': 'TcpSocket + HTTP',
            '模式': 'Sync / Async',
            '能力': 'KV / Lease / Pipeline'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-etcd 基于 etcd v3 HTTP/JSON API 提供协程化 KV、租约与前缀操作接口。',
                    '它定位为配置与注册发现访问层，集群运维、权限与策略治理需外部系统配合。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/etcd-performance.json'
            },
            {
                type: 'code-switch',
                title: '示例',
                switchLabel: '运行模式',
                defaultTab: 'sync',
                tabs: [
                    {
                        id: 'sync',
                        label: 'Sync',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'etcd_sync_smoke.cpp',
                                code: `#include "galay-etcd/sync/EtcdClient.h"
#include <galay-kernel/kernel/Runtime.h>
#include <chrono>
#include <thread>

using namespace galay::etcd;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    EtcdConfig cfg;
    cfg.endpoint = "http://127.0.0.1:2379";
    cfg.api_prefix = "/v3";

    EtcdClient session(scheduler, cfg);
    co_await session.connect();
    co_await session.put("/galay/key", "value");
    co_await session.get("/galay/key");
    co_await session.del("/galay/key");
    co_await session.close();
    co_return;
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'etcd_sync_smoke.module.cpp',
                                code: `import galay.etcd;
import galay.kernel;
#include <chrono>
#include <thread>

using namespace galay::etcd;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    EtcdConfig cfg;
    cfg.endpoint = "http://127.0.0.1:2379";
    cfg.api_prefix = "/v3";

    EtcdClient session(scheduler, cfg);
    co_await session.connect();
    co_await session.put("/galay/key", "value");
    co_await session.get("/galay/key");
    co_await session.del("/galay/key");
    co_await session.close();
    co_return;
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            }
                        ]
                    },
                    {
                        id: 'async',
                        label: 'Async',
                        defaultVariant: 'include',
                        variants: [
                            {
                                id: 'include',
                                label: 'Include',
                                filename: 'etcd_async_client.cpp',
                                code: `#include "galay-etcd/async/AsyncEtcdClient.h"
#include <galay-kernel/kernel/Runtime.h>
#include <chrono>
#include <thread>

using namespace galay::etcd;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    EtcdConfig cfg;
    cfg.endpoint = "http://127.0.0.1:2379";
    cfg.api_prefix = "/v3";

    AsyncEtcdClient client(scheduler, cfg);
    auto conn = co_await client.connect();
    if (!conn.has_value()) {
        co_return;
    }

    co_await client.put("/galay/key", "value");
    co_await client.get("/galay/key");
    co_await client.del("/galay/key");
    co_await client.close();
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            },
                            {
                                id: 'module',
                                label: 'Module',
                                filename: 'etcd_async_client.module.cpp',
                                code: `import galay.etcd;
import galay.kernel;
#include <chrono>
#include <thread>

using namespace galay::etcd;
using namespace galay::kernel;

Coroutine run(IOScheduler* scheduler) {
    EtcdConfig cfg;
    cfg.endpoint = "http://127.0.0.1:2379";
    cfg.api_prefix = "/v3";

    AsyncEtcdClient client(scheduler, cfg);
    auto conn = co_await client.connect();
    if (!conn.has_value()) {
        co_return;
    }

    co_await client.put("/galay/key", "value");
    co_await client.get("/galay/key");
    co_await client.del("/galay/key");
    co_await client.close();
}

int main() {
    Runtime runtime;
    runtime.start();

    auto* scheduler = runtime.getNextIOScheduler();
    scheduler->spawn(run(scheduler));

    std::this_thread::sleep_for(std::chrono::seconds(1));
    runtime.stop();
    return 0;
}`
                            }
                        ]
                    }
                ]
            }
        ]
    },
    {
        id: 'utils',
        name: 'galay-utils',
        icon: '🛠️',
        tagline: '面向工程基础能力的 C++23 工具库',
        indexDescription: '数据结构 / 并发组件 / 分布式工具',
        summary: '提供字符串、并发、限流与一致性哈希等基础组件，采用纯头文件方式集成。',
        badges: ['C++23', 'Header-only', 'Utils'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-utils',
            docs: 'docs/galay-utils.html'
        },
        stats: {
            '类型': '纯头文件',
            '模块': 'String / Thread / Balancer',
            '平台': '跨平台'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-utils 是面向工程基础设施的头文件工具集，涵盖字符串、并发与分布式常用组件。',
                    '它强调轻量可组合的基础能力，不替代完整业务框架或领域特定库。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/utils-performance.json'
            },
            {
                type: 'code',
                title: '示例',
                defaultVariant: 'include',
                variants: [
                    {
                        id: 'include',
                        label: 'Include',
                        filename: 'utils_example.cpp',
                        code: `#include <galay-utils/galay-utils.hpp>
#include <iostream>
#include <string>

using namespace galay::utils;

int main() {
    auto parts = StringUtils::split("hello,world", ',');
    std::cout << StringUtils::join(parts, " ") << "\\n";

    ConsistentHash<std::string> hash;
    hash.addNode("server1", 100);
    hash.addNode("server2", 100);
    auto node = hash.getNode("user_123");
    std::cout << "selected node: " << node << "\\n";

    return 0;
}`
                    },
                    {
                        id: 'module',
                        label: 'Module',
                        filename: 'utils_example.module.cpp',
                        code: `import galay.utils;
#include <iostream>
#include <string>

using namespace galay::utils;

int main() {
    auto parts = StringUtils::split("hello,world", ',');
    std::cout << StringUtils::join(parts, " ") << "\\n";

    ConsistentHash<std::string> hash;
    hash.addNode("server1", 100);
    hash.addNode("server2", 100);
    auto node = hash.getNode("user_123");
    std::cout << "selected node: " << node << "\\n";

    return 0;
}`
                    }
                ]
            }
        ]
    },
    {
        id: 'mcp',
        name: 'galay-mcp',
        icon: '🤖',
        tagline: 'MCP 协议实现与 AI 工具接入层',
        indexDescription: 'JSON-RPC / Tool 调用 / stdio+HTTP',
        summary: '提供 MCP 协议对接与工具暴露能力，支持 stdio/HTTP 传输接入 AI 工具调用。',
        badges: ['C++23', 'JSON-RPC', 'HTTP', 'AI'],
        language: 'C++23',
        license: 'MIT',
        links: {
            github: 'https://github.com/gzj-creator/galay-mcp',
            docs: 'docs/galay-mcp.html'
        },
        stats: {
            '协议': 'MCP',
            '通信': 'JSON-RPC 2.0',
            '传输': 'stdio / HTTP'
        },
        modules: [
            {
                type: 'text',
                title: '简介',
                paragraphs: [
                    'galay-mcp 实现 MCP 协议并支持 stdio/HTTP 传输，便于 C++ 服务接入 AI 工具调用。',
                    '它负责协议对接与工具暴露，不直接提供模型推理能力或业务编排逻辑。'
                ]
            },
            {
                type: 'data',
                dataFile: 'data/mcp-performance.json'
            },
            {
                type: 'code',
                title: '示例',
                defaultVariant: 'include',
                variants: [
                    {
                        id: 'include',
                        label: 'Include',
                        filename: 'mcp_stdio_server.cpp',
                        code: `#include "galay-mcp/server/McpStdioServer.h"
#include "galay-mcp/common/McpSchemaBuilder.h"
#include "galay-mcp/common/JsonWriter.h"
#include <expected>

using namespace galay::mcp;

int main() {
    McpStdioServer server;
    server.setServerInfo("example-server", "1.0.0");

    auto schema = SchemaBuilder()
        .addString("message", "要回显的消息", true)
        .build();

    server.addTool(
        "echo",
        "回显输入消息",
        schema,
        [](const JsonElement& args) -> std::expected<JsonString, McpError> {
            (void)args;
            JsonWriter writer;
            writer.StartObject();
            writer.Key("ok");
            writer.Bool(true);
            writer.EndObject();
            return writer.TakeString();
        }
    );

    server.run();
    return 0;
}`
                    },
                    {
                        id: 'module',
                        label: 'Module',
                        filename: 'mcp_stdio_server.module.cpp',
                        code: `import galay.mcp;
#include <expected>

using namespace galay::mcp;

int main() {
    McpStdioServer server;
    server.setServerInfo("example-server", "1.0.0");

    auto schema = SchemaBuilder()
        .addString("message", "要回显的消息", true)
        .build();

    server.addTool(
        "echo",
        "回显输入消息",
        schema,
        [](const JsonElement& args) -> std::expected<JsonString, McpError> {
            (void)args;
            JsonWriter writer;
            writer.StartObject();
            writer.Key("ok");
            writer.Bool(true);
            writer.EndObject();
            return writer.TakeString();
        }
    );

    server.run();
    return 0;
}`
                    }
                ]
            }
        ]
    }
];

const DATA_MODULE_CACHE = new Map();

async function fetchJsonData(path) {
    if (!path) return null;
    if (DATA_MODULE_CACHE.has(path)) {
        return DATA_MODULE_CACHE.get(path);
    }

    const promise = fetch(path)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load ${path}`);
            }
            return response.json();
        })
        .catch(error => {
            console.warn(`Performance data not loaded: ${path}`, error);
            return null;
        });

    DATA_MODULE_CACHE.set(path, promise);
    return promise;
}

function normalizeDataModules(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.modules)) return payload.modules;
    return [];
}

async function expandModules(modules) {
    const expanded = [];
    for (const module of modules) {
        if (module && typeof module.dataFile === 'string') {
            const payload = await fetchJsonData(module.dataFile);
            const dataModules = normalizeDataModules(payload);
            if (dataModules.length) {
                expanded.push(...dataModules);
            }
            continue;
        }
        expanded.push(module);
    }
    return expanded;
}

async function hydrateProjects(projects) {
    const dataFiles = new Set();
    projects.forEach(project => {
        const modules = Array.isArray(project.modules) ? project.modules : [];
        modules.forEach(module => {
            if (module && typeof module.dataFile === 'string') {
                dataFiles.add(module.dataFile);
            }
        });
    });

    dataFiles.forEach(path => {
        fetchJsonData(path);
    });

    const hydrated = await Promise.all(projects.map(async project => {
        const modules = Array.isArray(project.modules) ? project.modules : [];
        const expanded = await expandModules(modules);
        return {
            ...project,
            modules: expanded.length ? expanded : modules
        };
    }));

    return hydrated;
}

let allProjects = [];
let activeProjectId = null;
const INDEX_PIN_STORAGE_KEY = 'projects-index-pinned-v2';
let closeIndexDrawer = () => {};
let isIndexDrawerPinned = () => false;

const localProjectMap = new Map(
    PROJECTS_VECTOR.map(project => [project.id, normalizeProject(project)])
);

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const numberFormatter = new Intl.NumberFormat('en-US');

function formatNumber(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return value;
    }
    return numberFormatter.format(value);
}

function normalizeProject(project) {
    return {
        id: project.id,
        name: project.name,
        icon: project.icon || '📦',
        tagline: project.tagline || project.description || '',
        indexDescription: project.indexDescription || project.shortDescription || project.tagline || '',
        summary: project.summary || project.description || '',
        badges: project.badges || [project.language, project.license].filter(Boolean),
        language: project.language || 'C++23',
        license: project.license || 'MIT',
        links: project.links || {
            github: project.github || '',
            docs: project.docs || 'docs/index.html'
        },
        stats: project.stats || {},
        modules: Array.isArray(project.modules) ? project.modules : []
    };
}

function mergeWithLocal(project) {
    const fallback = localProjectMap.get(project.id);
    if (!fallback) {
        return project;
    }

    const merged = {
        ...fallback,
        ...project,
        badges: project.badges?.length ? project.badges : fallback.badges,
        links: {
            ...fallback.links,
            ...project.links
        },
        stats: Object.keys(project.stats || {}).length ? project.stats : fallback.stats,
        modules: project.modules?.length ? project.modules : fallback.modules
    };

    merged.tagline = project.tagline || fallback.tagline;
    merged.summary = project.summary || fallback.summary;
    merged.indexDescription = project.indexDescription || fallback.indexDescription;
    merged.icon = project.icon || fallback.icon;
    merged.name = project.name || fallback.name;

    return merged;
}

async function loadProjects() {
    let loadedFromApi = false;
    try {
        const response = await fetch(`${API_BASE}/projects`);
        if (!response.ok) {
            throw new Error('Failed to fetch projects');
        }

        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
            const normalizedRemote = data.map(normalizeProject);
            const remoteById = new Map(normalizedRemote.map(project => [project.id, project]));

            const ordered = PROJECTS_VECTOR.map(local => {
                const remote = remoteById.get(local.id);
                return remote ? mergeWithLocal(remote) : normalizeProject(local);
            });

            const extras = normalizedRemote
                .filter(project => !localProjectMap.has(project.id))
                .map(mergeWithLocal);

            allProjects = [...ordered, ...extras];
            loadedFromApi = true;
        }
    } catch (error) {
        console.warn('Use local project data:', error);
    }

    if (!loadedFromApi) {
        allProjects = PROJECTS_VECTOR.map(normalizeProject);
    }

    allProjects = await hydrateProjects(allProjects);
}

function renderIndex(projects) {
    const container = document.getElementById('projectIndex');
    if (!container) return;

    container.innerHTML = projects.map(project => {
        const meta = [project.language, project.license].filter(Boolean).join(' · ');
        return `
            <button type="button" class="project-index-item" data-project-id="${escapeHtml(project.id)}">
                <div class="project-index-header">
                    <span class="project-index-icon">${escapeHtml(project.icon)}</span>
                    <span class="project-index-name">${escapeHtml(project.name)}</span>
                </div>
                <p class="project-index-desc">${escapeHtml(project.indexDescription || project.summary)}</p>
                <span class="project-index-meta">${escapeHtml(meta)}</span>
            </button>
        `;
    }).join('');

    container.querySelectorAll('.project-index-item').forEach(item => {
        item.addEventListener('click', () => {
            const projectId = item.dataset.projectId;
            selectProject(projectId, { scroll: true, updateHash: true });
            if (!isIndexDrawerPinned()) {
                closeIndexDrawer();
            }
        });
    });
}

function initIndexSidebarDrawer() {
    const shell = document.getElementById('projectsIndexShell');
    const trigger = document.getElementById('projectsIndexTrigger');
    const pinButton = document.getElementById('projectsSidebarPin');
    const layout = document.querySelector('.projects-layout');

    if (!shell || !trigger || !pinButton || !layout) {
        return;
    }

    const isCompact = () => window.matchMedia('(max-width: 1024px)').matches;
    let pinned = false;

    const updatePinnedUi = (nextPinned) => {
        pinned = nextPinned;
        shell.classList.toggle('is-pinned', nextPinned);
        layout.classList.toggle('has-pinned-index', nextPinned && !isCompact());
        pinButton.setAttribute('aria-pressed', String(nextPinned));
        pinButton.textContent = nextPinned ? '取消固定' : '固定';
    };

    const open = () => {
        if (!isCompact()) {
            shell.classList.add('is-open');
        }
    };

    const close = () => {
        if (!isCompact() && !pinned) {
            shell.classList.remove('is-open');
        }
    };

    const applyResponsive = () => {
        if (isCompact()) {
            shell.classList.add('is-open');
            layout.classList.remove('has-pinned-index');
            return;
        }

        if (pinned) {
            shell.classList.add('is-open');
            layout.classList.add('has-pinned-index');
        } else {
            shell.classList.remove('is-open');
            layout.classList.remove('has-pinned-index');
        }
    };

    trigger.addEventListener('mouseenter', open);
    shell.addEventListener('mouseenter', open);
    shell.addEventListener('mouseleave', close);

    trigger.addEventListener('focus', open);
    trigger.addEventListener('click', () => {
        if (isCompact()) return;
        shell.classList.toggle('is-open');
    });

    pinButton.addEventListener('click', () => {
        const nextPinned = !pinned;
        updatePinnedUi(nextPinned);
        if (nextPinned) {
            shell.classList.add('is-open');
        } else {
            shell.classList.remove('is-open');
        }
        try {
            localStorage.setItem(INDEX_PIN_STORAGE_KEY, nextPinned ? '1' : '0');
        } catch (error) {
            console.warn('Failed to persist index pin state:', error);
        }
        applyResponsive();
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !pinned) {
            shell.classList.remove('is-open');
        }
    });

    window.addEventListener('resize', applyResponsive);

    const savedPinned = true;
    updatePinnedUi(savedPinned);
    applyResponsive();

    closeIndexDrawer = close;
    isIndexDrawerPinned = () => pinned;
}

function setActiveIndex(projectId) {
    let activeItem = null;
    document.querySelectorAll('.project-index-item').forEach(item => {
        const isActive = item.dataset.projectId === projectId;
        item.classList.toggle('active', isActive);
        if (isActive) {
            activeItem = item;
        }
    });

    if (activeItem) {
        activeItem.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }
}

function getModuleJumpLabel(module, index) {
    if (module?.title && module.title.trim()) {
        return module.title.trim();
    }

    const typeNames = {
        text: '简介',
        data: '性能数据',
        features: '特性',
        diagram: '架构图',
        code: '示例代码',
        'code-switch': '示例代码',
        table: '数据表',
        modules: '模块清单',
        protocol: '协议示例',
        links: '参考链接'
    };

    return typeNames[module?.type] || `模块 ${index + 1}`;
}

function renderModuleJumpBar(modules) {
    if (!Array.isArray(modules) || modules.length <= 1) {
        return '';
    }

    const items = modules.map((module, index) => {
        const targetId = `project-module-${index}`;
        return `
            <button type="button" class="project-module-jump-btn" data-target-id="${escapeHtml(targetId)}">
                ${escapeHtml(getModuleJumpLabel(module, index))}
            </button>
        `;
    }).join('');

    return `
        <div class="project-module-jump">
            <span class="project-module-jump-label">模块跳转</span>
            <div class="project-module-jump-list">
                ${items}
            </div>
        </div>
    `;
}

function renderProject(project) {
    const container = document.getElementById('projectContent');
    if (!container) return;

    const badges = (project.badges || []).filter(Boolean).map(badge => `
        <span class="badge">${escapeHtml(badge)}</span>
    `).join('');
    const docsLink = project.links?.docs || 'docs/index.html';
    const githubLink = project.links?.github || '';
    const moduleJumpBar = renderModuleJumpBar(project.modules);

    container.innerHTML = `
        <article class="project-detail">
            <div class="project-detail-header">
                <div class="project-detail-info">
                    <span class="project-detail-tagline">${escapeHtml(project.tagline)}</span>
                    <h1 class="project-detail-title">${escapeHtml(project.name)}</h1>
                    <div class="project-detail-badges">${badges}</div>
                    <p class="project-detail-description">${escapeHtml(project.summary)}</p>
                </div>
            </div>
            <div class="project-detail-body">
                <div class="project-detail-content">
                    <section class="project-inline-tools">
                        <div class="project-inline-links">
                            ${githubLink ? `
                                <a href="${escapeHtml(githubLink)}" class="btn btn-primary" target="_blank" rel="noopener">
                                    GitHub 仓库
                                </a>
                            ` : ''}
                            <a href="${escapeHtml(docsLink)}" class="btn btn-secondary">
                                查看文档
                            </a>
                        </div>
                        ${moduleJumpBar}
                    </section>
                    ${renderModules(project.modules)}
                </div>
            </div>
        </article>
    `;

    container.querySelectorAll('.project-module-jump-btn').forEach(button => {
        button.addEventListener('click', () => {
            const targetId = button.dataset.targetId;
            if (!targetId) return;
            const target = container.querySelector(`#${targetId}`);
            if (!target) return;
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    initCodeSwitchModules(container);
    initCodeVariantSwitches(container);
}

function renderModules(modules) {
    if (!Array.isArray(modules) || modules.length === 0) {
        return '<p class="project-empty">暂无模块化说明。</p>';
    }

    return modules.map((module, index) => renderModule(module, index)).join('');
}

function renderCodeWindow(module, options = {}) {
    const {
        hidden = false,
        panelClass = '',
        panelId = '',
        panelDataAttrName = 'tab-panel'
    } = options;
    const codeContent = module.codeHtml ? module.codeHtml : escapeHtml(module.code || '');
    const hiddenClass = hidden ? ' hidden' : '';
    const panelClassName = panelClass ? ` ${panelClass}` : '';
    const attrName = /^[a-z0-9_-]+$/i.test(panelDataAttrName) ? panelDataAttrName : 'tab-panel';
    const panelDataAttr = panelId ? ` data-${attrName}="${escapeHtml(panelId)}"` : '';

    return `
        <div class="code-window${panelClassName}${hiddenClass}"${panelDataAttr}>
            <div class="code-header">
                <span class="code-filename">${escapeHtml(module.filename || 'example.cpp')}</span>
                <button class="code-copy" onclick="copyCode(this)">复制</button>
            </div>
            <pre class="code-content${hiddenClass}"><code>${codeContent}</code></pre>
        </div>
    `;
}

function resolveCodeVariants(tab) {
    const variants = Array.isArray(tab.variants) ? tab.variants.filter(item => item && item.id) : [];
    if (variants.length) {
        return variants;
    }

    return [
        {
            id: 'include',
            label: 'Include',
            filename: tab.filename,
            code: tab.code,
            codeHtml: tab.codeHtml
        }
    ];
}

function renderCodeSwitchPanel(tab, hidden) {
    const variants = resolveCodeVariants(tab);
    const hiddenClass = hidden ? ' hidden' : '';
    const defaultVariant = tab.defaultVariant || variants.find(item => item.id === 'include')?.id || variants[0].id;

    if (variants.length === 1) {
        return `
            <div class="code-switch-panel${hiddenClass}" data-tab-panel="${escapeHtml(tab.id)}">
                ${renderCodeWindow(variants[0])}
            </div>
        `;
    }

    return `
        <div class="code-switch-panel${hiddenClass}" data-tab-panel="${escapeHtml(tab.id)}">
            <div class="code-variant" data-default-variant="${escapeHtml(defaultVariant)}">
                <div class="code-variant-tabs" role="tablist" aria-label="代码版本">
                    ${variants.map(item => `
                        <button
                            type="button"
                            class="code-variant-tab"
                            data-variant-id="${escapeHtml(item.id)}"
                            role="tab"
                            aria-selected="false"
                        >
                            ${escapeHtml(item.label || item.id)}
                        </button>
                    `).join('')}
                </div>
                <div class="code-variant-panels">
                    ${variants.map(item => {
                        const isHidden = item.id !== defaultVariant;
                        return renderCodeWindow(item, {
                            hidden: isHidden,
                            panelClass: 'code-variant-panel',
                            panelId: item.id,
                            panelDataAttrName: 'variant-panel'
                        });
                    }).join('')}
                </div>
            </div>
        </div>
    `;
}

function renderCodeSwitchModule(module, moduleId) {
    const tabs = Array.isArray(module.tabs) ? module.tabs.filter(item => item && item.id) : [];
    if (!tabs.length) {
        return '';
    }

    const fallbackDefault = tabs.find(item => item.id === 'sync')?.id || tabs[0].id;
    const defaultTab = module.defaultTab || fallbackDefault;
    const switchLabel = module.switchLabel || '示例类型';

    return `
        <section class="project-module project-code-switch" id="${moduleId}">
            ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
            <div class="code-switch" data-default-tab="${escapeHtml(defaultTab)}">
                <div class="code-switch-head">
                    <span class="code-switch-label">${escapeHtml(switchLabel)}</span>
                    <div class="code-switch-tabs" role="tablist" aria-label="${escapeHtml(switchLabel)}">
                        ${tabs.map(item => `
                            <button
                                type="button"
                                class="code-switch-tab"
                                data-tab-id="${escapeHtml(item.id)}"
                                role="tab"
                                aria-selected="false"
                            >
                                ${escapeHtml(item.label || item.id)}
                            </button>
                        `).join('')}
                    </div>
                </div>
                <div class="code-switch-panels">
                    ${tabs.map(item => {
                        const hidden = item.id !== defaultTab;
                        return renderCodeSwitchPanel(item, hidden);
                    }).join('')}
                </div>
            </div>
        </section>
    `;
}

function initCodeVariantSwitches(container) {
    if (!container) return;

    container.querySelectorAll('.code-variant').forEach(variantGroup => {
        const tabs = Array.from(variantGroup.querySelectorAll('.code-variant-tab'));
        const panels = Array.from(variantGroup.querySelectorAll('.code-variant-panel'));
        if (!tabs.length || !panels.length) {
            return;
        }

        const activate = (variantId) => {
            tabs.forEach(button => {
                const isActive = button.dataset.variantId === variantId;
                button.classList.toggle('active', isActive);
                button.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });

            panels.forEach(panel => {
                const isActive = panel.dataset.variantPanel === variantId;
                panel.classList.toggle('hidden', !isActive);
                const pre = panel.querySelector('pre.code-content');
                if (pre) {
                    pre.classList.toggle('hidden', !isActive);
                }
            });
        };

        const initialVariant = variantGroup.dataset.defaultVariant || tabs[0].dataset.variantId;
        if (initialVariant) {
            activate(initialVariant);
        }

        tabs.forEach(button => {
            button.addEventListener('click', () => {
                const variantId = button.dataset.variantId;
                if (!variantId) return;
                activate(variantId);
            });
        });
    });
}

function initCodeSwitchModules(container) {
    if (!container) return;

    container.querySelectorAll('.code-switch').forEach(codeSwitch => {
        const tabs = Array.from(codeSwitch.querySelectorAll('.code-switch-tab'));
        const panels = Array.from(codeSwitch.querySelectorAll('.code-switch-panel'));
        if (!tabs.length || !panels.length) {
            return;
        }

        const activate = (tabId) => {
            tabs.forEach(button => {
                const isActive = button.dataset.tabId === tabId;
                button.classList.toggle('active', isActive);
                button.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });

            panels.forEach(panel => {
                const isActive = panel.dataset.tabPanel === tabId;
                panel.classList.toggle('hidden', !isActive);
            });
        };

        const initialTab = codeSwitch.dataset.defaultTab || tabs[0].dataset.tabId;
        activate(initialTab);

        tabs.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.dataset.tabId;
                if (!tabId) return;
                activate(tabId);
            });
        });

    });
}

function renderModule(module, index) {
    const moduleId = `project-module-${index}`;

    switch (module.type) {
        case 'text':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    ${(module.paragraphs || []).map(p => `<p>${escapeHtml(p)}</p>`).join('')}
                </section>
            `;
        case 'data': {
            const machine = module.machine || {};
            const machineItems = Array.isArray(machine.items) ? machine.items : [];
            const table = module.table || {};
            const tableColumns = Array.isArray(table.columns) ? table.columns : [];
            const tableRows = Array.isArray(table.rows) ? table.rows : [];
            const chart = module.chart || {};
            const chartItems = Array.isArray(chart.items) ? chart.items : [];
            const maxValue = chartItems.reduce((max, item) => {
                const value = typeof item.value === 'number' ? item.value : Number(item.value);
                return Number.isFinite(value) ? Math.max(max, value) : max;
            }, 0);

            const noteText = typeof module.note === 'string' ? module.note.trim() : '';
            const isSourceNote = /^(数据来源|Data\s*Source)\s*[:：]/i.test(noteText);
            const note = noteText && !isSourceNote ? `<p class="data-note">${escapeHtml(noteText)}</p>` : '';
            const emptyText = module.emptyText ? `<div class="data-empty">${escapeHtml(module.emptyText)}</div>` : '';

            const machineBlock = machineItems.length ? `
                <div class="data-machine">
                    <h3>${escapeHtml(machine.title || '测试环境')}</h3>
                    <div class="machine-grid">
                        ${machineItems.map(item => `
                            <div class="machine-item">
                                <span class="machine-label">${escapeHtml(item.label)}</span>
                                <span class="machine-value">${escapeHtml(item.value)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : '';

            const tableBlock = tableColumns.length ? `
                <div class="data-table">
                    <h3>${escapeHtml(table.title || '压测数据')}</h3>
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    ${tableColumns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.map(row => `
                                    <tr>
                                        ${row.map(cell => renderTableCell(cell)).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : '';

            const chartBlock = chartItems.length ? `
                <div class="data-chart">
                    <h3>${escapeHtml(chart.title || '数据趋势')}</h3>
                    <div class="chart-list">
                        ${chartItems.map(item => {
                            const rawValue = typeof item.value === 'number' ? item.value : Number(item.value);
                            const value = Number.isFinite(rawValue) ? rawValue : 0;
                            const height = maxValue ? Math.max(4, (value / maxValue) * 100) : 0;
                            const displayValue = item.display ?? formatNumber(value);
                            const unit = item.unit || chart.unit || '';
                            return `
                                <div class="chart-item">
                                    <div class="chart-bar-container">
                                        <div class="chart-bar" style="height: ${height}%;"></div>
                                    </div>
                                    <div class="chart-meta">
                                        <span class="chart-label">${escapeHtml(item.label)}</span>
                                        <span class="chart-value">${escapeHtml(`${displayValue}${unit ? ` ${unit}` : ''}`)}</span>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : '';

            return `
                <section class="project-module project-data" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    ${note}
                    <div class="data-grid">
                        ${machineBlock}
                        ${tableBlock}
                    </div>
                    ${emptyText}
                    ${chartBlock}
                </section>
            `;
        }
        case 'features':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="feature-grid">
                        ${(module.items || []).map(item => `
                            <div class="feature-card">
                                <span class="feature-icon">${escapeHtml(item.icon || '✨')}</span>
                                <h4>${escapeHtml(item.title)}</h4>
                                <p>${escapeHtml(item.text)}</p>
                            </div>
                        `).join('')}
                    </div>
                </section>
            `;
        case 'diagram': {
            const layers = Array.isArray(module.layers) ? module.layers : [];
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="architecture-diagram">
                        <div class="architecture-layers">
                            ${layers.map((layer, index) => {
                                const data = typeof layer === 'string' ? { label: layer } : layer;
                                const cls = data.highlight ? 'architecture-layer highlight' : 'architecture-layer';
                                return `
                                    <div class="${cls}">${escapeHtml(data.label)}</div>
                                    ${index < layers.length - 1 ? '<div class="architecture-arrow">↓</div>' : ''}
                                `;
                            }).join('')}
                        </div>
                    </div>
                </section>
            `;
        }
        case 'code': {
            const variants = Array.isArray(module.variants) ? module.variants.filter(item => item && item.id) : [];
            if (variants.length > 1) {
                const defaultVariant = module.defaultVariant || variants.find(item => item.id === 'include')?.id || variants[0].id;
                return `
                    <section class="project-module project-code" id="${moduleId}">
                        ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                        <div class="code-variant" data-default-variant="${escapeHtml(defaultVariant)}">
                            <div class="code-variant-tabs" role="tablist" aria-label="代码版本">
                                ${variants.map(item => `
                                    <button
                                        type="button"
                                        class="code-variant-tab"
                                        data-variant-id="${escapeHtml(item.id)}"
                                        role="tab"
                                        aria-selected="false"
                                    >
                                        ${escapeHtml(item.label || item.id)}
                                    </button>
                                `).join('')}
                            </div>
                            <div class="code-variant-panels">
                                ${variants.map(item => {
                                    const hidden = item.id !== defaultVariant;
                                    return renderCodeWindow(item, {
                                        hidden,
                                        panelClass: 'code-variant-panel',
                                        panelId: item.id,
                                        panelDataAttrName: 'variant-panel'
                                    });
                                }).join('')}
                            </div>
                        </div>
                    </section>
                `;
            }

            return `
                <section class="project-module project-code" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    ${renderCodeWindow(module)}
                </section>
            `;
        }
        case 'code-switch':
            return renderCodeSwitchModule(module, moduleId);
        case 'table':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    ${(module.columns || []).map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${(module.rows || []).map(row => `
                                    <tr>
                                        ${row.map(cell => renderTableCell(cell)).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </section>
            `;
        case 'modules':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="modules-grid">
                        ${(module.categories || []).map(category => `
                            <div class="module-category">
                                <h4>${escapeHtml(category.title)}</h4>
                                <ul class="module-list">
                                    ${(category.items || []).map(item => `
                                        <li><span class="module-name">${escapeHtml(item.name)}</span> ${escapeHtml(item.desc)}</li>
                                    `).join('')}
                                </ul>
                            </div>
                        `).join('')}
                    </div>
                </section>
            `;
        case 'protocol':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="protocol-example">
                        ${(module.items || []).map(item => `
                            <div class="protocol-item">
                                <span class="protocol-label">${escapeHtml(item.label)}</span>
                                <code>${escapeHtml(item.code)}</code>
                            </div>
                        `).join('')}
                    </div>
                </section>
            `;
        case 'links':
            return `
                <section class="project-module" id="${moduleId}">
                    ${module.title ? `<h2>${escapeHtml(module.title)}</h2>` : ''}
                    <div class="project-links">
                        ${(module.items || []).map(item => `
                            <a class="project-link-item" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">
                                <span class="project-link-label">${escapeHtml(item.label)}</span>
                                <span class="project-link-url">${escapeHtml(item.url)}</span>
                            </a>
                        `).join('')}
                    </div>
                </section>
            `;
        default:
            return '';
    }
}

function renderTableCell(cell) {
    if (cell && typeof cell === 'object') {
        const rawValue = cell.value ?? '';
        const value = typeof rawValue === 'number' ? escapeHtml(formatNumber(rawValue)) : escapeHtml(rawValue);
        const cls = cell.highlight ? ' class="highlight"' : '';
        return `<td${cls}>${value}</td>`;
    }
    if (typeof cell === 'number') {
        return `<td>${escapeHtml(formatNumber(cell))}</td>`;
    }
    return `<td>${escapeHtml(cell ?? '')}</td>`;
}

function getProjectFromHash() {
    const hash = window.location.hash.replace('#', '').trim();
    if (!hash) return null;
    return hash;
}

function selectProject(projectId, options = {}) {
    const project = allProjects.find(p => p.id === projectId);
    if (!project) return;

    activeProjectId = projectId;
    setActiveIndex(projectId);
    renderProject(project);

    if (options.updateHash) {
        history.replaceState(null, '', `#${projectId}`);
    }

    if (options.scroll) {
        const content = document.getElementById('projectContent');
        if (content) {
            content.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

async function initProjectsPage() {
    await loadProjects();
    renderIndex(allProjects);

    const initialProjectId = getProjectFromHash() || allProjects[0]?.id;
    if (initialProjectId) {
        selectProject(initialProjectId, { updateHash: false, scroll: false });
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initIndexSidebarDrawer();
    initProjectsPage();

    window.addEventListener('hashchange', () => {
        const projectId = getProjectFromHash();
        if (projectId && projectId !== activeProjectId) {
            selectProject(projectId, { updateHash: false, scroll: true });
        }
    });
});
