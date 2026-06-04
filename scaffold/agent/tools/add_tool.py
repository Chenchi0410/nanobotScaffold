"""
示例工具：Add — 加法计算。

展示 JSON Schema 参数定义和数值类型验证。
"""

from __future__ import annotations

from typing import Any

from scaffold.agent.tools.base import Tool


class AddTool(Tool):
    """加法工具：计算两个数的和。"""

    @property
    def name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Add two numbers together."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"],
        }

    async def execute(self, **kwargs: Any) -> str:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        return str(a + b)
