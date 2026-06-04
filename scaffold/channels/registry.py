"""
模式 1：渠道自动发现 — pkgutil 扫描 + entry_points 插件

这是整个项目最核心的脚手架代码，同样的模式在 providers/ 和 agent/tools/ 中复用。

设计要点：
  1. discover_channel_names() — 只扫描目录名，不导入模块（廉价）
  2. load_channel_class() — 按需导入，找到第一个 BaseChannel 子类
  3. discover_plugins() — 通过 entry_points 发现外部插件
  4. discover_enabled() — 合并内置 + 外部，内置优先
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from scaffold.channels.base import BaseChannel

# 这些是基础设施模块，不是渠道实现
_INTERNAL = frozenset({"base", "manager", "registry"})


def discover_channel_names() -> list[str]:
    """扫描 channels/ 包，返回所有模块名（不导入任何模块）。"""
    import scaffold.channels as pkg

    return [
        name
        for _, name, ispkg in pkgutil.iter_modules(pkg.__path__)
        if name not in _INTERNAL and not ispkg
    ]


def load_channel_class(module_name: str) -> type[BaseChannel]:
    """导入指定模块，返回其中第一个 BaseChannel 子类。"""
    from scaffold.channels.base import BaseChannel as _Base

    mod = importlib.import_module(f"scaffold.channels.{module_name}")
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if isinstance(obj, type) and issubclass(obj, _Base) and obj is not _Base:
            return obj
    raise ImportError(f"No BaseChannel subclass in scaffold.channels.{module_name}")


def discover_plugins(enabled_names: set[str] | None = None) -> dict[str, type[BaseChannel]]:
    """通过 entry_points 发现外部渠道插件。"""
    from importlib.metadata import entry_points

    plugins: dict[str, type[BaseChannel]] = {}
    for ep in entry_points(group="scaffold.channels"):
        if enabled_names is not None and ep.name not in enabled_names:
            continue
        try:
            cls = ep.load()
            plugins[ep.name] = cls
        except Exception as e:
            logger.warning("Failed to load channel plugin '{}': {}", ep.name, e)
    return plugins


def discover_enabled(
    enabled_names: set[str],
    *,
    _names: list[str] | None = None,
) -> dict[str, type[BaseChannel]]:
    """返回 enabled_names 中启用的渠道类。内置渠道优先于外部插件。"""
    names = _names if _names is not None else discover_channel_names()
    result: dict[str, type[BaseChannel]] = {}

    # 内置渠道
    for modname in names:
        if modname not in enabled_names:
            continue
        try:
            result[modname] = load_channel_class(modname)
        except ImportError as e:
            logger.debug("Skipping built-in channel '{}': {}", modname, e)

    # 外部插件（不覆盖内置）
    external = discover_plugins(enabled_names)
    for name, cls in external.items():
        if name not in result:
            result[name] = cls

    return result
