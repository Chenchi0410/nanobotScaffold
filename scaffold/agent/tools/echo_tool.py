"""
示例工具：Echo — 回显输入。

展示如何创建一个 Tool：继承基类，实现 4 个属性/方法。
"""

from __future__ import annotations

from typing import Any

from scaffold.agent.tools.base import Tool


class EchoTool(Tool):
    """回显工具：返回输入的文本。"""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo back the input text. Useful for testing."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to echo back",
                },
            },
            "required": ["text"],
        }

    async def execute(self, **kwargs: Any) -> str:
        text = kwargs.get("text", "")
        return f"Echo: {text}"
