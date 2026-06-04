"""
Tool 注册表 — 存储和执行工具。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from scaffold.agent.tools.base import Tool


class ToolRegistry:
    """
    工具注册表。

    支持动态注册、查找、执行工具。
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具。"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名称查找工具。"""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    async def execute(self, name: str, params: dict[str, Any]) -> Any:
        """执行指定工具。"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"

        errors = tool.validate_params(params)
        if errors:
            return f"Error: Invalid parameters: {'; '.join(errors)}"

        try:
            result = await tool.execute(**params)
            return result
        except Exception as e:
            return f"Error executing {name}: {e}"

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI 函数定义，用于传给 LLM。"""
        return [tool.to_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)
