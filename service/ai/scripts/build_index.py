#!/usr/bin/env python3
"""构建/重建向量索引"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging, get_logger
from src.config import settings
from src.core.vector_store import VectorStoreManager

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Build Galay vector index")
    parser.add_argument("--force", action="store_true", help="Force rebuild (delete existing index)")
    args = parser.parse_args()

    setup_logging(settings.LOG_LEVEL)

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is required. Set it in .env file.")
        sys.exit(1)

    valid_paths = settings.validate_docs_paths()
    logger.info(f"Found {len(valid_paths)} valid documentation paths:")
    for p in valid_paths:
        logger.info(f"  - {p}")

    if not valid_paths:
        logger.error("No valid documentation paths found")
        sys.exit(1)

    vs = VectorStoreManager()
    vs.initialize(force_rebuild=args.force)

    logger.info("Index build complete!")

    # 简单验证
    test_query = "galay"
    results = vs.search(test_query, k=2)
    logger.info(f"Verification: search '{test_query}' returned {len(results)} results")


if __name__ == "__main__":
    main()
