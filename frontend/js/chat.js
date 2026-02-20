const AI_API_BASE = '/ai';
const STREAM_CONNECT_TIMEOUT_MS = 15000;
const STREAM_IDLE_TIMEOUT_MS = 45000;

class ChatApp {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.quickButtons = document.querySelectorAll('.chat-quick-btn');
        this.sessionId = this._loadSessionId();

        this.init();
    }

    init() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.quickButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.getAttribute('data-question');
                this.chatInput.value = question;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.sendButton.disabled = true;

        this.showTypingIndicator();

        try {
            await this.callStreamAPI(message);
        } catch (error) {
            this.removeTypingIndicator();
            const detail = this._extractErrorDetail(error);
            this.addMessage(`抱歉，服务暂时不可用：${detail}`, 'bot');
            console.error('Error:', error);
        }

        this.sendButton.disabled = false;
        this.chatInput.focus();
    }

    _createAvatar(type) {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (type === 'bot') {
            avatar.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>';
        } else {
            avatar.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
        }
        return avatar;
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        messageDiv.appendChild(this._createAvatar(type));

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const formattedText = this.formatMessage(text);
        contentDiv.innerHTML = formattedText;

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        this.scrollToBottom();
        return contentDiv;
    }

    addSources(sources) {
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'message bot-message sources-message';

        const items = sources.map(s =>
            `<span class="source-tag" title="${this.escapeHtml(s.file)}">${this.escapeHtml(s.project)} / ${this.escapeHtml(s.file_name)}</span>`
        ).join(' ');

        sourceDiv.innerHTML = `
            <div class="message-content sources-content">
                <small>引用来源：${items}</small>
            </div>
        `;
        this.chatMessages.appendChild(sourceDiv);
        this.scrollToBottom();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatMessage(text) {
        // 先转义 HTML
        text = this.escapeHtml(text);

        // 代码块
        text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

        // 行内代码
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

        // 列表
        text = text.replace(/^\* (.+)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // 段落
        text = text.replace(/\n\n/g, '</p><p>');
        text = '<p>' + text + '</p>';

        return text;
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message bot-message typing-message';
        indicator.appendChild(this._createAvatar('bot'));
        const content = document.createElement('div');
        content.className = 'message-content typing-indicator';
        content.innerHTML = '<span></span><span></span><span></span>';
        indicator.appendChild(content);
        this.chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = this.chatMessages.querySelector('.typing-message');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    async callStreamAPI(message) {
        const response = await this._fetchWithTimeout(
            `${AI_API_BASE}/api/chat/stream`,
            {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                session_id: this.sessionId,
                use_memory: true,
            }),
            },
            STREAM_CONNECT_TIMEOUT_MS,
            '连接 AI 服务超时'
        );

        if (!response.ok) {
            let detail = `HTTP ${response.status}`;
            try {
                const contentType = response.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    const body = await response.json();
                    detail = body.error || body.detail || body.message || detail;
                } else {
                    const text = (await response.text()).trim();
                    if (text) {
                        detail = text;
                    }
                }
            } catch (e) {
                // ignore parse errors
            }
            throw new Error(detail);
        }

        this.removeTypingIndicator();

        // 创建 bot 消息容器，用于流式追加
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.appendChild(this._createAvatar('bot'));
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        let fullText = '';
        if (!response.body) {
            throw new Error('AI 流式响应不可用');
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let gotContent = false;

        while (true) {
            const { done, value } = await this._readChunkWithTimeout(reader, STREAM_IDLE_TIMEOUT_MS);
            if (done) {
                this._consumeSSEBuffer(buffer, contentDiv, (updatedText) => {
                    fullText = updatedText;
                    gotContent = gotContent || Boolean(fullText);
                });
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            buffer = this._consumeSSEBuffer(buffer, contentDiv, (updatedText) => {
                fullText = updatedText;
                gotContent = gotContent || Boolean(fullText);
            });
        }

        if (!gotContent) {
            const fallback = await this._callNonStreamAPI(message);
            contentDiv.innerHTML = this.formatMessage(fallback.response);
            if (fallback.sources && fallback.sources.length > 0) {
                this.addSources(fallback.sources);
            }
            this.scrollToBottom();
        }
    }

    _consumeSSEBuffer(buffer, contentDiv, onTextUpdate) {
        const lines = buffer.split('\n');
        const tail = lines.pop() || '';
        let fullText = contentDiv.textContent || '';

        for (const rawLine of lines) {
            const line = rawLine.trimEnd();
            if (!line.startsWith('data:')) continue;
            const payload = line.replace(/^data:\s*/, '');
            if (!payload) continue;

            try {
                const data = JSON.parse(payload);
                if (data.content) {
                    fullText += String(data.content);
                    contentDiv.innerHTML = this.formatMessage(fullText);
                    this.scrollToBottom();
                    onTextUpdate(fullText);
                }
                if (data.done && data.sources && data.sources.length > 0) {
                    this.addSources(data.sources);
                }
                if (data.error) {
                    contentDiv.innerHTML = this.formatMessage('抱歉，生成回答时出错了。');
                    onTextUpdate(contentDiv.textContent || '');
                }
            } catch (e) {
                // ignore malformed chunk
            }
        }
        return tail;
    }

    async _callNonStreamAPI(message) {
        const response = await this._fetchWithTimeout(
            `${AI_API_BASE}/api/chat`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    session_id: this.sessionId,
                    use_memory: true,
                }),
            },
            STREAM_CONNECT_TIMEOUT_MS,
            '连接 AI 服务超时'
        );

        if (!response.ok) {
            const detail = (await response.text()).trim() || `HTTP ${response.status}`;
            throw new Error(detail);
        }

        const body = await response.json();
        return {
            response: body.response || '抱歉，未返回有效内容。',
            sources: Array.isArray(body.sources) ? body.sources : [],
        };
    }

    _loadSessionId() {
        return localStorage.getItem('galay_chat_session') || 'session_' + Date.now();
    }

    _saveSessionId(id) {
        localStorage.setItem('galay_chat_session', id);
    }

    _extractErrorDetail(error) {
        const fallback = '请稍后再试';
        if (!error || !error.message) return fallback;
        const message = String(error.message).replace(/\s+/g, ' ').trim();
        if (!message) return fallback;
        return message.slice(0, 180);
    }

    async _fetchWithTimeout(url, options, timeoutMs, timeoutMessage) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await fetch(url, { ...options, signal: controller.signal });
        } catch (error) {
            if (error && error.name === 'AbortError') {
                throw new Error(timeoutMessage || '请求超时');
            }
            throw error;
        } finally {
            clearTimeout(timer);
        }
    }

    _readChunkWithTimeout(reader, timeoutMs) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('AI 响应超时，请稍后重试')), timeoutMs);
            reader.read()
                .then(result => {
                    clearTimeout(timer);
                    resolve(result);
                })
                .catch(error => {
                    clearTimeout(timer);
                    reject(error);
                });
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
