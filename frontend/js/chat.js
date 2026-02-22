const AI_API_BASE = '/ai';
const STREAM_CONNECT_TIMEOUT_MS = 15000;
const STREAM_IDLE_TIMEOUT_MS = 45000;
const FALLBACK_CONNECT_TIMEOUT_MS = 5000;

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
        this.chatMessages.addEventListener('click', (e) => {
            const copyBtn = e.target.closest('.code-copy-btn');
            if (!copyBtn) return;
            const codeElement = copyBtn.closest('.code-block')?.querySelector('code');
            if (!codeElement) return;
            this._copyCodeText(codeElement.textContent || '', copyBtn);
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
            let detail = this._extractErrorDetail(error);
            if (this._isConnectTimeoutError(error)) {
                try {
                    await this._callNonStreamAPI(message, FALLBACK_CONNECT_TIMEOUT_MS);
                } catch (fallbackError) {
                    const fallbackDetail = this._extractErrorDetail(fallbackError);
                    if (fallbackDetail) {
                        detail = fallbackDetail;
                    }
                }
            }
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

    addMessage(text, type, blocks = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        messageDiv.appendChild(this._createAvatar(type));

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (type === 'bot' && Array.isArray(blocks) && blocks.length > 0) {
            contentDiv.innerHTML = this.renderBlocks(blocks);
        } else {
            const formattedText = this.formatMessage(text);
            contentDiv.innerHTML = formattedText;
        }

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
        const codeBlocks = [];
        const normalized = this._normalizeMarkdownInput(text);
        const withPlaceholders = normalized.replace(/(^|\n)[“”"']*```([a-zA-Z0-9_-]+)?[ \t]*[”"']*\n([\s\S]*?)\n[“”"']*```[ \t]*[”"']*(?=\n|$)/g, (_match, prefix, lang, code) => {
            const codeIndex = codeBlocks.length;
            const firstCodeLine = String(code || '').split('\n')[0] || '';
            const guessedLang = this._guessCodeLanguage(firstCodeLine);
            const explicitLang = String(lang || '').trim().toLowerCase();
            const normalizedLang = (explicitLang || guessedLang || 'text').trim().toLowerCase();
            const safeLang = normalizedLang ? ` class="language-${this.escapeHtml(normalizedLang)}"` : '';
            const displayCode = this._normalizeCodeForDisplay((code || '').replace(/\n$/, ''), normalizedLang);
            if (!displayCode.trim()) {
                return `${prefix}\n`;
            }
            if (!explicitLang && !this._isLikelyCodeContent(displayCode, normalizedLang)) {
                return `${prefix}\n${displayCode}\n`;
            }
            codeBlocks.push(this._buildCodeBlockHtml(displayCode, normalizedLang, safeLang));
            return `${prefix}\n@@CODEBLOCK_${codeIndex}@@\n`;
        });

        const lines = withPlaceholders.split('\n');
        const htmlParts = [];
        let paragraphLines = [];
        let blockquoteLines = [];
        let activeList = '';
        let nextOrderedNumber = null;

        const flushParagraph = () => {
            if (paragraphLines.length === 0) return;
            const html = paragraphLines.map(line => this._formatInlineMarkdown(line)).join('<br>');
            htmlParts.push(`<p>${html}</p>`);
            paragraphLines = [];
        };

        const flushBlockquote = () => {
            if (blockquoteLines.length === 0) return;
            const html = blockquoteLines.map(line => this._formatInlineMarkdown(line)).join('<br>');
            htmlParts.push(`<blockquote>${html}</blockquote>`);
            blockquoteLines = [];
        };

        const closeList = () => {
            if (!activeList) return;
            htmlParts.push(`</${activeList}>`);
            if (activeList === 'ol') {
                nextOrderedNumber = null;
            }
            activeList = '';
        };

        for (const rawLine of lines) {
            const line = rawLine.trimEnd();
            const trimmed = line.trim();
            if (!trimmed) {
                flushParagraph();
                flushBlockquote();
                closeList();
                continue;
            }

            const codeMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
            if (codeMatch) {
                flushParagraph();
                flushBlockquote();
                closeList();
                const codeHtml = codeBlocks[Number(codeMatch[1])];
                if (codeHtml) {
                    htmlParts.push(codeHtml);
                }
                continue;
            }

            if (/^([-*_])\1{2,}$/.test(trimmed)) {
                flushParagraph();
                flushBlockquote();
                closeList();
                htmlParts.push('<hr>');
                continue;
            }

            const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
            if (headingMatch) {
                flushParagraph();
                flushBlockquote();
                closeList();
                const level = headingMatch[1].length;
                htmlParts.push(`<h${level}>${this._formatInlineMarkdown(headingMatch[2])}</h${level}>`);
                continue;
            }

            const quoteMatch = trimmed.match(/^>\s?(.*)$/);
            if (quoteMatch) {
                flushParagraph();
                closeList();
                blockquoteLines.push(quoteMatch[1]);
                continue;
            }

            const olMatch = trimmed.match(/^[✅☑️✔️🔥🌟🧠🔧⚙️🛠️📈📌]?\s*(\d+)\.\s+(.+)$/u);
            if (olMatch) {
                flushParagraph();
                flushBlockquote();
                const itemNumber = Number(olMatch[1]);
                const isRepeatedOne = activeList === 'ol' && nextOrderedNumber !== null && nextOrderedNumber > 1 && itemNumber === 1;
                const shouldOpenNewOl = activeList !== 'ol' || nextOrderedNumber === null || (!isRepeatedOne && itemNumber !== nextOrderedNumber);
                if (shouldOpenNewOl) {
                    closeList();
                    htmlParts.push(itemNumber > 1 ? `<ol start="${itemNumber}">` : '<ol>');
                    activeList = 'ol';
                }
                htmlParts.push(`<li>${this._formatInlineMarkdown(olMatch[2])}</li>`);
                nextOrderedNumber = isRepeatedOne ? (nextOrderedNumber + 1) : (itemNumber + 1);
                continue;
            }

            const ulMatch = trimmed.match(/^[-*]\s+(.+)$/);
            if (ulMatch) {
                flushParagraph();
                flushBlockquote();
                if (activeList !== 'ul') {
                    closeList();
                    htmlParts.push('<ul>');
                    activeList = 'ul';
                }
                htmlParts.push(`<li>${this._formatInlineMarkdown(ulMatch[1])}</li>`);
                continue;
            }

            flushBlockquote();
            closeList();
            paragraphLines.push(trimmed);
        }

        flushParagraph();
        flushBlockquote();
        closeList();

        return htmlParts.join('');
    }

    _buildCodeBlockHtml(displayCode, normalizedLang, safeLang) {
        const language = (normalizedLang || 'text').trim().toLowerCase() || 'text';
        const classAttr = safeLang || (language ? ` class="language-${this.escapeHtml(language)}"` : '');
        const safeCode = this._highlightCode(displayCode, language);
        const safeLabel = this.escapeHtml(language);
        return `<div class="code-block"><div class="code-block-toolbar"><span class="code-lang">${safeLabel}</span><button type="button" class="code-copy-btn">复制</button></div><pre><code${classAttr}>${safeCode}</code></pre></div>`;
    }

    renderBlocks(blocks) {
        if (!Array.isArray(blocks) || blocks.length === 0) {
            return '';
        }

        const htmlParts = [];
        for (const block of blocks) {
            if (!block || typeof block !== 'object') continue;
            const type = String(block.type || '').toLowerCase();

            if (type === 'heading') {
                const level = Math.min(Math.max(Number(block.level) || 1, 1), 6);
                const text = this._formatInlineMarkdown(String(block.text || ''));
                htmlParts.push(`<h${level}>${text}</h${level}>`);
                continue;
            }

            if (type === 'paragraph') {
                const text = String(block.text || '');
                if (!text.trim()) continue;
                const html = text.split('\n').map(line => this._formatInlineMarkdown(line)).join('<br>');
                htmlParts.push(`<p>${html}</p>`);
                continue;
            }

            if (type === 'blockquote') {
                const text = String(block.text || '');
                if (!text.trim()) continue;
                const html = text.split('\n').map(line => this._formatInlineMarkdown(line)).join('<br>');
                htmlParts.push(`<blockquote>${html}</blockquote>`);
                continue;
            }

            if (type === 'hr') {
                htmlParts.push('<hr>');
                continue;
            }

            if (type === 'list') {
                const items = Array.isArray(block.items) ? block.items : [];
                if (items.length === 0) continue;
                const isOrdered = Boolean(block.ordered);
                if (isOrdered) {
                    const start = Number(block.start) || 1;
                    htmlParts.push(start > 1 ? `<ol start="${start}">` : '<ol>');
                    for (const item of items) {
                        htmlParts.push(`<li>${this._formatInlineMarkdown(String(item || ''))}</li>`);
                    }
                    htmlParts.push('</ol>');
                } else {
                    htmlParts.push('<ul>');
                    for (const item of items) {
                        htmlParts.push(`<li>${this._formatInlineMarkdown(String(item || ''))}</li>`);
                    }
                    htmlParts.push('</ul>');
                }
                continue;
            }

            if (type === 'code') {
                const language = String(block.language || 'text').trim().toLowerCase() || 'text';
                const rawCode = String(block.code || '');
                const displayCode = this._normalizeCodeForDisplay(rawCode.replace(/\n$/, ''), language);
                if (!displayCode.trim()) continue;
                const safeLang = ` class="language-${this.escapeHtml(language)}"`;
                htmlParts.push(this._buildCodeBlockHtml(displayCode, language, safeLang));
                continue;
            }
        }

        return htmlParts.join('');
    }

    _normalizeMarkdownInput(text) {
        let normalized = String(text || '').replace(/\r\n?/g, '\n');
        normalized = normalized.replace(/(^|\n)[“”"']*```([a-zA-Z0-9_-]*)[”"']*[ \t]*(?=\n|$)/g, '$1```$2');
        normalized = normalized.replace(/```([a-zA-Z0-9_-]+)\s+(?=\S)/g, '```$1\n');
        normalized = normalized.replace(/([^\n])```[”"']?(?=\s*(?:\n|$))/g, '$1\n```');
        normalized = normalized.replace(/([^\n])\s*[“”"']?\s*```([a-zA-Z0-9_-]*)/g, '$1\n```$2');
        normalized = normalized.replace(/\n{3,}/g, '\n\n');
        return normalized.trim();
    }

    _recoverLooseCodeFences(text) {
        const lines = String(text || '').split('\n');
        const output = [];
        let inFence = false;
        let syntheticFence = false;
        let pendingLanguageHint = '';

        const closeSyntheticFence = () => {
            if (!syntheticFence) return;
            output.push('```');
            syntheticFence = false;
        };

        const normalizeFenceLine = (line) => String(line || '').trim().replace(/^[“”"']+|[“”"']+$/g, '');
        const isFenceLine = (line) => /^```[a-zA-Z0-9_-]*\s*$/.test(normalizeFenceLine(line));
        const isFenceClose = (line) => /^```\s*$/.test(normalizeFenceLine(line));

        for (const rawLine of lines) {
            const line = rawLine.replace(/\s+$/g, '');
            const trimmed = line.trim();
            const normalizedFenceLine = normalizeFenceLine(trimmed);

            if (isFenceLine(trimmed)) {
                if (syntheticFence) {
                    closeSyntheticFence();
                    pendingLanguageHint = '';
                    if (isFenceClose(trimmed)) {
                        // synthetic 代码块后面的裸 ``` 视为同一个 closing，不再输出。
                        continue;
                    }
                    output.push(normalizedFenceLine);
                    inFence = true;
                    continue;
                }

                if (!inFence) {
                    closeSyntheticFence();
                    pendingLanguageHint = '';
                    output.push(normalizedFenceLine);
                    inFence = true;
                    continue;
                }

                if (isFenceClose(trimmed)) {
                    output.push('```');
                    inFence = false;
                    pendingLanguageHint = '';
                    continue;
                }

                // fence 内再次出现 ```cpp 这类脏行，按语言标记文本处理，避免提前闭合。
                const nestedHint = normalizedFenceLine.replace(/^```/, '').trim();
                if (nestedHint) {
                    output.push(nestedHint);
                }
                continue;
            }

            if (inFence) {
                output.push(rawLine);
                continue;
            }

            if (!trimmed) {
                closeSyntheticFence();
                pendingLanguageHint = '';
                output.push('');
                continue;
            }

            if (this._isStandaloneLanguageHint(trimmed) && !syntheticFence) {
                pendingLanguageHint = this._normalizeLanguageHint(trimmed);
                continue;
            }

            const inlineCodeIndex = this._detectInlineCodeStartIndex(trimmed);
            if (inlineCodeIndex > 0) {
                const plainText = trimmed.slice(0, inlineCodeIndex).trim();
                const codeText = trimmed.slice(inlineCodeIndex).trim();
                if (plainText) {
                    closeSyntheticFence();
                    if (pendingLanguageHint) {
                        output.push(pendingLanguageHint);
                        pendingLanguageHint = '';
                    }
                    output.push(plainText);
                }
                if (!syntheticFence) {
                    const lang = pendingLanguageHint || this._guessCodeLanguage(codeText);
                    output.push(`\`\`\`${lang}`);
                    syntheticFence = true;
                }
                pendingLanguageHint = '';
                this._splitPackedCodeLine(codeText).forEach(part => output.push(part));
                continue;
            }

            if (this._looksLikeCodeLine(trimmed)) {
                if (!syntheticFence) {
                    const lang = pendingLanguageHint || this._guessCodeLanguage(trimmed);
                    output.push(`\`\`\`${lang}`);
                    syntheticFence = true;
                }
                pendingLanguageHint = '';
                this._splitPackedCodeLine(trimmed).forEach(part => output.push(part));
                continue;
            }

            closeSyntheticFence();
            if (pendingLanguageHint) {
                output.push(pendingLanguageHint);
                pendingLanguageHint = '';
            }
            output.push(trimmed);
        }

        closeSyntheticFence();
        if (pendingLanguageHint) {
            output.push(pendingLanguageHint);
        }
        return output.join('\n');
    }

    _detectInlineCodeStartIndex(text) {
        const hasChinese = /[\u4e00-\u9fa5]/u.test(text);
        if (/^(?:cpp|c\+\+)?\s*#include\s*</i.test(text)) return -1;
        if (/^(?:template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+)/.test(text)) return -1;
        if (/^\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake|make|mkdir|cd|ls|pwd|echo|export|sudo|apt(?:-get)?|brew|dnf|yum|nc|telnet|g\+\+|gcc|clang\+\+|clang)\b/i.test(text) && !hasChinese) return -1;
        if (/^(?:cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(/i.test(text)) return -1;
        if (/^\s*(int|void|bool|auto|size_t)\s+\w+.*[;{]?\s*$/.test(text)) return -1;

        const commandPattern = /\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake|make|mkdir|cd|ls|pwd|echo|export|sudo|apt(?:-get)?|brew|dnf|yum|nc|telnet|g\+\+|gcc|clang\+\+|clang)\b/i;
        const patterns = [
            /(?:cpp|c\+\+)?\s*#include\s*</i,
            /\bint\s+main\s*\(/,
            /\bcmake_minimum_required\s*\(/i,
            /\bproject\s*\(/i,
            commandPattern,
        ];
        let minIndex = -1;
        for (const pattern of patterns) {
            const match = pattern.exec(text);
            if (!match) continue;
            if (match.index <= 0) continue;
            if (pattern === commandPattern) {
                if (hasChinese) continue;
                const tail = text.slice(match.index + match[0].length);
                if (!/^\s+[$A-Za-z0-9_./:@=-]/.test(tail)) {
                    continue;
                }
            }
            if (minIndex < 0 || match.index < minIndex) {
                minIndex = match.index;
            }
        }
        return minIndex;
    }

    _looksLikeCodeLine(line) {
        const text = String(line || '').trim();
        if (!text) return false;
        const hasChinese = /[\u4e00-\u9fa5]/u.test(text);

        if (/^(?:cpp|c\+\+)?\s*#include\s*</i.test(text)) return true;
        if (/^(?:template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+)/.test(text)) return true;
        if (/^\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake|make|mkdir|cd|ls|pwd|echo|export|sudo|apt(?:-get)?|brew|dnf|yum|nc|telnet|g\+\+|gcc|clang\+\+|clang)\b/i.test(text) && !hasChinese) return true;
        if (/^(?:cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(/i.test(text)) return true;
        if (/^\s*(int|void|bool|auto|size_t)\s+\w+.*[;{]\s*$/.test(text)) return true;
        if (/\bco_(?:return|await|yield)\b/.test(text) && !hasChinese) return true;
        if (/^\s*return\b[^一-龥]*[;}]\s*$/.test(text) && !hasChinese) return true;
        if (/->\s*\w+\(/.test(text) && !hasChinese) return true;
        if (/^[{}]+[;,]?$/.test(text)) return true;
        if (/^[)\]}]+[;,]?$/.test(text)) return true;
        if (/[{}]/.test(text) && /\(/.test(text) && !hasChinese) return true;
        if (/;$/.test(text) && text.length >= 12 && !hasChinese) return true;

        return false;
    }

    _guessCodeLanguage(line) {
        const text = String(line || '').trim();
        if (!text) return 'text';
        if (/^(?:cpp|c\+\+)?\s*#include\s*</i.test(text) || /\bint\s+main\s*\(/.test(text)) return 'cpp';
        if (/^(?:cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(/i.test(text)) return 'cmake';
        if (/^\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake|make|mkdir|cd|ls|pwd|echo|export|sudo|apt(?:-get)?|brew|dnf|yum|nc|telnet|g\+\+|gcc|clang\+\+|clang)\b/i.test(text) && !/[\u4e00-\u9fa5]/u.test(text)) return 'bash';
        return 'text';
    }

    _isStandaloneLanguageHint(line) {
        const lang = this._normalizeLanguageHint(line);
        return lang !== '';
    }

    _normalizeLanguageHint(line) {
        let text = String(line || '').trim().toLowerCase();
        text = text
            .replace(/^\s*[-*+]\s*/, '')
            .replace(/^`+|`+$/g, '')
            .replace(/[：:]\s*$/g, '')
            .replace(/^language\s*[：:]\s*/g, '')
            .trim();

        if (['cpp', 'c++', 'cc', 'cxx', 'hpp', 'h'].includes(text)) return 'cpp';
        if (['bash', 'shell', 'sh', 'zsh'].includes(text)) return 'bash';
        if (text === 'cmake') return 'cmake';
        if (text === 'text' || text === 'plaintext') return 'text';
        return '';
    }

    _splitPackedCodeLine(line) {
        const normalized = String(line || '')
            .replace(
                /(#include\s*<[^>]+>)\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+))/gi,
                '$1\n'
            )
            .replace(
                /([;{}])\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+|return\b))/g,
                '$1\n'
            );

        return normalized
            .split('\n')
            .map(part => part.trim())
            .filter(Boolean);
    }

    _normalizeCodeForDisplay(code, language) {
        let text = this._sanitizeCodeFenceContent(String(code || '').replace(/\r\n?/g, '\n'), language).trimEnd();
        if (!text) return '';

        const lang = String(language || '').toLowerCase();
        const isCppLike = ['cpp', 'c++', 'cc', 'cxx', 'hpp', 'h'].includes(lang) || (lang === 'text' && this._looksLikeCodeLine(text.split('\n')[0] || ''));

        if (isCppLike && this._needsCodeReflow(text)) {
            text = this._splitCollapsedCppCode(text);
            text = this._reindentBraceCode(text);
        } else if (['bash', 'sh', 'zsh'].includes(lang)) {
            text = text.replace(/(\bcd\s+\S*?)(cmake\s+\.\.)/gi, '$1\n$2');
            if (this._needsCodeReflow(text)) {
                text = text.replace(/;\s*(?=\S)/g, ';\n');
                text = text.replace(/&&\s*(?=\S)/g, '&&\n');
                text = text.replace(/(\bcd\s+\S+)(?=(?:cmake\s|make\b|\.\/|nc\b|telnet\b))/gi, '$1\n');
            }
        } else if (lang === 'cmake' && this._needsCodeReflow(text)) {
            text = text.replace(/\)\s*(?=[A-Za-z_])/g, ')\n');
        }

        return text;
    }

    _sanitizeCodeFenceContent(code, language) {
        const lines = String(code || '').split('\n');
        const lang = this._normalizeLanguageHint(language) || String(language || '').toLowerCase() || 'text';
        const isFence = (line) => /^```[a-zA-Z0-9_-]*\s*$/.test(line.trim());

        while (lines.length > 0) {
            const first = lines[0].trim();
            if (!first) {
                lines.shift();
                continue;
            }
            if (isFence(first)) {
                lines.shift();
                continue;
            }
            const hint = this._normalizeLanguageHint(first);
            if (hint && (hint === lang || lang === 'text')) {
                lines.shift();
                continue;
            }
            break;
        }

        while (lines.length > 0) {
            const last = lines[lines.length - 1].trim();
            if (!last) {
                lines.pop();
                continue;
            }
            if (isFence(last)) {
                lines.pop();
                continue;
            }
            break;
        }

        return lines.join('\n');
    }

    _isLikelyCodeContent(code, language) {
        const text = String(code || '').trim();
        if (!text) return false;
        const lang = String(language || '').toLowerCase();

        if (['bash', 'sh', 'zsh'].includes(lang)) {
            const lines = text.split('\n');
            const hasCommandLikeLine = lines.some((line) => {
                if (/[\u4e00-\u9fa5]/u.test(line)) return false;
                const match = line.match(/^\$?\s*(git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake|make|mkdir|cd|ls|pwd|echo|export|sudo|apt(?:-get)?|brew|dnf|yum|nc|telnet|g\+\+|gcc|clang\+\+|clang)\b([^\n]*)$/i);
                if (!match) return false;
                const tail = String(match[2] || '');
                if (!tail.trim()) return true;
                return /^\s+[$A-Za-z0-9_./:@=-]/.test(tail);
            });

            return hasCommandLikeLine
                || /[;&|]/.test(text)
                || /^\s*\.\//m.test(text);
        }

        if (lang === 'cmake') {
            return /\b(cmake_minimum_required|project|add_executable|add_library|target_link_libraries|find_package)\s*\(/i.test(text);
        }

        if (['cpp', 'c++', 'cc', 'cxx', 'hpp', 'h'].includes(lang)) {
            return /#include\s*</.test(text)
                || /\b(int|void|bool|auto|size_t)\s+\w+\s*\(/.test(text)
                || /[;{}]/.test(text)
                || /::/.test(text);
        }

        if (lang === 'text') {
            return /\n/.test(text) && /[;{}()]/.test(text);
        }

        return true;
    }

    _needsCodeReflow(code) {
        const text = String(code || '');
        const lines = text.split('\n');
        if (lines.length <= 1) return true;

        const longLineCount = lines.filter(line => line.length > 120).length;
        const mediumLineCount = lines.filter(line => line.length > 90).length;
        const punctCount = (text.match(/[{};]/g) || []).length;

        return longLineCount > 0 || (lines.length <= 6 && mediumLineCount >= 2) || (lines.length <= 4 && punctCount >= 8);
    }

    _splitCollapsedCppCode(code) {
        let text = String(code || '');
        text = text.replace(/(#\s*include\s*<[^>]+>)\s*(?=\S)/g, '$1\n');
        text = text.replace(/>\s*(?=(?:#include\b|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+))/g, '>\n');
        text = text.replace(/;\s*(?=})/g, ';\n');
        text = text.replace(
            /;\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+|if\s*\(|for\s*\(|while\s*\(|switch\s*\(|return\b|auto\s+\w+|const\s+\w+|std::|[A-Za-z_]\w+\s*->))/g,
            ';\n'
        );
        text = text.replace(/{\s*(?=\S)/g, '{\n');
        text = text.replace(/}\s*(?=(?:else\b|[A-Za-z_#]))/g, '}\n');
        text = text.replace(
            /\)\s*(?=(?:if|for|while|switch|return|auto|const|std::|[A-Za-z_]\w+\s*->))/g,
            ')\n'
        );
        text = text.replace(/\n{3,}/g, '\n\n');
        return text;
    }

    _reindentBraceCode(code) {
        const lines = String(code || '').split('\n');
        const output = [];
        let depth = 0;

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) {
                output.push('');
                continue;
            }

            const startsWithClose = line.startsWith('}');
            const indentLevel = Math.max(depth - (startsWithClose ? 1 : 0), 0);
            const indent = line.startsWith('#') ? '' : '    '.repeat(indentLevel);
            output.push(`${indent}${line}`);

            const openCount = (line.match(/{/g) || []).length;
            const closeCount = (line.match(/}/g) || []).length;
            depth += openCount - closeCount;
            if (depth < 0) depth = 0;
        }

        return output.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    }

    _highlightCode(code, language) {
        const text = String(code || '');
        const lang = String(language || '').toLowerCase();

        if (['cpp', 'c++', 'cc', 'cxx', 'hpp', 'h'].includes(lang)) {
            return this._highlightCpp(text);
        }
        if (['bash', 'sh', 'zsh'].includes(lang)) {
            return this._highlightBash(text);
        }
        if (lang === 'cmake') {
            return this._highlightCmake(text);
        }
        return this.escapeHtml(text);
    }

    _highlightCpp(code) {
        const keywords = this._getCppKeywordSet();
        const types = this._getCppTypeSet();
        const nonFunctionWords = this._getCppNonFunctionWordSet();
        let output = '';
        let i = 0;
        const text = String(code || '');

        const isWordChar = (ch) => /[A-Za-z0-9_]/.test(ch);
        const isDigit = (ch) => /[0-9]/.test(ch);

        while (i < text.length) {
            const ch = text[i];

            if (ch === '/' && text[i + 1] === '/') {
                let j = i + 2;
                while (j < text.length && text[j] !== '\n') j += 1;
                output += `<span class="code-token-comment">${this.escapeHtml(text.slice(i, j))}</span>`;
                i = j;
                continue;
            }

            if (ch === '/' && text[i + 1] === '*') {
                let j = i + 2;
                while (j + 1 < text.length && !(text[j] === '*' && text[j + 1] === '/')) j += 1;
                j = j + 1 < text.length ? j + 2 : text.length;
                output += `<span class="code-token-comment">${this.escapeHtml(text.slice(i, j))}</span>`;
                i = j;
                continue;
            }

            if (ch === '"' || ch === '\'') {
                const quote = ch;
                let j = i + 1;
                while (j < text.length) {
                    if (text[j] === '\\') {
                        j += 2;
                        continue;
                    }
                    if (text[j] === quote) {
                        j += 1;
                        break;
                    }
                    j += 1;
                }
                output += `<span class="code-token-string">${this.escapeHtml(text.slice(i, j))}</span>`;
                i = j;
                continue;
            }

            if (i === 0 || text[i - 1] === '\n') {
                let j = i;
                while (j < text.length && (text[j] === ' ' || text[j] === '\t')) j += 1;
                if (text[j] === '#') {
                    let k = j;
                    while (k < text.length && text[k] !== '\n') k += 1;
                    output += this.escapeHtml(text.slice(i, j));
                    output += `<span class="code-token-preproc">${this.escapeHtml(text.slice(j, k))}</span>`;
                    i = k;
                    continue;
                }
            }

            if (/[A-Za-z_]/.test(ch)) {
                let j = i + 1;
                while (j < text.length && isWordChar(text[j])) j += 1;
                const ident = text.slice(i, j);

                if (keywords.has(ident)) {
                    output += `<span class="code-token-keyword">${this.escapeHtml(ident)}</span>`;
                } else if (types.has(ident) || ident.endsWith('_t')) {
                    output += `<span class="code-token-type">${this.escapeHtml(ident)}</span>`;
                } else {
                    let k = j;
                    while (k < text.length && (text[k] === ' ' || text[k] === '\t')) k += 1;
                    const isFunction = text[k] === '(' && !nonFunctionWords.has(ident);
                    if (isFunction) {
                        output += `<span class="code-token-function">${this.escapeHtml(ident)}</span>`;
                    } else {
                        output += this.escapeHtml(ident);
                    }
                }
                i = j;
                continue;
            }

            if (isDigit(ch)) {
                let j = i;
                if (text[j] === '0' && (text[j + 1] === 'x' || text[j + 1] === 'X')) {
                    j += 2;
                    while (j < text.length && /[0-9A-Fa-f]/.test(text[j])) j += 1;
                } else {
                    while (j < text.length && /[0-9.]/.test(text[j])) j += 1;
                    while (j < text.length && /[uUlLfF]/.test(text[j])) j += 1;
                }
                output += `<span class="code-token-number">${this.escapeHtml(text.slice(i, j))}</span>`;
                i = j;
                continue;
            }

            output += this.escapeHtml(ch);
            i += 1;
        }

        return output;
    }

    _highlightBash(code) {
        let html = this.escapeHtml(String(code || ''));
        const placeholders = [];
        const saveToken = (tokenHtml) => {
            const index = placeholders.length;
            placeholders.push(tokenHtml);
            return `@@BASH_TOKEN_${index}@@`;
        };

        html = html.replace(/(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')/g, (match) => {
            return saveToken(`<span class="code-token-string">${match}</span>`);
        });

        html = html.replace(/(^|\n)(\s*#.*)(?=\n|$)/g, (_m, prefix, comment) => {
            return `${prefix}<span class="code-token-comment">${comment}</span>`;
        });

        html = html.replace(/\b(if|then|fi|for|in|do|done|while|case|esac|function|local|export|set|cd|echo|cat|grep|sed|awk|curl|wget|git|docker|kubectl|cmake|make|mkdir|ls|pwd|sudo|apt|apt-get|brew|dnf|yum|nc|telnet|python|python3|pip|npm|pnpm|yarn|g\+\+|gcc|clang\+\+|clang)\b/g, '<span class="code-token-keyword">$1</span>');
        html = html.replace(/(\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]+\})/g, '<span class="code-token-number">$1</span>');

        html = html.replace(/@@BASH_TOKEN_(\d+)@@/g, (_m, idx) => placeholders[Number(idx)] || '');
        return html;
    }

    _highlightCmake(code) {
        let html = this.escapeHtml(String(code || ''));
        const placeholders = [];
        const saveToken = (tokenHtml) => {
            const index = placeholders.length;
            placeholders.push(tokenHtml);
            return `@@CMAKE_TOKEN_${index}@@`;
        };

        html = html.replace(/(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')/g, (match) => {
            return saveToken(`<span class="code-token-string">${match}</span>`);
        });

        html = html.replace(/(^|\n)(\s*#.*)(?=\n|$)/g, (_m, prefix, comment) => {
            return `${prefix}<span class="code-token-comment">${comment}</span>`;
        });

        html = html.replace(/\b(project|cmake_minimum_required|add_executable|add_library|target_link_libraries|target_include_directories|set|if|elseif|else|endif|find_package|include|install)\b(?=\s*\()/g, '<span class="code-token-function">$1</span>');
        html = html.replace(/(\$\{[^}]+\})/g, '<span class="code-token-number">$1</span>');

        html = html.replace(/@@CMAKE_TOKEN_(\d+)@@/g, (_m, idx) => placeholders[Number(idx)] || '');
        return html;
    }

    _getCppKeywordSet() {
        if (!this._cppKeywordSet) {
            this._cppKeywordSet = new Set([
                'alignas', 'alignof', 'asm', 'auto', 'break', 'case', 'catch', 'class', 'concept', 'const',
                'consteval', 'constexpr', 'constinit', 'continue', 'co_await', 'co_return', 'co_yield',
                'decltype', 'default', 'delete', 'do', 'else', 'enum', 'explicit', 'export', 'extern', 'false',
                'for', 'friend', 'goto', 'if', 'inline', 'mutable', 'namespace', 'new', 'noexcept', 'nullptr',
                'operator', 'private', 'protected', 'public', 'requires', 'return', 'sizeof', 'static',
                'static_assert', 'struct', 'switch', 'template', 'this', 'thread_local', 'throw', 'true', 'try',
                'typedef', 'typename', 'union', 'using', 'virtual', 'volatile', 'while'
            ]);
        }
        return this._cppKeywordSet;
    }

    _getCppTypeSet() {
        if (!this._cppTypeSet) {
            this._cppTypeSet = new Set([
                'bool', 'char', 'char8_t', 'char16_t', 'char32_t', 'double', 'float', 'int', 'long', 'short',
                'signed', 'size_t', 'ssize_t', 'std', 'string', 'string_view', 'uint8_t', 'uint16_t', 'uint32_t',
                'uint64_t', 'int8_t', 'int16_t', 'int32_t', 'int64_t', 'void', 'wchar_t'
            ]);
        }
        return this._cppTypeSet;
    }

    _getCppNonFunctionWordSet() {
        if (!this._cppNonFunctionWordSet) {
            this._cppNonFunctionWordSet = new Set([
                'if', 'for', 'while', 'switch', 'catch', 'return', 'sizeof', 'alignof', 'decltype', 'new', 'delete'
            ]);
        }
        return this._cppNonFunctionWordSet;
    }

    _formatInlineMarkdown(text) {
        const escaped = this.escapeHtml(String(text || ''));
        const inlineCodes = [];
        let html = escaped.replace(/`([^`\n]+)`/g, (_match, code) => {
            const codeIndex = inlineCodes.length;
            inlineCodes.push(`<code>${code}</code>`);
            return `@@INLINE_CODE_${codeIndex}@@`;
        });

        html = html
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/__([^_]+)__/g, '<strong>$1</strong>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        html = html.replace(/@@INLINE_CODE_(\d+)@@/g, (_match, index) => {
            return inlineCodes[Number(index)] || '';
        });

        return html;
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
        let streamComplete = false;

        while (true) {
            const { done, value } = await this._readChunkWithTimeout(reader, STREAM_IDLE_TIMEOUT_MS);
            if (done) {
                const flushResult = this._consumeSSEBuffer(buffer, fullText, contentDiv, (updatedText) => {
                    fullText = updatedText;
                    gotContent = gotContent || Boolean((fullText || '').trim());
                });
                fullText = flushResult.fullText;
                gotContent = gotContent || Boolean((contentDiv.innerHTML || '').trim());
                streamComplete = streamComplete || flushResult.streamComplete;
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const parseResult = this._consumeSSEBuffer(buffer, fullText, contentDiv, (updatedText) => {
                fullText = updatedText;
                gotContent = gotContent || Boolean((fullText || '').trim());
            });
            fullText = parseResult.fullText;
            buffer = parseResult.tail;
            gotContent = gotContent || Boolean((contentDiv.innerHTML || '').trim());
            streamComplete = streamComplete || parseResult.streamComplete;
            if (streamComplete) {
                try {
                    await reader.cancel();
                } catch (e) {
                    // ignore cancellation errors
                }
                break;
            }
        }

        if (!gotContent) {
            const fallback = await this._callNonStreamAPI(message);
            if (Array.isArray(fallback.blocks) && fallback.blocks.length > 0) {
                contentDiv.innerHTML = this.renderBlocks(fallback.blocks);
            } else {
                contentDiv.innerHTML = this.formatMessage(fallback.response);
            }
            if (fallback.sources && fallback.sources.length > 0) {
                this.addSources(fallback.sources);
            }
            this.scrollToBottom();
        }
    }

    _consumeSSEBuffer(buffer, currentText, contentDiv, onTextUpdate) {
        const lines = buffer.split('\n');
        const tail = lines.pop() || '';
        let fullText = currentText || '';
        let streamComplete = false;

        for (const rawLine of lines) {
            const line = rawLine.trimEnd();
            if (!line.startsWith('data:')) continue;
            const payload = line.replace(/^data:\s*/, '');
            if (!payload) continue;

            try {
                const data = JSON.parse(payload);
                const blocks = Array.isArray(data.blocks) ? data.blocks : [];
                const replaceText = this._coerceText(data.replace);
                if (replaceText) {
                    fullText = replaceText;
                    if (blocks.length > 0) {
                        contentDiv.innerHTML = this.renderBlocks(blocks);
                    } else {
                        contentDiv.innerHTML = this.formatMessage(fullText);
                    }
                    this.scrollToBottom();
                    onTextUpdate(fullText);
                }
                const chunkText = this._coerceText(data.content);
                if (chunkText) {
                    fullText += chunkText;
                    contentDiv.innerHTML = this.formatMessage(fullText);
                    this.scrollToBottom();
                    onTextUpdate(fullText);
                }
                if (data.done && data.sources && data.sources.length > 0) {
                    this.addSources(data.sources);
                }
                if (data.done && blocks.length > 0) {
                    contentDiv.innerHTML = this.renderBlocks(blocks);
                    this.scrollToBottom();
                    onTextUpdate(fullText);
                }
                if (data.done) {
                    streamComplete = true;
                }
                if (data.error) {
                    contentDiv.innerHTML = this.formatMessage('抱歉，生成回答时出错了。');
                    onTextUpdate(contentDiv.textContent || '');
                    streamComplete = true;
                }
            } catch (e) {
                // ignore malformed chunk
            }
        }
        return { tail, streamComplete, fullText };
    }

    async _callNonStreamAPI(message, timeoutMs = STREAM_CONNECT_TIMEOUT_MS) {
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
            timeoutMs,
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

        const body = await response.json();
        const responseText = this._coerceText(body.response).trim();
        const blocks = Array.isArray(body.blocks) ? body.blocks : [];
        return {
            response: responseText || '抱歉，未返回可显示内容。',
            blocks,
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

    _isConnectTimeoutError(error) {
        if (!error || !error.message) return false;
        return String(error.message).includes('连接 AI 服务超时');
    }

    _coerceText(value) {
        if (value === null || value === undefined) return '';
        if (typeof value === 'string') return value;
        if (Array.isArray(value)) {
            return value.map(item => this._coerceText(item)).join('');
        }
        if (typeof value === 'object') {
            return this._coerceText(value.text || value.content || value.reasoning_content || '');
        }
        return String(value);
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

    async _copyCodeText(text, button) {
        const copyText = String(text || '');
        if (!copyText) return;

        const previousText = button.textContent;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(copyText);
            } else {
                this._fallbackCopyText(copyText);
            }
            button.textContent = '已复制';
            button.classList.add('copied');
        } catch (_error) {
            button.textContent = '复制失败';
            button.classList.add('copy-failed');
        } finally {
            window.setTimeout(() => {
                button.textContent = previousText || '复制';
                button.classList.remove('copied', 'copy-failed');
            }, 1200);
        }
    }

    _fallbackCopyText(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', 'readonly');
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.pointerEvents = 'none';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
