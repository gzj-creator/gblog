(function () {
    const AI_STREAM_PATH = '/ai/api/chat/stream';
    const AI_CHAT_PATH = '/ai/api/chat';

    const SOURCES = [
        { project: 'local-mock', file: 'offline://sample.md', file_name: 'sample.md' },
    ];

    const CASES = {
        raw_cmake: {
            streamText:
                '1. 环境要求：- C++20 编译器（GCC 11+/Clang 14+）- CMake 3.20+ 构建系统2. 安装步骤：git clone https://github.com/galay/galay.git 使用 CMake 构建：cmake -S . -B build cmake --build build -j 3. 编译运行命令：g++ -std=c++20 main.cpp -o demo ./demo',
            answer:
                '## 环境要求\n- C++20 编译器（GCC 11+/Clang 14+）\n- CMake 3.20+ 构建系统\n## 安装步骤\n```bash\ngit clone https://github.com/galay/galay.git\n```\n使用 CMake 构建：\n```bash\ncmake -S . -B build\ncmake --build build -j\n```\n## 编译运行命令\n```bash\ng++ -std=c++20 main.cpp -o demo ./demo\n```',
        },
        final_cmake: {
            answer:
                '## 环境要求\n- C++20 编译器（GCC 11+/Clang 14+）\n- CMake 3.20+ 构建系统\n## 安装步骤\n```bash\ngit clone https://github.com/galay/galay.git\n```\n使用 CMake 构建：\n```bash\ncmake -S . -B build\ncmake --build build -j\n```',
        },
        quoted_fence: {
            answer:
                '"```bash"\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\n"```"',
        },
        repeated_ol: {
            answer:
                '1. 第一项：环境要求\n1. 第二项：安装命令\n1. 第三项：最小示例\n1. 第四项：运行验证',
        },
        cpp_bash_mix: {
            answer:
                '## 最小示例\n```cpp\n#include <iostream>\nint main() {\n    std::cout << \"hello\" << std::endl;\n    return 0;\n}\n```\n## 编译运行命令\n```bash\ng++ -std=c++20 main.cpp -o demo\n./demo\n```',
        },
    };

    const HELP_TEXT = [
        '本地格式验证命令：',
        '- `:case raw_cmake`：模拟脏流式文本，并在结束用 replace 覆盖为规范结果',
        '- `:case final_cmake`：直接返回规范 Markdown',
        '- `:case quoted_fence`：测试引号包裹 fence',
        '- `:case repeated_ol`：测试连续 1. 有序列表渲染',
        '- `:case cpp_bash_mix`：测试 C++/Bash 代码块与高亮',
        '- `:raw 你的文本`：原样回显你输入的文本',
    ].join('\n');

    const originalFetch = typeof window.fetch === 'function' ? window.fetch.bind(window) : null;
    const encoder = new TextEncoder();

    function normalizeUrl(input) {
        if (typeof input === 'string') return input;
        if (input && typeof input.url === 'string') return input.url;
        return '';
    }

    function parseBody(init) {
        if (!init || !init.body) return {};
        if (typeof init.body === 'string') {
            try {
                return JSON.parse(init.body);
            } catch (_error) {
                return {};
            }
        }
        return {};
    }

    function markdownToBlocks(text) {
        const lines = String(text || '').replace(/\r\n?/g, '\n').split('\n');
        const blocks = [];

        let paragraph = [];
        let quote = [];
        let listItems = [];
        let listOrdered = false;
        let listStart = 1;
        let expectedOl = null;
        let inCode = false;
        let codeLang = 'text';
        let codeLines = [];

        const flushParagraph = () => {
            if (paragraph.length === 0) return;
            const value = paragraph.join('\n').trim();
            if (value) blocks.push({ type: 'paragraph', text: value });
            paragraph = [];
        };
        const flushQuote = () => {
            if (quote.length === 0) return;
            const value = quote.join('\n').trim();
            if (value) blocks.push({ type: 'blockquote', text: value });
            quote = [];
        };
        const flushList = () => {
            if (listItems.length === 0) return;
            const block = { type: 'list', ordered: listOrdered, items: listItems.slice() };
            if (listOrdered) block.start = listStart;
            blocks.push(block);
            listItems = [];
            listOrdered = false;
            listStart = 1;
            expectedOl = null;
        };
        const flushCode = () => {
            const value = codeLines.join('\n').replace(/\n+$/g, '');
            if (value) blocks.push({ type: 'code', language: codeLang || 'text', code: value });
            codeLines = [];
            codeLang = 'text';
        };
        const flushAll = () => {
            flushParagraph();
            flushQuote();
            flushList();
        };

        for (const rawLine of lines) {
            const line = rawLine.replace(/\s+$/g, '');
            const trimmed = line.trim();

            const fence = trimmed.match(/^```([a-zA-Z0-9_-]*)\s*$/);
            if (fence) {
                if (!inCode) {
                    flushAll();
                    inCode = true;
                    codeLang = (fence[1] || 'text').toLowerCase();
                    codeLines = [];
                    continue;
                }
                if (trimmed === '```') {
                    flushCode();
                    inCode = false;
                    continue;
                }
                codeLines.push(line);
                continue;
            }

            if (inCode) {
                codeLines.push(rawLine);
                continue;
            }

            if (!trimmed) {
                flushAll();
                continue;
            }

            if (/^([-*_])\1{2,}$/.test(trimmed)) {
                flushAll();
                blocks.push({ type: 'hr' });
                continue;
            }

            const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
            if (heading) {
                flushAll();
                blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] });
                continue;
            }

            const q = trimmed.match(/^>\s?(.*)$/);
            if (q) {
                flushParagraph();
                flushList();
                quote.push(q[1]);
                continue;
            }

            const ol = trimmed.match(/^[✅☑️✔️🔥🌟🧠🔧⚙️🛠️📈📌]?\s*(\d+)\.\s+(.+)$/u);
            if (ol) {
                flushParagraph();
                flushQuote();
                const current = Number(ol[1]);
                const itemText = ol[2];
                if (listItems.length === 0 || !listOrdered) {
                    flushList();
                    listOrdered = true;
                    listStart = current;
                    expectedOl = current + 1;
                } else if (expectedOl !== null && current !== expectedOl && current !== 1) {
                    flushList();
                    listOrdered = true;
                    listStart = current;
                    expectedOl = current + 1;
                } else {
                    expectedOl = (expectedOl || current) + 1;
                }
                listItems.push(itemText);
                continue;
            }

            const ul = trimmed.match(/^[-*]\s+(.+)$/);
            if (ul) {
                flushParagraph();
                flushQuote();
                if (listItems.length === 0 || listOrdered) {
                    flushList();
                    listOrdered = false;
                }
                listItems.push(ul[1]);
                continue;
            }

            flushQuote();
            flushList();
            paragraph.push(trimmed);
        }

        if (inCode) flushCode();
        else flushAll();

        return blocks;
    }

    function resolveMockOutput(message) {
        const raw = String(message || '');
        const trimmed = raw.trim();

        if (!trimmed) {
            const answer = '（空输入）';
            return { answer, streamText: '', blocks: markdownToBlocks(answer) };
        }

        if (trimmed === ':help') {
            return { answer: HELP_TEXT, streamText: HELP_TEXT, blocks: markdownToBlocks(HELP_TEXT) };
        }

        const caseMatch = trimmed.match(/^:case\s+([a-z0-9_-]+)$/i);
        if (caseMatch) {
            const key = caseMatch[1].toLowerCase();
            const found = CASES[key];
            if (found) {
                const answer = found.answer;
                return {
                    answer,
                    streamText: found.streamText || answer,
                    blocks: found.blocks || markdownToBlocks(answer),
                };
            }
            const answer = `未找到样例：${key}\n\n可先发送 :help 查看命令。`;
            return {
                answer,
                streamText: `未找到样例：${key}`,
                blocks: markdownToBlocks(answer),
            };
        }

        if (trimmed.startsWith(':raw ')) {
            const literal = raw.slice(raw.indexOf(':raw ') + 5);
            return { answer: literal, streamText: literal, blocks: markdownToBlocks(literal) };
        }

        return { answer: raw, streamText: raw, blocks: markdownToBlocks(raw) };
    }

    function splitStreamChunks(text) {
        const source = String(text || '');
        if (!source) return [];

        const chunks = [];
        let current = '';
        for (const char of source) {
            current += char;
            if (current.length >= 20 && /[\n。！？!?；;]/.test(char)) {
                chunks.push(current);
                current = '';
                continue;
            }
            if (current.length >= 56) {
                chunks.push(current);
                current = '';
            }
        }
        if (current) chunks.push(current);
        return chunks;
    }

    function createSseResponse(streamText, answer, blocks) {
        const chunks = splitStreamChunks(streamText);
        return new ReadableStream({
            start(controller) {
                const push = (payload) => {
                    const data = `data: ${JSON.stringify(payload)}\n\n`;
                    controller.enqueue(encoder.encode(data));
                };

                let index = 0;
                let partial = '';
                const timer = setInterval(() => {
                    if (index < chunks.length) {
                        partial += chunks[index];
                        push({
                            replace: partial,
                            blocks: markdownToBlocks(partial),
                            partial: true,
                        });
                        index += 1;
                        return;
                    }

                    clearInterval(timer);
                    push({ replace: answer, blocks });
                    push({ done: true, sources: SOURCES, blocks });
                    controller.close();
                }, 30);
            },
        });
    }

    function buildJsonResponse(answer, blocks) {
        return JSON.stringify({
            success: true,
            response: answer,
            blocks: Array.isArray(blocks) ? blocks : [],
            sources: SOURCES,
            session_id: 'local-preview-session',
        });
    }

    window.__chatLocalMock = {
        resolveMockOutput,
        CASES,
        HELP_TEXT,
    };

    window.fetch = async function localFetch(input, init) {
        const url = normalizeUrl(input);
        const body = parseBody(init);
        const message = body.message || '';
        const resolved = resolveMockOutput(message);

        if (url.endsWith(AI_STREAM_PATH)) {
            return new Response(createSseResponse(resolved.streamText, resolved.answer, resolved.blocks), {
                status: 200,
                headers: {
                    'Content-Type': 'text/event-stream; charset=utf-8',
                    'Cache-Control': 'no-cache',
                },
            });
        }

        if (url.endsWith(AI_CHAT_PATH)) {
            return new Response(buildJsonResponse(resolved.answer, resolved.blocks), {
                status: 200,
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                },
            });
        }

        if (originalFetch) {
            return originalFetch(input, init);
        }

        throw new Error('No fetch handler available in local preview mode');
    };

    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', () => {
            const clearBtn = document.getElementById('clearChatBtn');
            const chatMessages = document.getElementById('chatMessages');
            if (!clearBtn || !chatMessages) return;

            clearBtn.addEventListener('click', () => {
                const items = Array.from(chatMessages.querySelectorAll('.message'));
                items.forEach((node, index) => {
                    if (index === 0) return;
                    node.remove();
                });
            });
        });
    }
})();
