/* ============================================
   DOCS QUICKSTART - Library Pages
   ============================================ */

const DOCS_QUICKSTART_MAP = {
    'galay-kernel': {
        name: 'galay-kernel',
        deps: 'C++23 编译器、CMake 3.16+、spdlog',
        install: '使用 CMake 构建并安装到系统',
        usage: '初始化 Runtime，并在调度器上启动协程任务',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-kernel.git',
            'cd galay-kernel',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.kernel'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DENABLE_CPP23_MODULES=ON',
                'cmake --build build-mod --target galay-kernel-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.kernel;',
                '#else',
                '#include "galay-kernel/kernel/Runtime.h"',
                '#endif',
                '',
                'using namespace galay::kernel;',
                '',
                'int main() {',
                '    Runtime runtime;',
                '    runtime.start();',
                '    runtime.stop();',
                '}'
            ]
        }
    },
    'galay-ssl': {
        name: 'galay-ssl',
        deps: 'C++23 编译器、CMake 3.16+、OpenSSL、galay-kernel',
        install: '先安装 galay-kernel，再构建安装 galay-ssl',
        usage: '创建 TLS 上下文并与网络连接组件组合使用',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-ssl.git',
            'cd galay-ssl',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.ssl'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DBUILD_MODULE_EXAMPLES=ON',
                'cmake --build build-mod --target galay-ssl-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.ssl;',
                '#else',
                '#include "galay-ssl/async/SslContext.h"',
                '#endif',
                '',
                'using namespace galay::ssl;',
                '',
                '// SslContext ctx;'
            ]
        }
    },
    'galay-http': {
        name: 'galay-http',
        deps: 'C++23 编译器、CMake 3.16+、galay-kernel（可选 galay-ssl）',
        install: '先安装依赖库，再构建安装 galay-http',
        usage: '注册路由并启动 HTTP 服务',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-http.git',
            'cd galay-http',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.http', 'galay.http2', 'galay.websocket'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DBUILD_MODULE_EXAMPLES=ON',
                'cmake --build build-mod --target galay-http-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.http;',
                '// import galay.http2;',
                '// import galay.websocket;',
                '#else',
                '#include "galay-http/kernel/http/HttpServer.h"',
                '#include "galay-http/kernel/http/HttpRouter.h"',
                '#endif',
                '',
                'using namespace galay::http;'
            ]
        }
    },
    'galay-rpc': {
        name: 'galay-rpc',
        deps: 'C++23 编译器、CMake 3.16+、galay-kernel、galay-http、nlohmann/json',
        install: '安装依赖后构建并安装 galay-rpc',
        usage: '定义服务接口并注册到 RPC 服务器',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-rpc.git',
            'cd galay-rpc',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.rpc'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DBUILD_MODULE_EXAMPLES=ON',
                'cmake --build build-mod --target galay-rpc-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.rpc;',
                '#else',
                '#include "galay-rpc/kernel/RpcServer.h"',
                '#endif',
                '',
                'using namespace galay::rpc;',
                '',
                '// RpcServer server({"0.0.0.0", 9000});'
            ]
        }
    },
    'galay-redis': {
        name: 'galay-redis',
        deps: 'C++23 编译器、CMake 3.20+、galay-kernel、galay-utils、spdlog',
        install: '安装依赖后构建并安装 galay-redis',
        usage: '创建客户端后执行 Redis 命令或 Pipeline',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-redis.git',
            'cd galay-redis',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.redis'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DGALAY_REDIS_ENABLE_IMPORT_COMPILATION=ON',
                'cmake --build build-mod --target galay-redis-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.redis;',
                '#else',
                '#include "galay-redis/async/RedisClient.h"',
                '#endif',
                '',
                'using namespace galay::redis;'
            ]
        }
    },
    'galay-mysql': {
        name: 'galay-mysql',
        deps: 'C++23 编译器、CMake 3.20+、OpenSSL、spdlog、galay-kernel',
        install: '安装依赖后构建并安装 galay-mysql',
        usage: '创建连接后执行查询、预处理语句与事务',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-mysql.git',
            'cd galay-mysql',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.mysql'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DGALAY_MYSQL_ENABLE_IMPORT_COMPILATION=ON',
                'cmake --build build-mod --target galay-mysql -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.mysql;',
                '#else',
                '#include "galay-mysql/sync/MysqlClient.h"',
                '#endif',
                '',
                'using namespace galay::mysql;'
            ]
        }
    },
    'galay-mongo': {
        name: 'galay-mongo',
        deps: 'C++23 编译器、CMake 3.20+、OpenSSL、spdlog、galay-kernel',
        install: '安装依赖后构建并安装 galay-mongo',
        usage: '创建客户端后执行 CRUD 与 Pipeline 操作',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-mongo.git',
            'cd galay-mongo',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.mongo'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DGALAY_MONGO_ENABLE_IMPORT_COMPILATION=ON',
                'cmake --build build-mod --target galay-mongo-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.mongo;',
                '#else',
                '#include "galay-mongo/sync/MongoClient.h"',
                '#endif',
                '',
                'using namespace galay::mongo;'
            ]
        }
    },
    'galay-etcd': {
        name: 'galay-etcd',
        deps: 'C++23 编译器、CMake 3.20+、simdjson、galay-kernel、galay-http',
        install: '安装依赖后构建并安装 galay-etcd',
        usage: '连接 etcd 后执行 KV、Lease 与前缀查询操作',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-etcd.git',
            'cd galay-etcd',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.etcd'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DGALAY_ETCD_ENABLE_IMPORT_COMPILATION=ON',
                'cmake --build build-mod --target galay-etcd -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.etcd;',
                '#else',
                '#include "galay-etcd/async/EtcdClient.h"',
                '#endif',
                '',
                'using namespace galay::etcd;'
            ]
        }
    },
    'galay-utils': {
        name: 'galay-utils',
        deps: 'C++17 及以上编译器（header-only，无外部依赖）',
        install: 'header-only 库，无需编译安装',
        usage: '在项目中 include 头文件后即可直接使用',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-utils.git',
            '',
            '# 在你的项目中包含头文件目录',
            'include_directories(path/to/galay-utils/include)'
        ],
        module: {
            imports: ['galay.utils'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DBUILD_MODULE_TESTS=ON',
                'cmake --build build-mod --target galay-utils-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.utils;',
                '#else',
                '#include "galay-utils/galay-utils.hpp"',
                '#endif',
                '',
                'using namespace galay::utils;'
            ]
        }
    },
    'galay-mcp': {
        name: 'galay-mcp',
        deps: 'C++23 编译器、CMake 3.16+、galay-kernel、nlohmann/json',
        install: '安装依赖后构建并安装 galay-mcp',
        usage: '注册工具并通过 stdio/HTTP 暴露 MCP 接口',
        commands: [
            '# 克隆仓库',
            'git clone https://github.com/gzj-creator/galay-mcp.git',
            'cd galay-mcp',
            'mkdir build && cd build',
            'cmake .. -DCMAKE_BUILD_TYPE=Release',
            'make -j$(nproc)',
            'sudo make install'
        ],
        module: {
            imports: ['galay.mcp'],
            build: [
                'cmake -S . -B build-mod -G Ninja \\',
                '  -DCMAKE_BUILD_TYPE=Release \\',
                '  -DBUILD_MODULE_EXAMPLES=ON',
                'cmake --build build-mod --target galay-mcp-modules -j'
            ],
            usage: [
                '#if defined(__cpp_modules) && __cpp_modules >= 201907L',
                'import galay.mcp;',
                '#else',
                '#include "galay-mcp/server/McpHttpServer.h"',
                '#endif',
                '',
                'using namespace galay::mcp;'
            ]
        }
    }
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getDocSlug() {
    const file = window.location.pathname.split('/').pop() || '';
    return file.replace(/\.html$/i, '');
}

function renderQuickstartCard(config) {
    const steps = [
        { number: '01', title: '安装依赖', text: config.deps },
        { number: '02', title: '克隆仓库', text: `获取 ${config.name} 源码` },
        { number: '03', title: '编译安装', text: config.install },
        { number: '04', title: '开始使用', text: config.usage }
    ];

    const stepsHtml = steps.map(step => `
        <li class="docs-quickstart-step">
            <span class="docs-quickstart-step-no">${escapeHtml(step.number)}</span>
            <div class="docs-quickstart-step-content">
                <h4>${escapeHtml(step.title)}</h4>
                <p>${escapeHtml(step.text)}</p>
            </div>
        </li>
    `).join('');

    const commands = Array.isArray(config.commands) ? config.commands.join('\n') : '';
    const module = config.module || null;
    const moduleImports = module && Array.isArray(module.imports) ? module.imports : [];
    const moduleBuild = module && Array.isArray(module.build) ? module.build.join('\n') : '';
    const moduleUsage = module && Array.isArray(module.usage) ? module.usage.join('\n') : '';
    const moduleImportsText = moduleImports.map(name => `import ${name};`).join(' / ');
    const moduleHtml = module ? `
            <div class="docs-module-section">
                <div class="docs-module-header">
                    <h3>C++23 模块（import/export）</h3>
                    <p>模块接口：<code>${escapeHtml(moduleImportsText)}</code>。建议使用 CMake 3.28+ 与 Ninja/Visual Studio 生成器，具体生效由工具链决定。</p>
                </div>
                <div class="docs-module-grid">
                    <article class="docs-module-code">
                        <h4>模块构建</h4>
                        <pre><code>${escapeHtml(moduleBuild)}</code></pre>
                    </article>
                    <article class="docs-module-code">
                        <h4>模块使用示例</h4>
                        <pre><code>${escapeHtml(moduleUsage)}</code></pre>
                    </article>
                </div>
            </div>
    ` : '';

    return `
        <section class="docs-quickstart-card" data-quickstart-injected="1">
            <h2 class="docs-quickstart-title">快速上手</h2>
            <div class="docs-quickstart-layout">
                <ol class="docs-quickstart-steps">
                    ${stepsHtml}
                </ol>
                <div class="docs-quickstart-code">
                    <pre><code>${escapeHtml(commands)}</code></pre>
                </div>
            </div>
            ${moduleHtml}
        </section>
    `;
}

function initDocQuickstart() {
    const slug = getDocSlug();
    const config = DOCS_QUICKSTART_MAP[slug];
    if (!config) return;

    const body = document.querySelector('.docs-article-body');
    if (!body || body.querySelector('[data-quickstart-injected="1"]')) return;

    body.insertAdjacentHTML('afterbegin', renderQuickstartCard(config));
}

document.addEventListener('DOMContentLoaded', initDocQuickstart);
