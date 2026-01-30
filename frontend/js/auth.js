/* ============================================
   AUTH - JavaScript
   ============================================ */

// API 配置
const AUTH_API = '/api/auth';

// 存储 key
const TOKEN_KEY = 'galay_access_token';
const REFRESH_TOKEN_KEY = 'galay_refresh_token';
const USER_KEY = 'galay_user';

// ============================================
// Token 管理
// ============================================

function saveTokens(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
}

function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function saveUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
}

function isLoggedIn() {
    return !!getAccessToken();
}

// ============================================
// API 请求
// ============================================

async function authFetch(url, options = {}) {
    const token = getAccessToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    // 如果 token 过期，尝试刷新
    if (response.status === 401 && getRefreshToken()) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${getAccessToken()}`;
            return fetch(url, { ...options, headers });
        }
    }

    return response;
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${AUTH_API}/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            clearTokens();
            return false;
        }

        const data = await response.json();
        if (data.success && data.data.access_token) {
            localStorage.setItem(TOKEN_KEY, data.data.access_token);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }

    clearTokens();
    return false;
}

// ============================================
// 登录
// ============================================

async function login(username, password) {
    const response = await fetch(`${AUTH_API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (data.success) {
        saveTokens(data.data.access_token, data.data.refresh_token);
        saveUser(data.data.user);
        return { success: true, user: data.data.user };
    }

    return {
        success: false,
        error: data.error?.message || '登录失败'
    };
}

// ============================================
// 注册
// ============================================

async function register(username, password, email) {
    const response = await fetch(`${AUTH_API}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email })
    });

    const data = await response.json();

    if (data.success) {
        return { success: true, user: data.data };
    }

    return {
        success: false,
        error: data.error?.message || '注册失败'
    };
}

// ============================================
// 登出
// ============================================

async function logout() {
    const token = getAccessToken();
    if (token) {
        try {
            await fetch(`${AUTH_API}/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    clearTokens();
    window.location.href = 'index.html';
}

// ============================================
// 获取当前用户
// ============================================

async function getCurrentUser() {
    const response = await authFetch(`${AUTH_API}/me`);

    if (!response.ok) {
        return null;
    }

    const data = await response.json();
    if (data.success) {
        saveUser(data.data);
        return data.data;
    }

    return null;
}

// ============================================
// 密码强度检测
// ============================================

function checkPasswordStrength(password) {
    let strength = 0;

    if (password.length >= 6) strength++;
    if (password.length >= 10) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    return Math.min(strength, 4);
}

function updatePasswordStrength(password) {
    const strengthEl = document.getElementById('passwordStrength');
    if (!strengthEl) return;

    const strength = checkPasswordStrength(password);
    const segments = strengthEl.querySelectorAll('.strength-segment');
    const textEl = strengthEl.querySelector('.strength-text');

    const levels = ['', 'weak', 'fair', 'good', 'strong'];
    const texts = ['密码强度', '弱', '一般', '良好', '强'];

    segments.forEach((seg, i) => {
        seg.className = 'strength-segment';
        if (i < strength) {
            seg.classList.add(levels[strength]);
        }
    });

    if (textEl) {
        textEl.textContent = texts[strength];
        textEl.style.color = strength >= 3 ? 'var(--accent-primary)' : '';
    }
}

// ============================================
// 切换密码显示
// ============================================

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const wrapper = input.closest('.form-input-wrapper');
    const eyeOpen = wrapper.querySelector('.eye-open');
    const eyeClosed = wrapper.querySelector('.eye-closed');

    if (input.type === 'password') {
        input.type = 'text';
        eyeOpen.classList.add('hidden');
        eyeClosed.classList.remove('hidden');
    } else {
        input.type = 'password';
        eyeOpen.classList.remove('hidden');
        eyeClosed.classList.add('hidden');
    }
}

// ============================================
// 表单处理
// ============================================

function showError(formId, message) {
    const errorEl = document.getElementById(formId + 'Error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
}

function hideError(formId) {
    const errorEl = document.getElementById(formId + 'Error');
    if (errorEl) {
        errorEl.classList.add('hidden');
    }
}

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    const textEl = btn.querySelector('.btn-text');
    const loadingEl = btn.querySelector('.btn-loading');

    if (loading) {
        btn.disabled = true;
        textEl?.classList.add('hidden');
        loadingEl?.classList.remove('hidden');
    } else {
        btn.disabled = false;
        textEl?.classList.remove('hidden');
        loadingEl?.classList.add('hidden');
    }
}

// ============================================
// 初始化登录表单
// ============================================

function initLoginForm() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    // 如果已登录，跳转到首页
    if (isLoggedIn()) {
        window.location.href = 'index.html';
        return;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError('login');

        const username = form.username.value.trim();
        const password = form.password.value;

        if (!username || !password) {
            showError('login', '请填写用户名和密码');
            return;
        }

        setLoading('loginBtn', true);

        try {
            const result = await login(username, password);

            if (result.success) {
                // 登录成功，跳转
                const redirect = new URLSearchParams(window.location.search).get('redirect') || 'index.html';
                window.location.href = redirect;
            } else {
                showError('login', result.error);
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('login', '网络错误，请稍后重试');
        } finally {
            setLoading('loginBtn', false);
        }
    });
}

// ============================================
// 初始化注册表单
// ============================================

function initRegisterForm() {
    const form = document.getElementById('registerForm');
    if (!form) return;

    // 如果已登录，跳转到首页
    if (isLoggedIn()) {
        window.location.href = 'index.html';
        return;
    }

    // 密码强度检测
    const passwordInput = form.password;
    if (passwordInput) {
        passwordInput.addEventListener('input', () => {
            updatePasswordStrength(passwordInput.value);
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError('register');

        const username = form.username.value.trim();
        const email = form.email.value.trim();
        const password = form.password.value;
        const confirmPassword = form.confirmPassword.value;
        const agree = form.agree.checked;

        // 验证
        if (!username || !password) {
            showError('register', '请填写用户名和密码');
            return;
        }

        if (username.length < 3 || username.length > 20) {
            showError('register', '用户名长度应为 3-20 个字符');
            return;
        }

        if (password.length < 6) {
            showError('register', '密码长度至少 6 位');
            return;
        }

        if (password !== confirmPassword) {
            showError('register', '两次输入的密码不一致');
            return;
        }

        if (!agree) {
            showError('register', '请阅读并同意服务条款');
            return;
        }

        setLoading('registerBtn', true);

        try {
            const result = await register(username, password, email);

            if (result.success) {
                // 注册成功，跳转到登录页
                window.location.href = 'login.html?registered=1';
            } else {
                showError('register', result.error);
            }
        } catch (error) {
            console.error('Register error:', error);
            showError('register', '网络错误，请稍后重试');
        } finally {
            setLoading('registerBtn', false);
        }
    });
}

// ============================================
// 更新导航栏用户状态
// ============================================

function updateNavUserState() {
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;

    // 移除已有的用户菜单或登录链接
    const existingUserMenu = navLinks.querySelector('.user-menu');
    const existingLoginLink = navLinks.querySelector('.nav-link-login');
    if (existingUserMenu) existingUserMenu.remove();
    if (existingLoginLink) existingLoginLink.remove();

    if (isLoggedIn()) {
        const user = getUser();
        const initial = user?.username?.charAt(0) || 'U';

        const userMenu = document.createElement('div');
        userMenu.className = 'user-menu';
        userMenu.innerHTML = `
            <div class="user-avatar">
                <span class="user-avatar-text">${initial}</span>
            </div>
            <div class="user-dropdown">
                <div class="user-dropdown-header">
                    <div class="user-dropdown-name">${user?.username || '用户'}</div>
                    <div class="user-dropdown-email">${user?.email || ''}</div>
                </div>
                <a href="profile.html" class="user-dropdown-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    个人中心
                </a>
                <a href="#" class="user-dropdown-item danger" onclick="logout(); return false;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                        <polyline points="16 17 21 12 16 7"/>
                        <line x1="21" y1="12" x2="9" y2="12"/>
                    </svg>
                    退出登录
                </a>
            </div>
        `;
        navLinks.appendChild(userMenu);
    } else {
        const loginLink = document.createElement('a');
        loginLink.href = 'login.html';
        loginLink.className = 'nav-link nav-link-login';
        loginLink.innerHTML = '<span class="nav-link-prefix">~/</span>login';
        navLinks.appendChild(loginLink);
    }
}

// ============================================
// 初始化
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initLoginForm();
    initRegisterForm();
    updateNavUserState();

    // 检查是否刚注册成功
    const params = new URLSearchParams(window.location.search);
    if (params.get('registered') === '1') {
        const form = document.getElementById('loginForm');
        if (form) {
            const successEl = document.createElement('div');
            successEl.className = 'form-success';
            successEl.textContent = '注册成功！请登录';
            form.insertBefore(successEl, form.firstChild);
        }
    }
});

// 全局函数
window.togglePassword = togglePassword;
window.logout = logout;
window.isLoggedIn = isLoggedIn;
window.getUser = getUser;
window.authFetch = authFetch;
