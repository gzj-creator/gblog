/* ============================================
   PROJECTS PAGE - JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// 当前选中的项目
let currentProjectId = null;
let allProjects = [];

// 项目图标映射
const projectIcons = {
    'kernel': '⚡',
    'http': '🌐',
    'utils': '🛠️',
    'mcp': '🤖'
};

// 加载项目列表
async function loadProjects() {
    const container = document.getElementById('projectsGrid');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/projects`);
        if (!response.ok) {
            throw new Error('Failed to fetch projects');
        }

        allProjects = await response.json();
        renderProjects();

        // 检查 URL hash
        const hash = window.location.hash.slice(1);
        if (hash) {
            showProjectDetail(hash);
        }

    } catch (error) {
        console.error('Error loading projects:', error);
        // 使用静态数据作为后备
        allProjects = [
            {
                id: 'kernel',
                name: 'galay-kernel',
                description: '高性能 C++20 协程网络库，基于 kqueue/epoll/io_uring 实现异步 IO',
                language: 'C++20',
                license: 'MIT'
            },
            {
                id: 'http',
                name: 'galay-http',
                description: '现代化高性能异步 HTTP/WebSocket 库',
                language: 'C++20/23',
                license: 'MIT'
            },
            {
                id: 'utils',
                name: 'galay-utils',
                description: '现代化 C++20 工具库',
                language: 'C++20',
                license: 'MIT'
            },
            {
                id: 'mcp',
                name: 'galay-mcp',
                description: 'MCP (Model Context Protocol) 协议库，支持 AI 工具调用',
                language: 'C++23',
                license: 'MIT'
            }
        ];
        renderProjects();
    }
}

// 渲染项目列表
function renderProjects() {
    const container = document.getElementById('projectsGrid');
    if (!container) return;

    // 项目详细特性
    const projectFeatures = {
        'kernel': ['26-28万 QPS', '协程驱动', 'kqueue/epoll/io_uring', '跨平台'],
        'http': ['O(1) 路由匹配', '静态文件服务', 'Range 请求', 'WebSocket'],
        'utils': ['线程池', '一致性哈希', '熔断器', '负载均衡'],
        'mcp': ['JSON-RPC', '工具注册', '类型安全', '标准兼容']
    };

    container.innerHTML = allProjects.map(project => `
        <article class="project-card" id="card-${project.id}">
            <div class="project-card-header">
                <div class="project-card-icon">${projectIcons[project.id] || '📦'}</div>
                <div class="project-card-badges">
                    <span class="project-badge language">${project.language}</span>
                    <span class="project-badge">${project.license}</span>
                </div>
            </div>
            <h2 class="project-card-title">${project.name}</h2>
            <p class="project-card-description">${project.description}</p>
            <div class="project-features">
                <h3 class="project-features-title">核心特性</h3>
                <div class="project-features-list">
                    ${(projectFeatures[project.id] || []).map(f => `
                        <span class="project-feature-tag">${f}</span>
                    `).join('')}
                </div>
            </div>
            <div class="project-card-actions">
                <a href="#${project.id}" class="btn btn-primary" onclick="showProjectDetail('${project.id}'); return false;">
                    查看详情
                </a>
                <a href="https://github.com/galay/${project.name}" class="btn btn-secondary" target="_blank">
                    GitHub
                </a>
            </div>
        </article>
    `).join('');
}

// 显示项目详情
async function showProjectDetail(projectId) {
    const container = document.getElementById('projectDetail');
    if (!container) return;

    currentProjectId = projectId;
    window.location.hash = projectId;

    // 获取项目详情
    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}`);
        if (!response.ok) {
            throw new Error('Project not found');
        }

        const project = await response.json();
        renderProjectDetail(project);
        container.style.display = 'block';

        // 滚动到详情区域
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error loading project detail:', error);
        // 使用本地数据
        const project = allProjects.find(p => p.id === projectId);
        if (project) {
            renderProjectDetail(project);
            container.style.display = 'block';
            container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

// 渲染项目详情
function renderProjectDetail(project) {
    const container = document.getElementById('projectDetail');

    // 项目详细信息
    const projectDetails = {
        'kernel': {
            longDescription: 'galay-kernel 是整个 Galay 框架的核心，提供了基于 C++20 协程的高性能异步 IO 运行时。它支持 macOS 的 kqueue、Linux 的 epoll 和 io_uring，能够在单线程下达到 26-28 万 QPS 的极致性能。',
            features: [
                { icon: '⚡', text: '极致性能：单线程 26-28 万 QPS，130+ MB/s 吞吐量' },
                { icon: '🔄', text: '协程驱动：基于 C++20 标准协程，代码简洁直观' },
                { icon: '🌍', text: '跨平台：支持 macOS (kqueue) 和 Linux (epoll/io_uring)' },
                { icon: '📁', text: '异步文件 IO：支持异步文件读写操作' }
            ],
            stats: {
                'QPS': '280,000+',
                '吞吐量': '130+ MB/s',
                '延迟 P99': '< 1ms'
            }
        },
        'http': {
            longDescription: 'galay-http 是构建于 galay-kernel 之上的 HTTP/WebSocket 协议库。它提供了高性能的路由系统、静态文件服务、Range 请求支持、ETag 缓存等功能，是构建现代 Web 服务的理想选择。',
            features: [
                { icon: '🚀', text: '高性能路由：O(1) 精确匹配 + O(k) 模糊匹配' },
                { icon: '📦', text: '静态文件服务：支持 MEMORY/CHUNK/SENDFILE/AUTO 四种传输模式' },
                { icon: '📊', text: 'Range 请求：支持断点续传和分片下载' },
                { icon: '🔌', text: 'WebSocket：完整实现 RFC 6455 标准' }
            ],
            stats: {
                '路由匹配': 'O(1)',
                '传输模式': '4 种',
                'HTTP 版本': '1.1'
            }
        },
        'utils': {
            longDescription: 'galay-utils 是一个纯头文件的 C++20 工具库，提供了构建高性能应用所需的各种实用组件，包括线程池、一致性哈希、熔断器、负载均衡等。',
            features: [
                { icon: '🧵', text: '线程池：高效的任务调度和执行' },
                { icon: '#️⃣', text: '一致性哈希：支持虚拟节点的分布式哈希' },
                { icon: '🔒', text: '熔断器：服务保护和故障隔离' },
                { icon: '⚖️', text: '负载均衡：多种负载均衡策略' }
            ],
            stats: {
                '类型': '纯头文件',
                '依赖': '无外部依赖',
                '标准': 'C++20'
            }
        },
        'mcp': {
            longDescription: 'galay-mcp 实现了 Anthropic 的 Model Context Protocol (MCP) 协议，让 C++ 应用能够与 AI 模型进行工具调用交互。它提供了简洁的 API 来注册和调用工具。',
            features: [
                { icon: '📡', text: 'JSON-RPC 通信：标准的 JSON-RPC 2.0 协议' },
                { icon: '🔧', text: '工具注册 API：简洁的工具定义和注册接口' },
                { icon: '🛡️', text: '类型安全：编译时类型检查' },
                { icon: '📋', text: '标准兼容：完全兼容 MCP 规范' }
            ],
            stats: {
                '协议': 'MCP',
                '通信': 'JSON-RPC 2.0',
                '标准': 'C++23'
            }
        }
    };

    const details = projectDetails[project.id] || {
        longDescription: project.description,
        features: [],
        stats: {}
    };

    container.innerHTML = `
        <div class="project-detail-header">
            <div class="project-detail-info">
                <h1 class="project-detail-title">${project.name}</h1>
                <p class="project-detail-description">${details.longDescription}</p>
            </div>
            <button class="project-detail-close" onclick="hideProjectDetail()">&times;</button>
        </div>
        <div class="project-detail-body">
            <div class="project-detail-content">
                <h2>核心特性</h2>
                <div class="project-detail-features">
                    ${details.features.map(f => `
                        <div class="project-detail-feature">
                            <span class="project-detail-feature-icon">${f.icon}</span>
                            <span class="project-detail-feature-text">${f.text}</span>
                        </div>
                    `).join('')}
                </div>

                ${project.id === 'kernel' ? `
                    <h2>架构图</h2>
                    <div class="architecture-diagram">
                        <div class="architecture-layers">
                            <div class="architecture-layer">Application Layer</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer highlight">galay-kernel (Coroutine Runtime)</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer">kqueue / epoll / io_uring</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer">Operating System</div>
                        </div>
                    </div>
                ` : ''}

                ${project.id === 'http' ? `
                    <h2>架构图</h2>
                    <div class="architecture-diagram">
                        <div class="architecture-layers">
                            <div class="architecture-layer">Your Application</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer highlight">galay-http (HTTP/WebSocket)</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer">galay-kernel (Async IO)</div>
                            <div class="architecture-arrow">↓</div>
                            <div class="architecture-layer">Operating System</div>
                        </div>
                    </div>
                ` : ''}
            </div>
            <div class="project-detail-sidebar">
                <div class="project-sidebar-section">
                    <h3 class="project-sidebar-title">项目信息</h3>
                    <div class="project-sidebar-item">
                        <span class="project-sidebar-label">语言</span>
                        <span class="project-sidebar-value">${project.language}</span>
                    </div>
                    <div class="project-sidebar-item">
                        <span class="project-sidebar-label">许可证</span>
                        <span class="project-sidebar-value">${project.license}</span>
                    </div>
                    ${Object.entries(details.stats).map(([key, value]) => `
                        <div class="project-sidebar-item">
                            <span class="project-sidebar-label">${key}</span>
                            <span class="project-sidebar-value">${value}</span>
                        </div>
                    `).join('')}
                </div>
                <div class="project-sidebar-section">
                    <h3 class="project-sidebar-title">快速链接</h3>
                    <div class="project-sidebar-actions">
                        <a href="https://github.com/galay/${project.name}" class="btn btn-primary" target="_blank">
                            GitHub 仓库
                        </a>
                        <a href="docs.html" class="btn btn-secondary">
                            查看文档
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 隐藏项目详情
function hideProjectDetail() {
    const container = document.getElementById('projectDetail');
    if (container) {
        container.style.display = 'none';
    }
    currentProjectId = null;
    window.location.hash = '';
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();

    // 监听 hash 变化
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.slice(1);
        if (hash) {
            showProjectDetail(hash);
        } else {
            hideProjectDetail();
        }
    });
});

// 全局函数
window.showProjectDetail = showProjectDetail;
window.hideProjectDetail = hideProjectDetail;
