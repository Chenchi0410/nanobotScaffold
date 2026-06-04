"""
模式 6：Facade 门面 — 对外暴露的唯一入口

设计要点：
  - 把 AgentLoop、Provider、Tools、Session 等复杂内部结构全部隐藏
  - 外部用户只需要 Nanobot.from_config() + bot.run()
  - 这是 SDK 设计的关键：内部复杂，外部简单
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scaffold.agent.hook import AgentHook, SDKCaptureHook
from scaffold.agent.loop import AgentLoop


@dataclass(slots=True)
class RunResult:
    """SDK 返回的运行结果。"""

    content: str
    tools_used: list[str] = field(default_factory=list)
    iterations: int = 0


class Nanobot:
    """
    门面类 — 对外暴露的唯一入口。

    用法：
        # 最简用法
        bot = Nanobot.from_config()
        result = await bot.run("hello")
        print(result.content)

        # 带自定义 Hook
        bot = Nanobot.from_config(config)
        result = await bot.run("summarize this", hooks=[MyHook()])
    """

    def __init__(self, loop: AgentLoop) -> None:
        self._loop = loop

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any] | None = None,
    ) -> Nanobot:
        """
        从配置创建 Nanobot 实例。

        config 为 None 时使用默认配置（Demo Provider）。
        """
        config = config or {"provider": "demo", "model": "demo-model"}
        loop = AgentLoop.from_config(config)
        return cls(loop)

    async def run(
        self,
        message: str,
        *,
        session_key: str = "sdk:default",
        hooks: list[AgentHook] | None = None,
    ) -> RunResult:
        """
        运行一次对话并返回结果。

        Args:
            message: 用户消息
            session_key: 会话标识（不同 key 独立历史）
            hooks: 可选的生命周期 Hook

        Returns:
            RunResult 包含响应内容、使用的工具、迭代次数
        """
        capture = SDKCaptureHook()
        base_hooks = list(hooks) if hooks else []
        original = self._loop.hook

        # 临时注入 SDK Hook
        from scaffold.agent.hook import CompositeHook
        self._loop.hook = CompositeHook([capture, *base_hooks, original])
        try:
            result = await self._loop.run_once(message, session_key=session_key)
        finally:
            self._loop.hook = original

        return RunResult(
            content=result.content,
            tools_used=capture.tools_used,
            iterations=result.iterations,
        )
