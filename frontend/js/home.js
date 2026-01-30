/* ============================================
   HOME PAGE - Specific JavaScript
   ============================================ */

// API 基础路径
const API_BASE = '/api';

// ============================================
// Typing Animation
// ============================================
const typingTexts = [
    'make -j$(nproc) && ./server',
    'echo "280K QPS achieved!"',
    'git clone galay-kernel',
    'cmake .. && make install',
    './benchmark --connections 1000'
];

let textIndex = 0;
let charIndex = 0;
let isDeleting = false;
let typingSpeed = 80;

function typeText() {
    const typingElement = document.getElementById('typingText');
    if (!typingElement) return;

    const currentText = typingTexts[textIndex];

    if (isDeleting) {
        typingElement.textContent = currentText.substring(0, charIndex - 1);
        charIndex--;
        typingSpeed = 40;
    } else {
        typingElement.textContent = currentText.substring(0, charIndex + 1);
        charIndex++;
        typingSpeed = 80;
    }

    if (!isDeleting && charIndex === currentText.length) {
        isDeleting = true;
        typingSpeed = 2000;
    } else if (isDeleting && charIndex === 0) {
        isDeleting = false;
        textIndex = (textIndex + 1) % typingTexts.length;
        typingSpeed = 500;
    }

    setTimeout(typeText, typingSpeed);
}

// ============================================
// Counter Animation
// ============================================
function animateCounters() {
    const counters = document.querySelectorAll('.stat-value[data-target]');

    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = 2000;
        const startTime = performance.now();

        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(easeOutQuart * target);

            if (target >= 1000) {
                counter.textContent = current.toLocaleString();
            } else {
                counter.textContent = current;
            }

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    requestAnimationFrame(updateCounter);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        observer.observe(counter);
    });
}

// ============================================
// Load Latest Posts from API
// ============================================
async function loadLatestPosts() {
    const container = document.getElementById('latestPosts');
    if (!container) return;

    // 显示加载状态
    container.innerHTML = `
        <div class="loading" style="grid-column: 1 / -1;">
            <div class="loading-spinner"></div>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/posts`);
        if (!response.ok) {
            throw new Error('Failed to fetch posts');
        }

        const posts = await response.json();

        // 只显示最新的 3 篇文章
        const latestPosts = posts.slice(0, 3);

        if (latestPosts.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <div class="empty-state-icon">📝</div>
                    <p class="empty-state-text">暂无文章</p>
                </div>
            `;
            return;
        }

        container.innerHTML = latestPosts.map(post => `
            <article class="post-card">
                <div class="post-card-content">
                    <div class="post-meta">
                        <span class="post-date">${post.date}</span>
                        <span class="post-category">${post.categoryName}</span>
                    </div>
                    <h3 class="post-title">${post.title}</h3>
                    <p class="post-excerpt">${post.excerpt}</p>
                    <a href="article.html?id=${post.id}" class="post-link">
                        阅读全文 <span>→</span>
                    </a>
                </div>
            </article>
        `).join('');

    } catch (error) {
        console.error('Error loading posts:', error);
        // 如果 API 失败，显示静态数据作为后备
        const fallbackPosts = [
            {
                id: 'galay-http-router',
                title: 'Galay-HTTP 路由系统设计与实现',
                excerpt: '深入解析 Galay-HTTP 的混合路由策略，如何实现 O(1) 精确匹配和 O(k) 模糊匹配的完美结合。',
                date: '2024-01-20',
                categoryName: '技术分享'
            },
            {
                id: 'cpp20-coroutine',
                title: 'C++20 协程在网络编程中的应用',
                excerpt: '探索如何使用 C++20 协程构建高性能异步网络库，从原理到实践的完整指南。',
                date: '2024-01-15',
                categoryName: '教程'
            },
            {
                id: 'benchmark-280k-qps',
                title: '如何达到 28 万 QPS：性能优化实战',
                excerpt: '分享 Galay-Kernel 性能优化的经验，包括零拷贝、内存池、事件驱动等关键技术。',
                date: '2024-01-10',
                categoryName: '性能优化'
            }
        ];

        container.innerHTML = fallbackPosts.map(post => `
            <article class="post-card">
                <div class="post-card-content">
                    <div class="post-meta">
                        <span class="post-date">${post.date}</span>
                        <span class="post-category">${post.categoryName}</span>
                    </div>
                    <h3 class="post-title">${post.title}</h3>
                    <p class="post-excerpt">${post.excerpt}</p>
                    <a href="article.html?id=${post.id}" class="post-link">
                        阅读全文 <span>→</span>
                    </a>
                </div>
            </article>
        `).join('');
    }
}

// ============================================
// Initialize Home Page
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    typeText();
    animateCounters();
    loadLatestPosts();
});
