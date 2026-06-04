"""
模式 1（复用）：Tool 自动发现 — 与 Channel 完全相同的模式

这就是通用脚手架的核心：同样的 pkgutil 扫描模式，
换了基类就变成了 Tool 的发现器。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from loguru import logger

from scaffold.agent.tools.base import Tool
from scaffold.agent.tools.registry import ToolRegistry

# 基础设施模块，不是工具实现
_SKIP_MODULES = frozenset({"base", "registry", "loader", "__init__"})


class ToolLoader:
    """
    工具自动发现和注册。

    用法：
        loader = ToolLoader()
        registry = ToolRegistry()
        loader.load(registry)  # 自动扫描 tools/ 目录，注册所有 Tool 子类
    """

    def __init__(self, package: Any = None) -> None:
        if package is None:
            import scaffold.agent.tools as _pkg
            package = _pkg
        self._package = package

    def discover(self) -> list[type[Tool]]:
        """扫描包目录，找到所有 Tool 子类（不执行注册）。"""
        seen: set[int] = set()
        results: list[type[Tool]] = []

        for _, module_name, _ in pkgutil.iter_modules(self._package.__path__):
            if module_name in _SKIP_MODULES:
                continue
            try:
                module = importlib.import_module(f".{module_name}", self._package.__name__)
            except Exception:
                logger.exception("Failed to import tool module: %s", module_name)
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Tool)
                    and attr is not Tool
                    and not attr_name.startswith("_")
                    and not getattr(attr, "__abstractmethods__", None)
                    and getattr(attr, "_discoverable", True)
                    and id(attr) not in seen
                ):
                    seen.add(id(attr))
                    results.append(attr)

        results.sort(key=lambda cls: cls.__name__)
        return results

    def load(self, registry: ToolRegistry) -> list[str]:
        """发现并注册所有工具到注册表。返回注册的工具名列表。"""
        registered: list[str] = []
        for tool_cls in self.discover():
            try:
                tool = tool_cls()
                registry.register(tool)
                registered.append(tool.name)
            except Exception:
                logger.exception("Failed to register tool: %s", tool_cls.__name__)
        return registered
