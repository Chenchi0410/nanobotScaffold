"""
模式 3：生命周期 Hook — 观察者模式 + 组合模式

设计要点：
  - AgentHook 定义 5 个生命周期钩子，子类只需覆盖关心的方法
  - CompositeHook 把多个 Hook 组合在一起，扇出调用
  - _for_each_hook_safe() 做错误隔离：单个 Hook 异常不影响其他
  - SDKCaptureHook 是一个具体 Hook 示例：收集运行数据，不侵入核心逻辑
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass(slots=True)
class AgentHookContext:
    """每次 LLM 迭代的上下文，Hook 可以读取和修改。"""

    iteration: int
    messages: list[dict[str, Any]]
    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[Any] = field(default_factory=list)
    error: str | None = None


class AgentHook:
    """
    Hook 基类。子类只需覆盖关心的方法。

    用法：
        class MyHook(AgentHook):
            async def before_iteration(self, ctx):
                print(f"第 {ctx.iteration} 轮开始")

            async def after_iteration(self, ctx):
                print(f"第 {ctx.iter轮结束，内容: {ctx.content}")
    """

    def __init__(self, reraise: bool = False) -> None:
        self._reraise = reraise  # True 时异常会冒泡，不被 CompositeHook 吞掉

    async def before_iteration(self, context: AgentHookContext) -> None:
        """每次 LLM 调用之前。"""
        pass

    async def after_iteration(self, context: AgentHookContext) -> None:
        """每次 LLM 调用之后。"""
        pass

    async def before_tool_execution(self, context: AgentHookContext) -> None:
        """工具执行之前。"""
        pass

    async def on_error(self, context: AgentHookContext) -> None:
        """发生错误时。"""
        pass

    def finalize_content(self, context: AgentHookContext, content: str | None) -> str | None:
        """内容后处理管道。返回修改后的内容。"""
        return content


class CompositeHook(AgentHook):
    """
    组合多个 Hook，扇出调用。

    核心特性：错误隔离 — 单个 Hook 异常不会崩溃整个循环。

    用法：
        hook = CompositeHook([LogHook(), MetricsHook(), CustomHook()])
        await hook.before_iteration(ctx)  # 会依次调用每个 Hook
    """

    __slots__ = ("_hooks",)

    def __init__(self, hooks: list[AgentHook]) -> None:
        super().__init__()
        self._hooks = list(hooks)

    async def _for_each_hook_safe(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """依次调用每个 Hook 的指定方法，单个失败不影响其他。"""
        for h in self._hooks:
            if getattr(h, "_reraise", False):
                # reraise=True 的 Hook 不做隔离，异常直接冒泡
                await getattr(h, method_name)(*args, **kwargs)
                continue
            try:
                await getattr(h, method_name)(*args, **kwargs)
            except Exception:
                logger.exception("Hook.{} error in {}", method_name, type(h).__name__)

    async def before_iteration(self, context: AgentHookContext) -> None:
        await self._for_each_hook_safe("before_iteration", context)

    async def after_iteration(self, context: AgentHookContext) -> None:
        await self._for_each_hook_safe("after_iteration", context)

    async def before_tool_execution(self, context: AgentHookContext) -> None:
        await self._for_each_hook_safe("before_tool_execution", context)

    async def on_error(self, context: AgentHookContext) -> None:
        await self._for_each_hook_safe("on_error", context)

    def finalize_content(self, context: AgentHookContext, content: str | None) -> str | None:
        """管道模式：依次通过每个 Hook 处理内容。"""
        for h in self._hooks:
            content = h.finalize_content(context, content)
        return content


# ---- 具体 Hook 示例 ----

class LogHook(AgentHook):
    """日志 Hook：记录每次迭代的输入输出。"""

    async def before_iteration(self, context: AgentHookContext) -> None:
        logger.info("[LogHook] Iteration {} started, {} messages", context.iteration, len(context.messages))

    async def after_iteration(self, context: AgentHookContext) -> None:
        logger.info("[LogHook] Iteration {} finished, content: {}", context.iteration, (context.content or "")[:80])


class SDKCaptureHook(AgentHook):
    """SDK 数据采集 Hook：收集工具调用和消息，供 RunResult 使用。"""

    def __init__(self) -> None:
        super().__init__()
        self.tools_used: list[str] = []
        self.messages: list[dict[str, Any]] = []

    async def after_iteration(self, context: AgentHookContext) -> None:
        for call in context.tool_calls:
            self.tools_used.append(call.get("name", "unknown"))
        self.messages = list(context.messages)
