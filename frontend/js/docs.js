/* ============================================
   DOCS PAGE - JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// 当前选中的文档
let currentDocId = null;
let allDocs = [];

// 分类映射
const categoryNames = {
    'getting-started': '快速开始',
    'guide': '使用指南',
    'advanced': '进阶主题',
    'api': 'API 参考'
};

// 加载文档列表
async function loadDocs() {
    try {
        const response = await fetch(`${API_BASE}/docs`);
        if (!response.ok) {
            throw new Error('Failed to fetch docs');
        }

        allDocs = await response.json();
        renderSidebar();

        // 检查 URL hash
        const hash = window.location.hash.slice(1);
        if (hash) {
            loadDoc(hash);
        }

    } catch (error) {
        console.error('Error loading docs:', error);
        // 使用静态数据作为后备
        allDocs = [
            { id: 'quick-start', title: '快速开始', description: '5 分钟内搭建你的第一个 Galay 应用', category: 'getting-started', order: 1 },
            { id: 'installation', title: '安装指南', description: '详细的安装和配置说明', category: 'getting-started', order: 2 },
            { id: 'http-server', title: 'HTTP 服务器', description: '使用 HttpServer 创建 Web 服务', category: 'guide', order: 3 },
            { id: 'http-router', title: '路由系统', description: 'HttpRouter 的使用方法和路由匹配规则', category: 'guide', order: 4 },
            { id: 'static-files', title: '静态文件服务', description: '配置静态文件服务和传输模式', category: 'guide', order: 5 },
            { id: 'websocket', title: 'WebSocket', description: 'WebSocket 服务器和客户端的使用', category: 'guide', order: 6 },
            { id: 'coroutine', title: '协程基础', description: 'C++20 协程在 Galay 中的应用', category: 'advanced', order: 7 },
            { id: 'performance', title: '性能优化', description: '性能调优和最佳实践', category: 'advanced', order: 8 },
            { id: 'api-httpserver', title: 'HttpServer API', description: 'HttpServer 类的完整 API 参考', category: 'api', order: 9 },
            { id: 'api-httprouter', title: 'HttpRouter API', description: 'HttpRouter 类的完整 API 参考', category: 'api', order: 10 }
        ];
        renderSidebar();
    }
}

// 渲染侧边栏
function renderSidebar() {
    const categories = {
        'getting-started': document.getElementById('gettingStartedList'),
        'guide': document.getElementById('guideList'),
        'advanced': document.getElementById('advancedList'),
        'api': document.getElementById('apiList')
    };

    // 清空所有列表
    Object.values(categories).forEach(list => {
        if (list) list.innerHTML = '';
    });

    // 按 order 排序
    const sortedDocs = [...allDocs].sort((a, b) => a.order - b.order);

    // 填充列表
    sortedDocs.forEach(doc => {
        const list = categories[doc.category];
        if (list) {
            const li = document.createElement('li');
            li.innerHTML = `
                <a class="docs-sidebar-link ${doc.id === currentDocId ? 'active' : ''}"
                   data-doc="${doc.id}"
                   href="#${doc.id}">
                    ${doc.title}
                </a>
            `;
            list.appendChild(li);
        }
    });

    // 绑定点击事件
    document.querySelectorAll('.docs-sidebar-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const docId = link.dataset.doc;
            loadDoc(docId);
            window.location.hash = docId;
        });
    });
}

// 加载单个文档
async function loadDoc(docId) {
    const container = document.getElementById('docsContent');
    if (!container) return;

    currentDocId = docId;

    // 更新侧边栏激活状态
    document.querySelectorAll('.docs-sidebar-link').forEach(link => {
        link.classList.toggle('active', link.dataset.doc === docId);
    });

    // 显示加载状态
    container.innerHTML = `
        <div class="docs-loading">
            <div class="loading-spinner"></div>
        </div>
    `;

    // 查找文档
    const doc = allDocs.find(d => d.id === docId);
    if (!doc) {
        container.innerHTML = `
            <div class="docs-article">
                <h1>文档不存在</h1>
                <p>请从左侧菜单选择一个文档。</p>
            </div>
        `;
        return;
    }

    // 生成文档内容
    const content = generateDocContent(doc);

    // 获取上一篇和下一篇
    const sortedDocs = [...allDocs].sort((a, b) => a.order - b.order);
    const currentIndex = sortedDocs.findIndex(d => d.id === docId);
    const prevDoc = currentIndex > 0 ? sortedDocs[currentIndex - 1] : null;
    const nextDoc = currentIndex < sortedDocs.length - 1 ? sortedDocs[currentIndex + 1] : null;

    container.innerHTML = `
        <article class="docs-article">
            <header class="docs-article-header">
                <span class="docs-article-category">${categoryNames[doc.category] || doc.category}</span>
                <h1 class="docs-article-title">${doc.title}</h1>
                <p class="docs-article-description">${doc.description}</p>
            </header>
            <div class="docs-article-body">
                ${content}
            </div>
            <nav class="docs-article-nav">
                ${prevDoc ? `
                    <a href="#${prevDoc.id}" class="docs-nav-link prev" data-doc="${prevDoc.id}">
                        <span class="docs-nav-label">← 上一篇</span>
                        <span class="docs-nav-title">${prevDoc.title}</span>
                    </a>
                ` : '<div></div>'}
                ${nextDoc ? `
                    <a href="#${nextDoc.id}" class="docs-nav-link next" data-doc="${nextDoc.id}">
                        <span class="docs-nav-label">下一篇 →</span>
                        <span class="docs-nav-title">${nextDoc.title}</span>
                    </a>
                ` : '<div></div>'}
            </nav>
        </article>
    `;

    // 绑定导航点击事件
    container.querySelectorAll('.docs-nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const docId = link.dataset.doc;
            loadDoc(docId);
            window.location.hash = docId;
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

// 生成文档内容
function generateDocContent(doc) {
    const contents = {
        'quick-start': `
            <h2>环境要求</h2>
            <ul>
                <li>C++20 兼容的编译器 (GCC 11+, Clang 14+, MSVC 19.29+)</li>
                <li>CMake 3.20 或更高版本</li>
                <li>macOS 10.15+ 或 Linux (内核 5.1+ 推荐使用 io_uring)</li>
            </ul>

            <h2>安装依赖</h2>
            <pre><code># macOS
brew install cmake

# Ubuntu/Debian
sudo apt install cmake build-essential

# Fedora
sudo dnf install cmake gcc-c++</code></pre>

            <h2>克隆项目</h2>
            <pre><code>git clone https://github.com/gzj-creator/galay-kernel.git
git clone https://github.com/gzj-creator/galay-http.git
cd galay-http</code></pre>

            <h2>编译运行</h2>
            <pre><code>mkdir build && cd build
cmake ..
make -j$(nproc)
./examples/hello_world</code></pre>

            <h2>第一个程序</h2>
            <p>创建一个简单的 HTTP 服务器：</p>
            <pre><code>#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"

using namespace galay::http;

Coroutine helloHandler(HttpConn& conn, HttpRequest req) {
    auto response = Http1_1ResponseBuilder::ok()
        .text("Hello, World!")
        .build();

    auto writer = conn.getWriter();
    while (true) {
        auto result = co_await writer.sendResponse(response);
        if (!result || result.value()) break;
    }
}

int main() {
    HttpRouter router;
    router.addHandler&lt;HttpMethod::GET&gt;("/", helloHandler);

    HttpServerConfig config;
    config.port = 8080;

    HttpServer server(config);
    server.start(std::move(router));

    return 0;
}</code></pre>

            <p>编译并运行后，访问 <code>http://localhost:8080</code> 即可看到 "Hello, World!"。</p>
        `,

        'installation': `
            <h2>从源码编译</h2>
            <p>Galay 框架采用 CMake 构建系统，支持多种编译选项。</p>

            <h3>基本编译</h3>
            <pre><code>git clone https://github.com/gzj-creator/galay-http.git
cd galay-http
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install</code></pre>

            <h3>编译选项</h3>
            <pre><code># 启用 io_uring (Linux 5.1+)
cmake -DENABLE_IO_URING=ON ..

# 启用调试模式
cmake -DCMAKE_BUILD_TYPE=Debug ..

# 指定安装路径
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..</code></pre>

            <h2>作为子模块使用</h2>
            <pre><code>git submodule add https://github.com/gzj-creator/galay-http.git third_party/galay-http</code></pre>

            <p>在你的 CMakeLists.txt 中：</p>
            <pre><code>add_subdirectory(third_party/galay-http)
target_link_libraries(your_target galay-http)</code></pre>

            <h2>验证安装</h2>
            <pre><code># 运行测试
cd build
ctest --output-on-failure

# 运行示例
./examples/hello_world</code></pre>
        `,

        'http-server': `
            <h2>创建 HTTP 服务器</h2>
            <p>HttpServer 是 Galay-HTTP 的核心类，用于创建和管理 HTTP 服务。</p>

            <h3>基本用法</h3>
            <pre><code>#include "galay-http/kernel/http/HttpServer.h"
#include "galay-http/kernel/http/HttpRouter.h"

using namespace galay::http;

int main() {
    // 创建路由器
    HttpRouter router;

    // 配置服务器
    HttpServerConfig config;
    config.host = "0.0.0.0";
    config.port = 8080;
    config.backlog = 128;

    // 创建并启动服务器
    HttpServer server(config);
    server.start(std::move(router));

    return 0;
}</code></pre>

            <h2>配置选项</h2>
            <table>
                <tr><th>选项</th><th>类型</th><th>默认值</th><th>说明</th></tr>
                <tr><td>host</td><td>string</td><td>"0.0.0.0"</td><td>监听地址</td></tr>
                <tr><td>port</td><td>uint16_t</td><td>8080</td><td>监听端口</td></tr>
                <tr><td>backlog</td><td>int</td><td>128</td><td>连接队列长度</td></tr>
                <tr><td>io_scheduler_count</td><td>int</td><td>0 (自动)</td><td>IO 调度器数量</td></tr>
            </table>

            <h2>优雅关闭</h2>
            <pre><code>#include &lt;csignal&gt;

HttpServer* g_server = nullptr;

void signalHandler(int signum) {
    if (g_server) {
        g_server->stop();
    }
}

int main() {
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    HttpServer server(config);
    g_server = &server;

    server.start(std::move(router));

    while (server.isRunning()) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}</code></pre>
        `,

        'http-router': `
            <h2>路由系统概述</h2>
            <p>HttpRouter 提供了高性能的路由匹配功能，支持精确匹配和参数匹配。</p>

            <h3>路由匹配策略</h3>
            <ul>
                <li><strong>精确匹配</strong>：O(1) 时间复杂度，使用哈希表</li>
                <li><strong>参数匹配</strong>：O(k) 时间复杂度，k 为路径段数</li>
            </ul>

            <h2>注册路由</h2>
            <pre><code>HttpRouter router;

// GET 请求
router.addHandler&lt;HttpMethod::GET&gt;("/users", getUsersHandler);

// POST 请求
router.addHandler&lt;HttpMethod::POST&gt;("/users", createUserHandler);

// 带参数的路由
router.addHandler&lt;HttpMethod::GET&gt;("/users/:id", getUserByIdHandler);

// 通配符路由
router.addHandler&lt;HttpMethod::GET&gt;("/files/*", fileHandler);</code></pre>

            <h2>获取路由参数</h2>
            <pre><code>Coroutine getUserByIdHandler(HttpConn& conn, HttpRequest req) {
    // 从 URI 中提取参数
    std::string uri = req.header().uri();
    size_t lastSlash = uri.rfind('/');
    std::string userId = uri.substr(lastSlash + 1);

    // 处理请求...
    co_return;
}</code></pre>

            <h2>中间件支持</h2>
            <p>可以通过包装处理器来实现中间件功能：</p>
            <pre><code>auto withLogging = [](auto handler) {
    return [handler](HttpConn& conn, HttpRequest req) -> Coroutine {
        LogInfo("Request: {}", req.header().uri());
        co_await handler(conn, std::move(req));
    };
};

router.addHandler&lt;HttpMethod::GET&gt;("/api/data", withLogging(dataHandler));</code></pre>
        `,

        'static-files': `
            <h2>静态文件服务</h2>
            <p>Galay-HTTP 提供了强大的静态文件服务功能，支持多种传输模式。</p>

            <h2>基本配置</h2>
            <pre><code>HttpRouter router;

StaticFileConfig config;
config.setTransferMode(FileTransferMode::AUTO);

router.mount("/static", "./public", config);</code></pre>

            <h2>传输模式</h2>
            <table>
                <tr><th>模式</th><th>说明</th><th>适用场景</th></tr>
                <tr><td>MEMORY</td><td>完全加载到内存</td><td>小文件 (&lt;64KB)</td></tr>
                <tr><td>CHUNK</td><td>分块传输</td><td>中等文件</td></tr>
                <tr><td>SENDFILE</td><td>零拷贝传输</td><td>大文件</td></tr>
                <tr><td>AUTO</td><td>自动选择</td><td>推荐使用</td></tr>
            </table>

            <h2>高级配置</h2>
            <pre><code>StaticFileConfig config;

// 设置传输模式
config.setTransferMode(FileTransferMode::AUTO);

// 设置阈值
config.setSmallFileThreshold(64 * 1024);    // 64KB
config.setLargeFileThreshold(1024 * 1024);  // 1MB

// 启用 ETag 缓存
config.setEnableETag(true);

// 启用 Range 请求（断点续传）
config.setEnableRange(true);</code></pre>

            <h2>MIME 类型</h2>
            <p>系统会自动根据文件扩展名设置 Content-Type，支持常见的文件类型。</p>
        `,

        'websocket': `
            <h2>WebSocket 支持</h2>
            <p>Galay-HTTP 完整实现了 RFC 6455 WebSocket 协议。</p>

            <h2>服务端示例</h2>
            <pre><code>Coroutine wsHandler(HttpConn& conn, HttpRequest req) {
    // 升级到 WebSocket
    auto ws = co_await conn.upgradeToWebSocket(req);

    while (true) {
        // 接收消息
        auto message = co_await ws.receive();

        if (message.isClose()) {
            break;
        }

        // 发送响应
        co_await ws.send("Echo: " + message.text());
    }
}

router.addHandler&lt;HttpMethod::GET&gt;("/ws", wsHandler);</code></pre>

            <h2>消息类型</h2>
            <ul>
                <li><strong>Text</strong>：文本消息</li>
                <li><strong>Binary</strong>：二进制消息</li>
                <li><strong>Ping/Pong</strong>：心跳消息</li>
                <li><strong>Close</strong>：关闭连接</li>
            </ul>

            <h2>心跳保活</h2>
            <pre><code>// 服务端定期发送 Ping
co_await ws.ping();

// 客户端会自动响应 Pong</code></pre>
        `,

        'coroutine': `
            <h2>C++20 协程基础</h2>
            <p>Galay 框架基于 C++20 标准协程实现异步编程模型。</p>

            <h2>协程类型</h2>
            <pre><code>// 基本协程类型
Coroutine myHandler(HttpConn& conn, HttpRequest req) {
    // 异步操作
    co_await someAsyncOperation();

    // 返回
    co_return;
}</code></pre>

            <h2>co_await 表达式</h2>
            <p>使用 <code>co_await</code> 等待异步操作完成：</p>
            <pre><code>// 等待网络 IO
auto data = co_await socket.read();

// 等待定时器
co_await timer.sleep(std::chrono::seconds(1));

// 等待文件 IO
auto content = co_await file.readAll();</code></pre>

            <h2>协程调度</h2>
            <p>Galay 使用事件驱动的调度器管理协程：</p>
            <ul>
                <li>IO 调度器：处理网络和文件 IO</li>
                <li>计算调度器：处理 CPU 密集型任务</li>
            </ul>

            <h2>最佳实践</h2>
            <ul>
                <li>避免在协程中使用阻塞操作</li>
                <li>使用 co_await 而不是轮询</li>
                <li>合理设置调度器数量</li>
            </ul>
        `,

        'performance': `
            <h2>性能优化指南</h2>
            <p>Galay 框架在设计时就考虑了高性能，以下是一些优化建议。</p>

            <h2>基准测试结果</h2>
            <ul>
                <li>单线程 QPS：26-28 万</li>
                <li>吞吐量：130+ MB/s</li>
                <li>延迟：P99 &lt; 1ms</li>
            </ul>

            <h2>优化建议</h2>

            <h3>1. 使用合适的传输模式</h3>
            <pre><code>// 大文件使用 SENDFILE
config.setTransferMode(FileTransferMode::SENDFILE);

// 或使用 AUTO 自动选择
config.setTransferMode(FileTransferMode::AUTO);</code></pre>

            <h3>2. 调整调度器数量</h3>
            <pre><code>HttpServerConfig config;
config.io_scheduler_count = std::thread::hardware_concurrency();
config.compute_scheduler_count = 2;</code></pre>

            <h3>3. 启用缓存</h3>
            <pre><code>StaticFileConfig config;
config.setEnableETag(true);  // 启用 ETag 缓存</code></pre>

            <h3>4. 连接池复用</h3>
            <p>HTTP/1.1 默认启用 Keep-Alive，复用 TCP 连接。</p>

            <h2>性能监控</h2>
            <pre><code>// 使用日志记录性能指标
LogInfo("QPS: {}", server.getQPS());
LogInfo("Active connections: {}", server.getActiveConnections());</code></pre>
        `,

        'api-httpserver': `
            <h2>HttpServer 类</h2>
            <p>HTTP 服务器的核心类，负责监听端口、接受连接和分发请求。</p>

            <h2>构造函数</h2>
            <pre><code>HttpServer(const HttpServerConfig& config);</code></pre>

            <h2>公共方法</h2>

            <h3>start</h3>
            <pre><code>void start(HttpRouter&& router);</code></pre>
            <p>启动服务器，开始监听和处理请求。</p>

            <h3>stop</h3>
            <pre><code>void stop();</code></pre>
            <p>停止服务器，关闭所有连接。</p>

            <h3>isRunning</h3>
            <pre><code>bool isRunning() const;</code></pre>
            <p>检查服务器是否正在运行。</p>

            <h2>HttpServerConfig</h2>
            <pre><code>struct HttpServerConfig {
    std::string host = "0.0.0.0";
    uint16_t port = 8080;
    int backlog = 128;
    int io_scheduler_count = 0;      // 0 = 自动
    int compute_scheduler_count = 0; // 0 = 自动
};</code></pre>
        `,

        'api-httprouter': `
            <h2>HttpRouter 类</h2>
            <p>HTTP 路由器，负责将请求分发到对应的处理器。</p>

            <h2>公共方法</h2>

            <h3>addHandler</h3>
            <pre><code>template&lt;HttpMethod Method&gt;
void addHandler(const std::string& path, HttpHandler handler);</code></pre>
            <p>注册路由处理器。</p>

            <h3>mount</h3>
            <pre><code>bool mount(const std::string& prefix,
           const std::string& directory,
           const StaticFileConfig& config = {});</code></pre>
            <p>挂载静态文件目录。</p>

            <h2>HttpMethod 枚举</h2>
            <pre><code>enum class HttpMethod {
    GET,
    POST,
    PUT,
    DELETE,
    PATCH,
    HEAD,
    OPTIONS
};</code></pre>

            <h2>HttpHandler 类型</h2>
            <pre><code>using HttpHandler = std::function&lt;Coroutine(HttpConn&, HttpRequest)&gt;;</code></pre>

            <h2>路由匹配规则</h2>
            <ul>
                <li><code>/path</code> - 精确匹配</li>
                <li><code>/path/:param</code> - 参数匹配</li>
                <li><code>/path/*</code> - 通配符匹配</li>
            </ul>
        `
    };

    return contents[doc.id] || `
        <h2>概述</h2>
        <p>${doc.description}</p>

        <h2>内容待完善</h2>
        <p>本文档正在编写中，敬请期待。</p>

        <blockquote>
            <p>如果你有任何问题或建议，欢迎在 GitHub 上提出 Issue。</p>
        </blockquote>
    `;
}

// 绑定快速链接点击事件
function bindQuickLinks() {
    document.querySelectorAll('.docs-quick-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const docId = link.dataset.doc;
            if (docId) {
                loadDoc(docId);
                window.location.hash = docId;
            }
        });
    });
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadDocs();
    bindQuickLinks();

    // 监听 hash 变化
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.slice(1);
        if (hash && hash !== currentDocId) {
            loadDoc(hash);
        }
    });
});
