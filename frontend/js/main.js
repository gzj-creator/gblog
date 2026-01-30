/* ============================================
   GALAY FRAMEWORK - Main JavaScript
   ============================================ */

// ============================================
// Cursor Glow Effect
// ============================================
function initCursorGlow() {
    const cursorGlow = document.getElementById('cursorGlow');
    if (!cursorGlow) return;

    let mouseX = 0, mouseY = 0;
    let glowX = 0, glowY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    function animateGlow() {
        glowX += (mouseX - glowX) * 0.1;
        glowY += (mouseY - glowY) * 0.1;

        cursorGlow.style.left = glowX + 'px';
        cursorGlow.style.top = glowY + 'px';

        requestAnimationFrame(animateGlow);
    }

    animateGlow();
}

// ============================================
// Mobile Menu
// ============================================
function initMobileMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('mobileMenu');

    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
        menu.classList.toggle('active');
        toggle.classList.toggle('active');
    });

    // Close menu when clicking a link
    menu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            menu.classList.remove('active');
            toggle.classList.remove('active');
        });
    });
}

// ============================================
// Smooth Scroll
// ============================================
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// ============================================
// Copy Code
// ============================================
function copyCode(button) {
    const codeBlock = button.closest('.code-window').querySelector('pre:not(.hidden) code');
    if (!codeBlock) return;

    const text = codeBlock.textContent;

    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = '已复制!';
        button.style.color = 'var(--accent-primary)';
        button.style.borderColor = 'var(--accent-primary)';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.color = '';
            button.style.borderColor = '';
        }, 2000);
    });
}

// ============================================
// Code Tabs
// ============================================
function initCodeTabs() {
    document.querySelectorAll('.code-tabs').forEach(tabContainer => {
        const tabs = tabContainer.querySelectorAll('.code-tab');
        const codeWindow = tabContainer.closest('.code-window');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Show corresponding code
                codeWindow.querySelectorAll('.code-content').forEach(content => {
                    content.classList.add('hidden');
                });

                const targetCode = codeWindow.querySelector(`#code${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`);
                if (targetCode) {
                    targetCode.classList.remove('hidden');
                }
            });
        });
    });
}

// ============================================
// Nav Scroll Effect
// ============================================
function initNavScroll() {
    const nav = document.querySelector('.nav');
    if (!nav) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.style.background = 'rgba(10, 10, 15, 0.95)';
        } else {
            nav.style.background = 'rgba(10, 10, 15, 0.85)';
        }
    });
}

// ============================================
// Scroll Animations
// ============================================
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll(
        '.project-card, .feature-card, .step, .post-card, .doc-card'
    );

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    animatedElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = `opacity 0.6s ease ${index * 0.05}s, transform 0.6s ease ${index * 0.05}s`;
        observer.observe(el);
    });
}

// ============================================
// Project Card Hover Effect
// ============================================
function initProjectCards() {
    const cards = document.querySelectorAll('.project-card');

    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const glow = card.querySelector('.project-card-glow');
            if (glow) {
                glow.style.background = `radial-gradient(circle at ${x}px ${y}px, var(--accent-subtle), transparent 60%)`;
            }
        });
    });
}

// ============================================
// Global Search Shortcut
// ============================================
function initGlobalSearch() {
    // Ctrl+K or Cmd+K to open search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            window.location.href = 'search.html';
        }
    });

    // Nav search button click
    const navSearch = document.querySelector('.nav-search');
    if (navSearch) {
        navSearch.addEventListener('click', () => {
            window.location.href = 'search.html';
        });
    }
}

// ============================================
// Add Search Button to Nav
// ============================================
function addNavSearchButton() {
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;

    // Check if search button already exists
    if (navLinks.querySelector('.nav-search')) return;

    // Create search button
    const searchBtn = document.createElement('button');
    searchBtn.className = 'nav-search';
    searchBtn.innerHTML = `
        <span class="nav-search-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
            </svg>
        </span>
        搜索
        <kbd>⌘K</kbd>
    `;

    // Insert before the last link (github)
    const githubLink = navLinks.querySelector('a[href*="github"]');
    if (githubLink) {
        navLinks.insertBefore(searchBtn, githubLink);
    } else {
        navLinks.appendChild(searchBtn);
    }
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initCursorGlow();
    initMobileMenu();
    initSmoothScroll();
    initCodeTabs();
    initNavScroll();
    initScrollAnimations();
    initProjectCards();
    addNavSearchButton();
    initGlobalSearch();
});

// Make copyCode available globally
window.copyCode = copyCode;
