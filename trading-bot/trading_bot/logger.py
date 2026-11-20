from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def get_logger(name: str = "trading_bot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    log_dir = ROOT_DIR / "state"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "trading_bot.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
