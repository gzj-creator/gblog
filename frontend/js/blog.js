/* ============================================
   BLOG PAGE - JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// 当前状态
let currentCategory = 'all';
let currentPage = 1;
let postsPerPage = 5;
let allPosts = [];
let isLoading = false;

// 加载文章列表
async function loadPosts() {
    if (isLoading) return;
    isLoading = true;

    const container = document.getElementById('blogPosts');
    if (!container) return;

    // 显示加载状态
    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/posts`);
        if (!response.ok) {
            throw new Error('Failed to fetch posts');
        }

        allPosts = await response.json();
        renderPosts();
    } catch (error) {
        console.error('Error loading posts:', error);
        container.innerHTML = `
            <div class="blog-empty">
                <div class="blog-empty-icon">⚠️</div>
                <h3>加载失败</h3>
                <p>无法加载文章列表，请稍后重试</p>
                <button class="btn btn-secondary" onclick="loadPosts()" style="margin-top: var(--space-lg);">
                    重新加载
                </button>
            </div>
        `;
    } finally {
        isLoading = false;
    }
}

// 渲染文章列表
function renderPosts() {
    const container = document.getElementById('blogPosts');
    if (!container) return;

    // 过滤文章
    let filteredPosts = allPosts;
    if (currentCategory !== 'all') {
        filteredPosts = allPosts.filter(post => post.category === currentCategory);
    }

    // 分页
    const startIndex = (currentPage - 1) * postsPerPage;
    const endIndex = startIndex + postsPerPage;
    const pagePosts = filteredPosts.slice(startIndex, endIndex);

    if (pagePosts.length === 0) {
        container.innerHTML = `
            <div class="blog-empty">
                <div class="blog-empty-icon">📝</div>
                <h3>暂无文章</h3>
                <p>该分类下还没有文章</p>
            </div>
        `;
        renderPagination(0);
        return;
    }

    // 渲染文章
    let html = '';

    // 如果是第一页且显示全部，显示置顶文章
    if (currentPage === 1 && currentCategory === 'all') {
        const featuredPost = pagePosts.find(p => p.featured);
        if (featuredPost) {
            html += `
                <article class="featured-post">
                    <span class="featured-label">置顶推荐</span>
                    <h2><a href="article.html?id=${featuredPost.id}">${featuredPost.title}</a></h2>
                    <div class="post-meta">
                        <span class="blog-post-date">${featuredPost.date}</span>
                        <span class="blog-post-category">${featuredPost.categoryName}</span>
                        <span class="blog-post-reading-time">${featuredPost.readingTime}</span>
                    </div>
                    <p class="blog-post-excerpt">${featuredPost.excerpt}</p>
                    <div class="blog-post-tags">
                        ${(featuredPost.tags || []).map(tag => `<span class="blog-post-tag">#${tag}</span>`).join('')}
                    </div>
                </article>
            `;
        }
    }

    // 渲染普通文章
    pagePosts.filter(p => !(currentPage === 1 && currentCategory === 'all' && p.featured)).forEach(post => {
        html += `
            <article class="blog-post" data-category="${post.category}">
                <div class="blog-post-meta">
                    <span class="blog-post-date">${post.date}</span>
                    <span class="blog-post-category">${post.categoryName}</span>
                    <span class="blog-post-reading-time">${post.readingTime || '5 分钟'}</span>
                </div>
                <div class="blog-post-content">
                    <h2><a href="article.html?id=${post.id}">${post.title}</a></h2>
                    <p class="blog-post-excerpt">${post.excerpt}</p>
                    <div class="blog-post-tags">
                        ${(post.tags || []).map(tag => `<span class="blog-post-tag">#${tag}</span>`).join('')}
                    </div>
                </div>
            </article>
        `;
    });

    container.innerHTML = html;

    // 渲染分页
    renderPagination(filteredPosts.length);
}

// 渲染分页
function renderPagination(totalPosts) {
    const container = document.getElementById('blogPagination');
    if (!container) return;

    const totalPages = Math.ceil(totalPosts / postsPerPage);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    // 上一页
    html += `<button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">←</button>`;

    // 页码
    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
    }

    // 下一页
    html += `<button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">→</button>`;

    container.innerHTML = html;
}

// 切换分类
function changeCategory(category) {
    currentCategory = category;
    currentPage = 1;

    // 更新按钮状态
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });

    renderPosts();
}

// 切换页码
function changePage(page) {
    currentPage = page;
    renderPosts();

    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 绑定分类按钮事件
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            changeCategory(btn.dataset.category);
        });
    });

    // 加载文章
    loadPosts();
});

// 全局函数
window.changePage = changePage;
window.loadPosts = loadPosts;
