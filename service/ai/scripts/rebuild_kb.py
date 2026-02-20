#!/usr/bin/env python3
"""One-shot knowledge base rebuild helper."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> None:
    print(f"[RUN] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Galay AI knowledge base")
    parser.add_argument("--force", action="store_true", help="Force rebuild vector index")
    parser.add_argument(
        "--generate-docs",
        action="store_true",
        help="Generate markdown docs from frontend/docs/galay-*.html before indexing",
    )
    parser.add_argument(
        "--docs-html-dir",
        default="frontend/docs",
        help="Input directory for galay-*.html docs (relative to repo root)",
    )
    parser.add_argument(
        "--docs-output-dir",
        default="repos",
        help="Output directory for generated markdown docs (relative to repo root)",
    )
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    ai_dir = scripts_dir.parent
    repo_root = ai_dir.parent.parent

    if args.generate_docs:
        generator = scripts_dir / "generate_galay_docs.py"
        html_dir = repo_root / args.docs_html_dir
        output_dir = repo_root / args.docs_output_dir
        if html_dir.exists():
            run_cmd(
                [
                    sys.executable,
                    str(generator),
                    "--input-dir",
                    str(html_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
            )
        else:
            print(f"[WARN] Skip docs generation, input dir not found: {html_dir}")

    build_index = scripts_dir / "build_index.py"
    build_cmd = [sys.executable, str(build_index)]
    if args.force:
        build_cmd.append("--force")

    run_cmd(build_cmd, cwd=ai_dir)
    print("[OK] Knowledge base rebuild finished.")


if __name__ == "__main__":
    main()
