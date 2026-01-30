/* ============================================
   PROFILE PAGE - JavaScript
   ============================================ */

// ============================================
// 初始化
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    // 检查登录状态
    if (!isLoggedIn()) {
        window.location.href = 'login.html?redirect=profile.html';
        return;
    }

    // 加载用户信息
    await loadUserProfile();

    // 初始化标签页
    initTabs();

    // 初始化表单
    initProfileForm();
    initPasswordForm();
    initNotificationsForm();
});

// ============================================
// 加载用户信息
// ============================================

async function loadUserProfile() {
    const user = getUser();

    if (user) {
        updateProfileUI(user);
    }

    // 从服务器获取最新信息
    try {
        const freshUser = await getCurrentUser();
        if (freshUser) {
            updateProfileUI(freshUser);
        }
    } catch (error) {
        console.error('Failed to load user profile:', error);
    }
}

function updateProfileUI(user) {
    // 头像
    const avatarEl = document.getElementById('profileAvatar');
    if (avatarEl) {
        const initial = user.username?.charAt(0) || 'U';
        avatarEl.querySelector('.profile-avatar-text').textContent = initial.toUpperCase();
    }

    // 名称和邮箱
    const nameEl = document.getElementById('profileName');
    const emailEl = document.getElementById('profileEmail');
    if (nameEl) nameEl.textContent = user.display_name || user.username || '用户';
    if (emailEl) emailEl.textContent = user.email || '';

    // 表单字段
    const usernameInput = document.getElementById('username');
    const displayNameInput = document.getElementById('displayName');
    const emailInput = document.getElementById('email');
    const bioInput = document.getElementById('bio');
    const websiteInput = document.getElementById('website');
    const githubInput = document.getElementById('github');

    if (usernameInput) usernameInput.value = user.username || '';
    if (displayNameInput) displayNameInput.value = user.display_name || '';
    if (emailInput) emailInput.value = user.email || '';
    if (bioInput) bioInput.value = user.bio || '';
    if (websiteInput) websiteInput.value = user.website || '';
    if (githubInput) githubInput.value = user.github || '';
}

// ============================================
// 标签页切换
// ============================================

function initTabs() {
    const navItems = document.querySelectorAll('.profile-nav-item[data-tab]');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.dataset.tab;
            switchTab(tabId);

            // 更新 URL hash
            window.location.hash = tabId;
        });
    });

    // 检查 URL hash
    const hash = window.location.hash.slice(1);
    if (hash && ['profile', 'security', 'notifications'].includes(hash)) {
        switchTab(hash);
    }
}

function switchTab(tabId) {
    // 更新导航
    document.querySelectorAll('.profile-nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabId);
    });

    // 更新内容
    document.querySelectorAll('.profile-section').forEach(section => {
        section.classList.remove('active');
    });

    const targetSection = document.getElementById(tabId + 'Tab');
    if (targetSection) {
        targetSection.classList.add('active');
    }
}

// ============================================
// 个人资料表单
// ============================================

function initProfileForm() {
    const form = document.getElementById('profileForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = {
            display_name: form.displayName.value.trim(),
            email: form.email.value.trim(),
            bio: form.bio.value.trim(),
            website: form.website.value.trim(),
            github: form.github.value.trim()
        };

        try {
            const response = await authFetch('/api/auth/profile', {
                method: 'PUT',
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                saveUser(data.data);
                updateProfileUI(data.data);
                showToast('个人资料已更新', 'success');
            } else {
                showToast(data.error?.message || '更新失败', 'error');
            }
        } catch (error) {
            console.error('Profile update error:', error);
            showToast('网络错误，请稍后重试', 'error');
        }
    });
}

// ============================================
// 密码修改表单
// ============================================

function initPasswordForm() {
    const form = document.getElementById('passwordForm');
    if (!form) return;

    const errorEl = document.getElementById('passwordError');
    const successEl = document.getElementById('passwordSuccess');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        errorEl.classList.add('hidden');
        successEl.classList.add('hidden');

        const currentPassword = form.currentPassword.value;
        const newPassword = form.newPassword.value;
        const confirmPassword = form.confirmNewPassword.value;

        // 验证
        if (newPassword.length < 6) {
            errorEl.textContent = '新密码长度至少 6 位';
            errorEl.classList.remove('hidden');
            return;
        }

        if (newPassword !== confirmPassword) {
            errorEl.textContent = '两次输入的密码不一致';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            const response = await authFetch('/api/auth/password', {
                method: 'PUT',
                body: JSON.stringify({
                    old_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (data.success) {
                successEl.textContent = '密码已更新';
                successEl.classList.remove('hidden');
                form.reset();
            } else {
                errorEl.textContent = data.error?.message || '密码更新失败';
                errorEl.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Password update error:', error);
            errorEl.textContent = '网络错误，请稍后重试';
            errorEl.classList.remove('hidden');
        }
    });
}

// ============================================
// 通知设置表单
// ============================================

function initNotificationsForm() {
    const form = document.getElementById('notificationsForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const settings = {
            email_notifications: form.emailNotifications.checked,
            new_post_notifications: form.newPostNotifications.checked,
            comment_reply_notifications: form.commentReplyNotifications.checked,
            release_notifications: form.releaseNotifications.checked
        };

        try {
            const response = await authFetch('/api/auth/notifications', {
                method: 'PUT',
                body: JSON.stringify(settings)
            });

            const data = await response.json();

            if (data.success) {
                showToast('通知设置已保存', 'success');
            } else {
                showToast(data.error?.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('Notifications update error:', error);
            showToast('网络错误，请稍后重试', 'error');
        }
    });
}

// ============================================
// 删除账户
// ============================================

function confirmDeleteAccount() {
    if (confirm('确定要删除账户吗？此操作不可撤销，所有数据将被永久删除。')) {
        if (confirm('请再次确认：删除账户后无法恢复。')) {
            deleteAccount();
        }
    }
}

async function deleteAccount() {
    try {
        const response = await authFetch('/api/auth/account', {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            clearTokens();
            window.location.href = 'index.html';
        } else {
            showToast(data.error?.message || '删除失败', 'error');
        }
    } catch (error) {
        console.error('Delete account error:', error);
        showToast('网络错误，请稍后重试', 'error');
    }
}

// ============================================
// Toast 通知
// ============================================

function showToast(message, type = 'info') {
    // 移除已有的 toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    // 添加样式
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? 'rgba(39, 201, 63, 0.9)' : type === 'error' ? 'rgba(255, 95, 86, 0.9)' : 'rgba(0, 255, 136, 0.9)'};
        color: ${type === 'success' || type === 'error' ? 'white' : 'var(--bg-primary)'};
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    // 自动移除
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .toast-close {
        background: none;
        border: none;
        color: inherit;
        font-size: 1.25rem;
        cursor: pointer;
        opacity: 0.7;
    }
    .toast-close:hover {
        opacity: 1;
    }
`;
document.head.appendChild(style);

// 全局函数
window.confirmDeleteAccount = confirmDeleteAccount;
