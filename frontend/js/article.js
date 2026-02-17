/* ============================================
   ARTICLE PAGE - JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// 获取 URL 参数
function getUrlParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// 加载文章
async function loadArticle() {
    const container = document.getElementById('articleContent');
    if (!container) return;

    const articleId = getUrlParam('id');

    if (!articleId) {
        showError('未指定文章 ID');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/posts/${articleId}`);

        if (!response.ok) {
            if (response.status === 404) {
                showError('文章不存在');
            } else {
                throw new Error('Failed to fetch article');
            }
            return;
        }

        const article = await response.json();
        renderArticle(article);

        // 更新页面标题
        document.title = `${article.title} | Galay Framework`;

    } catch (error) {
        console.error('Error loading article:', error);
        showError('加载文章失败，请稍后重试');
    }
}

// 渲染文章
function renderArticle(article) {
    const container = document.getElementById('articleContent');

    // 生成文章内容（如果后端没有提供完整内容，使用摘要）
    const content = article.content || generatePlaceholderContent(article);

    container.innerHTML = `
        <header class="article-header">
            <span class="article-category">${article.categoryName}</span>
            <h1 class="article-title">${article.title}</h1>
            <div class="article-meta">
                <span class="article-meta-item">
                    <span class="article-meta-icon">📅</span>
                    ${article.date}
                </span>
                <span class="article-meta-item">
                    <span class="article-meta-icon">⏱️</span>
                    ${article.readingTime || '5 分钟'}
                </span>
            </div>
            <div class="article-tags">
                ${(article.tags || []).map(tag => `<span class="article-tag">#${tag}</span>`).join('')}
            </div>
        </header>
        <div class="article-body">
            ${content}
        </div>
    `;
}

// 生成占位内容
function generatePlaceholderContent(article) {
    return `
        <p>${article.excerpt}</p>

        <h2>概述</h2>
        <p>本文将深入探讨 ${article.title} 的相关内容。作为 Galay 框架系列文章的一部分，我们将从原理到实践，全面解析这一主题。</p>

        <blockquote>
            <p>Galay 框架致力于提供高性能、易用的 C++23 异步编程解决方案。</p>
        </blockquote>

        <h2>核心要点</h2>
        <ul>
            <li>深入理解底层实现原理</li>
            <li>掌握最佳实践和使用技巧</li>
            <li>了解性能优化策略</li>
            <li>探索实际应用场景</li>
        </ul>

        <h2>技术细节</h2>
        <p>在实现过程中，我们采用了多种先进的技术手段来确保系统的高性能和可靠性。以下是一个简单的代码示例：</p>

        <pre><code>// 示例代码
#include "galay-http/kernel/http/HttpServer.h"

int main() {
    HttpServer server;
    server.start();
    return 0;
}</code></pre>

        <h2>总结</h2>
        <p>通过本文的介绍，相信你已经对 ${article.title.replace(/[<>]/g, '')} 有了更深入的理解。如果你有任何问题或建议，欢迎在 GitHub 上提出 Issue 或参与讨论。</p>

        <hr>

        <p><em>本文是 Galay 框架技术博客系列的一部分。更多精彩内容，请关注我们的 <a href="blog.html">博客</a> 和 <a href="https://github.com/gzj-creator" target="_blank">GitHub</a>。</em></p>
    `;
}

// 显示错误
function showError(message) {
    const container = document.getElementById('articleContent');
    container.innerHTML = `
        <div class="article-empty">
            <div class="article-empty-icon">📄</div>
            <h2>${message}</h2>
            <p>请检查链接是否正确，或返回博客列表查看其他文章</p>
            <a href="blog.html" class="btn btn-primary">返回博客列表</a>
        </div>
    `;
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadArticle();
});
