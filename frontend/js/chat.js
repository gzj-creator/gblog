const AI_API_BASE = 'http://localhost:8000';

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
            this.addMessage('抱歉，服务暂时不可用，请稍后再试。', 'bot');
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
        const response = await fetch(`${AI_API_BASE}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                session_id: this.sessionId,
                use_memory: true,
            }),
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
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
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 解析 SSE 事件
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 保留未完成的行

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.content) {
                        fullText += data.content;
                        contentDiv.innerHTML = this.formatMessage(fullText);
                        this.scrollToBottom();
                    }

                    if (data.done && data.sources && data.sources.length > 0) {
                        this.addSources(data.sources);
                    }

                    if (data.error) {
                        contentDiv.innerHTML = this.formatMessage('抱歉，生成回答时出错了。');
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    }

    _loadSessionId() {
        return localStorage.getItem('galay_chat_session') || 'session_' + Date.now();
    }

    _saveSessionId(id) {
        localStorage.setItem('galay_chat_session', id);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
