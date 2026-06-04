"""
配置加载器 — 从文件加载配置。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from scaffold.config.schema import AppConfig

_DEFAULT_CONFIG_PATH = Path.home() / ".scaffold" / "config.json"


def load_config(path: str | Path | None = None) -> AppConfig:
    """
    加载配置文件。

    优先级：指定路径 > 默认路径 > 空配置（使用默认值）
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            return AppConfig(**raw)
        except Exception as e:
            logger.warning("Failed to load config from {}: {}", config_path, e)

    logger.info("No config found, using defaults")
    return AppConfig()
