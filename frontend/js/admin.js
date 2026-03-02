const API_ROOT = "/ai/api";
const AUTH_ROOT = `${API_ROOT}/auth`;
const TOKEN_KEY = "galay_ai_admin_access_token";
const REFRESH_KEY = "galay_ai_admin_refresh_token";

let accessToken = localStorage.getItem(TOKEN_KEY) || "";
let refreshToken = localStorage.getItem(REFRESH_KEY) || "";

function setStatus(id, text, ok = true) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text || "";
    el.classList.remove("ok", "error");
    if (!text) return;
    el.classList.add(ok ? "ok" : "error");
}

function saveTokens(nextAccess, nextRefresh = null) {
    accessToken = nextAccess || "";
    refreshToken = nextRefresh !== null ? nextRefresh : refreshToken;
    if (accessToken) localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
}

function clearTokens() {
    accessToken = "";
    refreshToken = "";
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
}

function updateAuthLabel(text, ok = false) {
    setStatus("authStatus", text, ok);
}

async function refreshAccessToken() {
    if (!refreshToken) return false;
    try {
        const response = await fetch(`${AUTH_ROOT}/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        const data = await response.json();
        if (!response.ok || !data.success || !data.data?.access_token) {
            clearTokens();
            return false;
        }
        saveTokens(data.data.access_token);
        return true;
    } catch (_error) {
        clearTokens();
        return false;
    }
}

async function adminFetch(path, options = {}, retry401 = true) {
    const headers = { ...(options.headers || {}) };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
    if (response.status === 401 && retry401) {
        const ok = await refreshAccessToken();
        if (ok) {
            return adminFetch(path, options, false);
        }
    }
    return response;
}

async function parseJsonResponse(response) {
    const text = await response.text();
    let payload = {};
    if (text) {
        try {
            payload = JSON.parse(text);
        } catch (_error) {
            payload = { detail: text };
        }
    }
    if (!response.ok) {
        const detail = payload.detail || payload.error?.message || "请求失败";
        throw new Error(detail);
    }
    return payload;
}

async function login(event) {
    event.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;
    if (!username || !password) {
        updateAuthLabel("请输入用户名和密码", false);
        return;
    }

    try {
        const response = await fetch(`${AUTH_ROOT}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const payload = await parseJsonResponse(response);
        const access = payload.data?.access_token || "";
        const refresh = payload.data?.refresh_token || "";
        if (!access || !refresh) {
            throw new Error("登录响应缺少 token");
        }
        saveTokens(access, refresh);
        updateAuthLabel(`已登录：${payload.data?.user?.username || username}`, true);
        setStatus("uploadStatus", "");
        await loadConfig();
        await loadDocuments();
    } catch (error) {
        clearTokens();
        updateAuthLabel(`登录失败：${error.message}`, false);
    }
}

async function logout() {
    try {
        if (accessToken || refreshToken) {
            await fetch(`${AUTH_ROOT}/logout`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
                },
                body: JSON.stringify({ refresh_token: refreshToken || null })
            });
        }
    } catch (_error) {
        // ignore logout errors
    }
    clearTokens();
    updateAuthLabel("已登出", true);
    document.getElementById("docsList").innerHTML = "";
}

async function verifyLogin() {
    if (!accessToken) {
        updateAuthLabel("未登录", false);
        return;
    }
    try {
        const response = await adminFetch("/auth/me");
        const payload = await parseJsonResponse(response);
        updateAuthLabel(`已登录：${payload.data?.username || "admin"}`, true);
        await loadConfig();
        await loadDocuments();
    } catch (_error) {
        clearTokens();
        updateAuthLabel("登录状态已失效，请重新登录", false);
    }
}

async function rebuildIndex() {
    try {
        const response = await adminFetch("/admin/rebuild", {
            method: "POST",
            body: JSON.stringify({ confirm: true })
        });
        const payload = await parseJsonResponse(response);
        setStatus("rebuildStatus", payload.message || "索引重建完成", true);
    } catch (error) {
        setStatus("rebuildStatus", `重建失败：${error.message}`, false);
    }
}

async function uploadDocument(event) {
    event.preventDefault();
    const fileInput = document.getElementById("uploadFile");
    const file = fileInput.files?.[0];
    if (!file) {
        setStatus("uploadStatus", "请先选择文件", false);
        return;
    }

    const project = document.getElementById("uploadProject").value.trim();
    const relativePath = document.getElementById("uploadRelativePath").value.trim();
    const autoReindex = document.getElementById("uploadAutoReindex").checked;

    const formData = new FormData();
    formData.append("file", file);
    if (project) formData.append("project", project);
    if (relativePath) formData.append("relative_path", relativePath);
    formData.append("auto_reindex", autoReindex ? "true" : "false");

    try {
        const response = await adminFetch("/admin/docs/upload", {
            method: "POST",
            body: formData,
            headers: {}
        });
        const payload = await parseJsonResponse(response);
        const reindexText = payload.reindex?.triggered ? `；${payload.reindex.message || "已触发重建"}` : "";
        setStatus("uploadStatus", `上传成功：${payload.document.relative_path}${reindexText}`, true);
        fileInput.value = "";
        document.getElementById("uploadRelativePath").value = "";
        await loadDocuments();
    } catch (error) {
        setStatus("uploadStatus", `上传失败：${error.message}`, false);
    }
}

async function saveEditorDocument(event) {
    event.preventDefault();
    const project = document.getElementById("editorProject").value.trim();
    const relativePath = document.getElementById("editorRelativePath").value.trim();
    const content = document.getElementById("editorContent").value;
    const autoReindex = document.getElementById("editorAutoReindex").checked;

    if (!relativePath) {
        setStatus("editorStatus", "relative_path 不能为空", false);
        return;
    }

    try {
        const response = await adminFetch("/admin/docs/content", {
            method: "PUT",
            body: JSON.stringify({
                project: project || null,
                relative_path: relativePath,
                content,
                auto_reindex: autoReindex
            })
        });
        const payload = await parseJsonResponse(response);
        const reindexText = payload.reindex?.triggered ? `；${payload.reindex.message || "已触发重建"}` : "";
        setStatus("editorStatus", `保存成功：${payload.document.relative_path}${reindexText}`, true);
        await loadDocuments();
    } catch (error) {
        setStatus("editorStatus", `保存失败：${error.message}`, false);
    }
}

async function deleteCurrentDocument() {
    const project = document.getElementById("editorProject").value.trim();
    const relativePath = document.getElementById("editorRelativePath").value.trim();
    const autoReindex = document.getElementById("editorAutoReindex").checked;

    if (!relativePath) {
        setStatus("editorStatus", "请先填写要删除的 relative_path", false);
        return;
    }
    if (!window.confirm(`确认删除文档：${project || "custom"}/${relativePath}？`)) return;

    await deleteDocument(project || null, relativePath, autoReindex);
}

async function deleteDocument(project, relativePath, autoReindex = true) {
    try {
        const response = await adminFetch("/admin/docs", {
            method: "DELETE",
            body: JSON.stringify({
                project,
                relative_path: relativePath,
                auto_reindex: autoReindex
            })
        });
        const payload = await parseJsonResponse(response);
        const reindexText = payload.reindex?.triggered ? `；${payload.reindex.message || "已触发重建"}` : "";
        setStatus("editorStatus", `删除成功：${relativePath}${reindexText}`, true);
        await loadDocuments();
    } catch (error) {
        setStatus("editorStatus", `删除失败：${error.message}`, false);
    }
}

async function loadDocuments() {
    const list = document.getElementById("docsList");
    list.innerHTML = "<li class=\"doc-meta\">加载中...</li>";
    try {
        const response = await adminFetch("/admin/docs");
        const payload = await parseJsonResponse(response);
        const docs = payload.documents || [];
        if (!docs.length) {
            list.innerHTML = "<li class=\"doc-meta\">暂无后台文档</li>";
            return;
        }
        list.innerHTML = "";
        docs.forEach((doc) => {
            const item = document.createElement("li");
            item.className = "doc-item";
            const updated = new Date(doc.updated_at).toLocaleString();
            item.innerHTML = `
                <div class="doc-title">${doc.project}/${doc.relative_path}</div>
                <div class="doc-meta">${doc.size_bytes} bytes · ${updated}</div>
                <div class="doc-actions">
                    <button type="button" data-act="open">编辑</button>
                    <button type="button" class="danger" data-act="delete">删除</button>
                </div>
            `;
            item.querySelector('[data-act="open"]').addEventListener("click", () => {
                openDocument(doc.project, doc.relative_path);
            });
            item.querySelector('[data-act="delete"]').addEventListener("click", async () => {
                if (window.confirm(`确认删除 ${doc.project}/${doc.relative_path}？`)) {
                    await deleteDocument(doc.project, doc.relative_path, true);
                }
            });
            list.appendChild(item);
        });
    } catch (error) {
        list.innerHTML = `<li class="doc-meta">加载失败：${error.message}</li>`;
    }
}

async function openDocument(project, relativePath) {
    try {
        const query = new URLSearchParams({
            project,
            relative_path: relativePath
        });
        const response = await adminFetch(`/admin/docs/content?${query.toString()}`);
        const payload = await parseJsonResponse(response);
        const doc = payload.document || {};
        document.getElementById("editorProject").value = doc.project || project;
        document.getElementById("editorRelativePath").value = doc.relative_path || relativePath;
        document.getElementById("editorContent").value = doc.content || "";
        setStatus("editorStatus", `已加载：${doc.project}/${doc.relative_path}`, true);
    } catch (error) {
        setStatus("editorStatus", `加载文档失败：${error.message}`, false);
    }
}

async function loadConfig() {
    try {
        const response = await adminFetch("/admin/config");
        const payload = await parseJsonResponse(response);
        const cfg = payload.config || {};
        document.getElementById("cfgAutoReindex").checked = !!cfg.auto_reindex_on_doc_change;
        document.getElementById("cfgDefaultProject").value = cfg.default_doc_project || "custom";
        document.getElementById("cfgExtensions").value = Array.isArray(cfg.allowed_extensions)
            ? cfg.allowed_extensions.join(",")
            : "";
        document.getElementById("cfgMaxUpload").value = cfg.max_upload_size_kb || 1024;
        if (cfg.default_doc_project) {
            document.getElementById("uploadProject").value = cfg.default_doc_project;
            document.getElementById("editorProject").value = cfg.default_doc_project;
        }
        setStatus("configStatus", "配置已加载", true);
    } catch (error) {
        setStatus("configStatus", `读取配置失败：${error.message}`, false);
    }
}

async function saveConfig(event) {
    event.preventDefault();
    const extensionsRaw = document.getElementById("cfgExtensions").value.trim();
    const extensions = extensionsRaw
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

    const body = {
        auto_reindex_on_doc_change: document.getElementById("cfgAutoReindex").checked,
        default_doc_project: document.getElementById("cfgDefaultProject").value.trim() || "custom",
        allowed_extensions: extensions,
        max_upload_size_kb: Number(document.getElementById("cfgMaxUpload").value || "1024")
    };

    try {
        const response = await adminFetch("/admin/config", {
            method: "PUT",
            body: JSON.stringify(body)
        });
        await parseJsonResponse(response);
        setStatus("configStatus", "配置保存成功", true);
    } catch (error) {
        setStatus("configStatus", `保存失败：${error.message}`, false);
    }
}

function bindEvents() {
    document.getElementById("loginForm").addEventListener("submit", login);
    document.getElementById("logoutBtn").addEventListener("click", logout);
    document.getElementById("rebuildBtn").addEventListener("click", rebuildIndex);
    document.getElementById("uploadForm").addEventListener("submit", uploadDocument);
    document.getElementById("editorForm").addEventListener("submit", saveEditorDocument);
    document.getElementById("deleteDocBtn").addEventListener("click", deleteCurrentDocument);
    document.getElementById("loadConfigBtn").addEventListener("click", loadConfig);
    document.getElementById("configForm").addEventListener("submit", saveConfig);
    document.getElementById("refreshDocsBtn").addEventListener("click", loadDocuments);
}

document.addEventListener("DOMContentLoaded", async () => {
    bindEvents();
    await verifyLogin();
});
