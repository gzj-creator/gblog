#!/usr/bin/env python3

import argparse
import os
import sys

import uvicorn

# Ensure service root is importable when running as `python scripts/run_server.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run admin service")
    parser.add_argument("--host", default=settings.HOST)
    parser.add_argument("--port", type=int, default=settings.PORT)
    parser.add_argument("--reload", action="store_true", default=False)
    args = parser.parse_args()

    uvicorn.run("src.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
