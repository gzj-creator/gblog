/* ============================================
   SEARCH - JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// 搜索状态
let currentFilter = 'all';
let searchTimeout = null;
let allData = {
    docs: [],
    posts: [],
    projects: []
};

// 最近搜索存储 key
const RECENT_SEARCHES_KEY = 'galay_recent_searches';
const MAX_RECENT_SEARCHES = 5;

// ============================================
// 数据加载
// ============================================

async function loadAllData() {
    try {
        // 并行加载所有数据
        const [docsRes, postsRes, projectsRes] = await Promise.all([
            fetch(`${API_BASE}/docs`).catch(() => ({ ok: false })),
            fetch(`${API_BASE}/posts`).catch(() => ({ ok: false })),
            fetch(`${API_BASE}/projects`).catch(() => ({ ok: false }))
        ]);

        if (docsRes.ok) {
            allData.docs = await docsRes.json();
        } else {
            // 使用静态数据
            allData.docs = [
                { id: 'quick-start', title: '快速开始', description: '5 分钟内搭建你的第一个 Galay 应用', category: 'getting-started' },
                { id: 'installation', title: '安装指南', description: '详细的安装和配置说明', category: 'getting-started' },
                { id: 'http-server', title: 'HTTP 服务器', description: '使用 HttpServer 创建 Web 服务', category: 'guide' },
                { id: 'http-router', title: '路由系统', description: 'HttpRouter 的使用方法和路由匹配规则', category: 'guide' },
                { id: 'websocket', title: 'WebSocket', description: 'WebSocket 服务器和客户端的使用', category: 'guide' },
                { id: 'coroutine', title: '协程基础', description: 'C++20 协程在 Galay 中的应用', category: 'advanced' },
                { id: 'performance', title: '性能优化', description: '性能调优和最佳实践', category: 'advanced' }
            ];
        }

        if (postsRes.ok) {
            allData.posts = await postsRes.json();
        } else {
            allData.posts = [
                { id: 'galay-http-router', title: 'Galay-HTTP 路由系统设计与实现', excerpt: '深入解析 Galay-HTTP 的混合路由策略', date: '2024-01-20', category: 'tech' },
                { id: 'cpp20-coroutine', title: 'C++20 协程在网络编程中的应用', excerpt: '探索如何使用 C++20 协程构建高性能异步网络库', date: '2024-01-15', category: 'tutorial' },
                { id: 'benchmark-280k-qps', title: '如何达到 28 万 QPS：性能优化实战', excerpt: '分享 Galay-Kernel 性能优化的经验', date: '2024-01-10', category: 'performance' }
            ];
        }

        if (projectsRes.ok) {
            allData.projects = await projectsRes.json();
        } else {
            allData.projects = [
                { id: 'kernel', name: 'galay-kernel', description: '高性能 C++20 协程网络库' },
                { id: 'http', name: 'galay-http', description: '现代化高性能异步 HTTP/WebSocket 库' },
                { id: 'utils', name: 'galay-utils', description: '现代化 C++20 工具库' },
                { id: 'mcp', name: 'galay-mcp', description: 'MCP (Model Context Protocol) 协议库' }
            ];
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// ============================================
// 搜索功能
// ============================================

function search(query) {
    if (!query || query.trim().length < 2) {
        showEmptyState();
        return;
    }

    query = query.trim().toLowerCase();
    const results = [];

    // 搜索文档
    if (currentFilter === 'all' || currentFilter === 'docs') {
        allData.docs.forEach(doc => {
            const titleMatch = doc.title.toLowerCase().includes(query);
            const descMatch = doc.description.toLowerCase().includes(query);
            if (titleMatch || descMatch) {
                results.push({
                    type: 'docs',
                    typeName: '文档',
                    id: doc.id,
                    title: doc.title,
                    excerpt: doc.description,
                    url: `docs.html#${doc.id}`,
                    score: titleMatch ? 2 : 1
                });
            }
        });
    }

    // 搜索博客
    if (currentFilter === 'all' || currentFilter === 'blog') {
        allData.posts.forEach(post => {
            const titleMatch = post.title.toLowerCase().includes(query);
            const excerptMatch = post.excerpt.toLowerCase().includes(query);
            if (titleMatch || excerptMatch) {
                results.push({
                    type: 'blog',
                    typeName: '博客',
                    id: post.id,
                    title: post.title,
                    excerpt: post.excerpt,
                    url: `article.html?id=${post.id}`,
                    meta: post.date,
                    score: titleMatch ? 2 : 1
                });
            }
        });
    }

    // 搜索项目
    if (currentFilter === 'all' || currentFilter === 'projects') {
        allData.projects.forEach(project => {
            const nameMatch = project.name.toLowerCase().includes(query);
            const descMatch = project.description.toLowerCase().includes(query);
            if (nameMatch || descMatch) {
                results.push({
                    type: 'projects',
                    typeName: '项目',
                    id: project.id,
                    title: project.name,
                    excerpt: project.description,
                    url: `projects.html#${project.id}`,
                    score: nameMatch ? 2 : 1
                });
            }
        });
    }

    // 按相关度排序
    results.sort((a, b) => b.score - a.score);

    renderResults(results, query);

    // 保存到最近搜索
    saveRecentSearch(query);
}

// ============================================
// 渲染结果
// ============================================

function renderResults(results, query) {
    const container = document.getElementById('searchResults');
    if (!container) return;

    if (results.length === 0) {
        container.innerHTML = `
            <div class="search-no-results">
                <div class="search-no-results-icon">🔍</div>
                <h3>未找到相关结果</h3>
                <p>尝试使用其他关键词，或浏览以下热门主题</p>
                <div class="search-suggestions">
                    <button class="search-suggestion" onclick="setSearchQuery('HTTP')">HTTP</button>
                    <button class="search-suggestion" onclick="setSearchQuery('协程')">协程</button>
                    <button class="search-suggestion" onclick="setSearchQuery('路由')">路由</button>
                    <button class="search-suggestion" onclick="setSearchQuery('性能')">性能</button>
                </div>
            </div>
        `;
        return;
    }

    let html = `
        <div class="search-stats">
            找到 <strong>${results.length}</strong> 个相关结果
        </div>
    `;

    results.forEach(result => {
        const highlightedTitle = highlightText(result.title, query);
        const highlightedExcerpt = highlightText(result.excerpt, query);

        html += `
            <a href="${result.url}" class="search-result">
                <div class="search-result-header">
                    <span class="search-result-type">${result.typeName}</span>
                </div>
                <h3 class="search-result-title">${highlightedTitle}</h3>
                <p class="search-result-excerpt">${highlightedExcerpt}</p>
                ${result.meta ? `<div class="search-result-meta"><span>${result.meta}</span></div>` : ''}
            </a>
        `;
    });

    container.innerHTML = html;

    // 隐藏最近搜索和热门主题
    const recentEl = document.getElementById('recentSearches');
    const popularEl = document.querySelector('.popular-topics');
    if (recentEl) recentEl.style.display = 'none';
    if (popularEl) popularEl.style.display = 'none';
}

function showEmptyState() {
    const container = document.getElementById('searchResults');
    if (!container) return;

    container.innerHTML = `
        <div class="search-empty">
            <div class="search-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                </svg>
            </div>
            <h3>输入关键词开始搜索</h3>
            <p>搜索文档、博客文章和项目信息</p>
        </div>
    `;

    // 显示最近搜索和热门主题
    const recentEl = document.getElementById('recentSearches');
    const popularEl = document.querySelector('.popular-topics');
    if (recentEl) recentEl.style.display = 'block';
    if (popularEl) popularEl.style.display = 'block';
}

function highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============================================
// 最近搜索
// ============================================

function getRecentSearches() {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
    return stored ? JSON.parse(stored) : [];
}

function saveRecentSearch(query) {
    let recent = getRecentSearches();

    // 移除重复项
    recent = recent.filter(q => q.toLowerCase() !== query.toLowerCase());

    // 添加到开头
    recent.unshift(query);

    // 限制数量
    recent = recent.slice(0, MAX_RECENT_SEARCHES);

    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recent));
    renderRecentSearches();
}

function removeRecentSearch(query) {
    let recent = getRecentSearches();
    recent = recent.filter(q => q !== query);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recent));
    renderRecentSearches();
}

function renderRecentSearches() {
    const container = document.getElementById('recentList');
    const wrapper = document.getElementById('recentSearches');
    if (!container || !wrapper) return;

    const recent = getRecentSearches();

    if (recent.length === 0) {
        wrapper.style.display = 'none';
        return;
    }

    wrapper.style.display = 'block';

    container.innerHTML = recent.map(query => `
        <div class="recent-item" onclick="setSearchQuery('${escapeHtml(query)}')">
            <span class="recent-item-text">
                <svg class="recent-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="12 8 12 12 14 14"/>
                    <circle cx="12" cy="12" r="10"/>
                </svg>
                ${escapeHtml(query)}
            </span>
            <button class="recent-item-remove" onclick="event.stopPropagation(); removeRecentSearch('${escapeHtml(query)}')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// 辅助函数
// ============================================

function setSearchQuery(query) {
    const input = document.getElementById('searchInput');
    if (input) {
        input.value = query;
        input.focus();
        search(query);
    }
}

// ============================================
// 初始化
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    // 加载数据
    await loadAllData();

    // 搜索输入
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // 检查 URL 参数
        const params = new URLSearchParams(window.location.search);
        const q = params.get('q');
        if (q) {
            searchInput.value = q;
            search(q);
        }

        // 输入事件（防抖）
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                search(e.target.value);
            }, 300);
        });

        // 回车搜索
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(searchTimeout);
                search(searchInput.value);
            }
        });
    }

    // 过滤器按钮
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;

            const input = document.getElementById('searchInput');
            if (input && input.value) {
                search(input.value);
            }
        });
    });

    // 热门标签
    document.querySelectorAll('.popular-tag').forEach(tag => {
        tag.addEventListener('click', (e) => {
            e.preventDefault();
            setSearchQuery(tag.dataset.query);
        });
    });

    // 渲染最近搜索
    renderRecentSearches();

    // 全局快捷键 Ctrl+K
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const input = document.getElementById('searchInput');
            if (input) {
                input.focus();
                input.select();
            }
        }
    });
});

// 全局函数
window.setSearchQuery = setSearchQuery;
window.removeRecentSearch = removeRecentSearch;
