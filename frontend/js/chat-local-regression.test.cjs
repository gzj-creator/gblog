#!/usr/bin/env node
/* eslint-disable no-console */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { TextEncoder } = require('util');

if (typeof Response === 'undefined' || typeof ReadableStream === 'undefined') {
    console.error('Node >= 18 is required to run chat-local regression tests.');
    process.exit(1);
}

function createSandbox() {
    const sandbox = {
        console,
        window: {},
        navigator: {},
        localStorage: { getItem: () => null, setItem: () => {} },
        setTimeout,
        clearTimeout,
        setInterval,
        clearInterval,
        TextEncoder,
        Response,
        ReadableStream,
        document: {
            addEventListener: () => {},
            getElementById: () => ({
                addEventListener: () => {},
                focus: () => {},
                disabled: false,
                value: '',
                innerHTML: '',
                appendChild: () => {},
                querySelector: () => null,
                querySelectorAll: () => [],
                scrollTop: 0,
                scrollHeight: 0,
            }),
            querySelectorAll: () => [],
            createElement: () => ({
                _text: '',
                set textContent(v) {
                    this._text = String(v);
                    this.innerHTML = this._text
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#39;');
                },
                get textContent() {
                    return this._text;
                },
                innerHTML: '',
                appendChild: () => {},
                querySelector: () => null,
                closest: () => null,
                classList: { add: () => {}, remove: () => {} },
                style: {},
                setAttribute: () => {},
                select: () => {},
                remove: () => {},
                value: '',
            }),
            body: { appendChild: () => {}, removeChild: () => {} },
            execCommand: () => true,
        },
    };
    sandbox.window = sandbox;
    return sandbox;
}

function loadRuntime() {
    const jsDir = __dirname;
    const mockSource = fs.readFileSync(path.join(jsDir, 'chat-local-mock.js'), 'utf8');
    const chatSource = fs.readFileSync(path.join(jsDir, 'chat.js'), 'utf8');
    const sandbox = createSandbox();
    vm.createContext(sandbox);
    vm.runInContext(mockSource, sandbox);
    vm.runInContext(`${chatSource}\nthis.ChatApp = ChatApp;`, sandbox);

    const app = Object.create(sandbox.ChatApp.prototype);
    app.escapeHtml = (text) =>
        String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    app.addSources = () => {};
    app.scrollToBottom = () => {};

    return { app, mock: sandbox.__chatLocalMock };
}

function assertCase(name, condition) {
    if (!condition) {
        throw new Error(`FAILED: ${name}`);
    }
    console.log(`PASS: ${name}`);
}

function run() {
    const { app, mock } = loadRuntime();

    const rawCase = mock.resolveMockOutput(':case raw_cmake');
    const rawHtml = app.formatMessage(rawCase.answer);
    assertCase('raw_cmake heading', /<h2>环境要求<\/h2>/.test(rawHtml));
    assertCase('raw_cmake code blocks', (rawHtml.match(/class="code-block"/g) || []).length === 3);
    assertCase('raw_cmake CMake plain text', /CMake 3\.20\+ 构建系统/.test(rawHtml));

    const quoted = mock.resolveMockOutput(':case quoted_fence');
    const quotedHtml = app.formatMessage(quoted.answer);
    assertCase('quoted_fence code block', /class="code-block"/.test(quotedHtml));

    const repeated = mock.resolveMockOutput(':case repeated_ol');
    const repeatedHtml = app.formatMessage(repeated.answer);
    assertCase(
        'repeated_ol single ordered list',
        /<ol><li>第一项：环境要求<\/li><li>第二项：安装命令<\/li><li>第三项：最小示例<\/li><li>第四项：运行验证<\/li><\/ol>/.test(
            repeatedHtml
        )
    );

    const mix = mock.resolveMockOutput(':case cpp_bash_mix');
    const mixHtml = app.formatMessage(mix.answer);
    assertCase('cpp_bash_mix block count', (mixHtml.match(/class="code-block"/g) || []).length === 2);
    assertCase('cpp_bash_mix cpp label', /class="code-lang">cpp<\/span>/.test(mixHtml));
    assertCase('cpp_bash_mix bash label', /class="code-lang">bash<\/span>/.test(mixHtml));

    let updatedText = '';
    const contentDiv = { innerHTML: '' };
    const parse = app._consumeSSEBuffer(
        'data: {"content":"脏文本"}\n' +
            'data: {"replace":"## 标题\\n```bash\\ncmake -S . -B build\\n```","blocks":[{"type":"heading","level":2,"text":"标题"},{"type":"code","language":"bash","code":"cmake -S . -B build"}]}\n' +
            'data: {"done":true,"sources":[{"project":"local"}],"blocks":[{"type":"heading","level":2,"text":"标题"},{"type":"code","language":"bash","code":"cmake -S . -B build"}]}\n\n',
        '',
        contentDiv,
        (value) => {
            updatedText = value;
        }
    );

    assertCase('replace path final text', updatedText.startsWith('## 标题'));
    assertCase('replace path code block', /code-block/.test(contentDiv.innerHTML));
    assertCase('replace path done', parse.streamComplete === true);

    const contentDiv2 = { innerHTML: '' };
    let updatedText2 = '';
    const parse2 = app._consumeSSEBuffer(
        'data: {"done":true,"sources":[{"project":"local"}],"blocks":[{"type":"heading","level":2,"text":"仅结构化结果"},{"type":"list","ordered":false,"items":["A","B"]}]}\n\n',
        '',
        contentDiv2,
        (value) => {
            updatedText2 = value;
        }
    );
    assertCase('done-only blocks render heading', /仅结构化结果/.test(contentDiv2.innerHTML));
    assertCase('done-only blocks render list', /<li>A<\/li><li>B<\/li>/.test(contentDiv2.innerHTML));
    assertCase('done-only blocks stream complete', parse2.streamComplete === true);
    assertCase('done-only blocks keep text state stable', updatedText2 === '');

    const contentDiv3 = { innerHTML: '' };
    let updatedText3 = '';
    const parse3 = app._consumeSSEBuffer(
        'data: {"replace":"## 逐步\\n- A","blocks":[{"type":"heading","level":2,"text":"逐步"},{"type":"list","ordered":false,"items":["A"]}],"partial":true}\n' +
            'data: {"replace":"## 逐步\\n- A\\n- B","blocks":[{"type":"heading","level":2,"text":"逐步"},{"type":"list","ordered":false,"items":["A","B"]}],"partial":true}\n' +
            'data: {"done":true,"sources":[],"blocks":[{"type":"heading","level":2,"text":"逐步"},{"type":"list","ordered":false,"items":["A","B"]}]}\n\n',
        '',
        contentDiv3,
        (value) => {
            updatedText3 = value;
        }
    );
    assertCase('partial replace stream renders final list', /<li>A<\/li><li>B<\/li>/.test(contentDiv3.innerHTML));
    assertCase('partial replace stream completes', parse3.streamComplete === true);
    assertCase('partial replace updates text', updatedText3.includes('A'));
}

try {
    run();
    console.log('[chat-local-regression] PASS');
} catch (error) {
    console.error(`[chat-local-regression] ${error.message}`);
    process.exit(1);
}
