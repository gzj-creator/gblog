#!/usr/bin/env python3
"""Generate markdown docs for AI indexing from frontend galay-*.html docs."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


BODY_PATTERN = re.compile(
    r'<div class="docs-article-body">\s*(.*?)\s*</div>\s*</article>',
    re.DOTALL,
)


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def convert_inline(text: str) -> str:
    text = re.sub(
        r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: f"[{strip_tags(m.group(2)).strip()}]({m.group(1)})",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(
        r"<code>(.*?)</code>",
        lambda m: f"`{html.unescape(strip_tags(m.group(1)).strip())}`",
        text,
        flags=re.DOTALL,
    )
    return text


def convert_blocks(content: str) -> str:
    content = re.sub(
        r"<pre><code>(.*?)</code></pre>",
        lambda m: "\n```\n" + html.unescape(m.group(1).strip()) + "\n```\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<h1>(.*?)</h1>",
        lambda m: "\n# " + html.unescape(strip_tags(m.group(1)).strip()) + "\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<h2>(.*?)</h2>",
        lambda m: "\n## " + html.unescape(strip_tags(m.group(1)).strip()) + "\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<h3>(.*?)</h3>",
        lambda m: "\n### " + html.unescape(strip_tags(m.group(1)).strip()) + "\n",
        content,
        flags=re.DOTALL,
    )

    def convert_list(match: re.Match[str]) -> str:
        items = re.findall(r"<li>(.*?)</li>", match.group(1), flags=re.DOTALL)
        lines: list[str] = []
        for item in items:
            item = convert_inline(item)
            item = html.unescape(strip_tags(item)).strip()
            if item:
                lines.append(f"- {item}")
        return "\n" + "\n".join(lines) + "\n\n"

    content = re.sub(r"<ul>(.*?)</ul>", convert_list, content, flags=re.DOTALL)
    content = re.sub(
        r"<p>(.*?)</p>",
        lambda m: "\n" + html.unescape(strip_tags(convert_inline(m.group(1)))).strip() + "\n",
        content,
        flags=re.DOTALL,
    )

    content = convert_inline(content)
    content = html.unescape(strip_tags(content))
    return normalize_whitespace(content)


def build_markdown(title: str, source_path: Path, body_html: str) -> str:
    body_md = convert_blocks(body_html)
    source_rel = source_path.as_posix()
    header = (
        f"# {title}\n\n"
        f"> Generated from `{source_rel}` for AI vector indexing.\n\n"
    )
    return header + body_md


def extract_title(file_text: str, fallback: str) -> str:
    m = re.search(r'<h1 class="docs-article-title">(.*?)</h1>', file_text, flags=re.DOTALL)
    if m:
        return html.unescape(strip_tags(m.group(1)).strip())
    return fallback


def generate(input_dir: Path, output_dir: Path) -> int:
    html_files = sorted(input_dir.glob("galay-*.html"))
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for src in html_files:
        text = src.read_text(encoding="utf-8")
        body_match = BODY_PATTERN.search(text)
        if not body_match:
            continue

        module_name = src.stem  # galay-kernel
        title = extract_title(text, module_name)
        markdown = build_markdown(title, src, body_match.group(1))

        module_dir = output_dir / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "README.md").write_text(markdown, encoding="utf-8")
        generated += 1

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate galay markdown docs for AI indexing")
    parser.add_argument(
        "--input-dir",
        default="frontend/docs",
        help="Source docs directory containing galay-*.html",
    )
    parser.add_argument(
        "--output-dir",
        default="repos",
        help="Output directory with galay-* subdirectories and README.md",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    generated = generate(input_dir, output_dir)
    print(f"Generated {generated} markdown files into: {output_dir}")


if __name__ == "__main__":
    main()
