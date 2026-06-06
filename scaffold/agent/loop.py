"""
Agent 核心循环 — 把所有脚手架模式组装在一起。

这个文件展示了各个模式如何协同工作：
  - 用 ToolLoader 自动发现工具 → ToolRegistry
  - 用 make_provider 根据配置创建 Provider
  - 用 CompositeHook 管理生命周期
  - 用 EventBus 接收消息和发送响应
  - 用 SessionManager 管理会话历史
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from scaffold.agent.hook import AgentHook, AgentHookContext, CompositeHook
from scaffold.agent.tools.loader import ToolLoader
from scaffold.agent.tools.registry import ToolRegistry
from scaffold.bus.events import InboundMessage, OutboundMessage
from scaffold.bus.queue import EventBus
from scaffold.providers.base import LLMProvider, LLMResponse
from scaffold.providers.factory import make_provider
from scaffold.session.manager import SessionManager


@dataclass
class RunResult:
    """一次 Agent 运行的结果。"""

    content: str = ""
    tools_used: list[str] = field(default_factory=list)
    iterations: int = 0


class AgentLoop:
    """
    Agent 核心循环。

    展示了如何把 6 个脚手架模式组装成一个可工作的系统。
    """

    def __init__(
        self,
        provider: LLMProvider,
        bus: EventBus,
        tools: ToolRegistry,
        hook: CompositeHook,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.bus = bus
        self.tools = tools
        self.hook = hook
        self.config = config or {}
        self.session_manager = SessionManager()

    @classmethod
    def from_config(cls, config_dict: dict[str, Any]) -> AgentLoop:
        """
        工厂方法：从配置创建完整的 AgentLoop。

        这是模式 5（配置驱动工厂）的体现。
        """
        # 1. 创建 Provider（策略模式 + 工厂）
        provider = make_provider(config_dict)

        # 2. 创建消息总线（模式 2）
        bus = EventBus()

        # 3. 自动发现并注册工具（模式 1）
        tools = ToolRegistry()
        loader = ToolLoader()
        registered = loader.load(tools)
        logger.info("Discovered tools: {}", registered)

        # 4. 创建 Hook 组合（模式 3）
        from scaffold.agent.hook import LogHook
        hook = CompositeHook([LogHook()])

        return cls(provider=provider, bus=bus, tools=tools, hook=hook, config=config_dict)

    async def run_once(self, message: str, session_key: str = "default") -> RunResult:
        """
        运行一次对话（不经过消息总线，直接调用）。

        用于 SDK / 测试场景。
        """
        session = self.session_manager.get_or_create(session_key)
        session.add_message("user", message)

        result = RunResult()
        max_iter = self.config.get("agents", {}).get("max_iterations", 10)

        for i in range(max_iter):
            ctx = AgentHookContext(iteration=i, messages=session.messages)

            # Hook: before_iteration
            await self.hook.before_iteration(ctx)

            # 调用 LLM（带重试）
            # model 优先级：config["agents"]["model"] > config["model"] > provider 默认
            model = self.config.get("agents", {}).get("model") or self.config.get("model")
            response = await self.provider.chat_with_retry(
                messages=session.messages,
                model=model,
            )

            if not response.ok:
                ctx.error = response.content
                await self.hook.on_error(ctx)
                result.content = f"Error: {response.content}"
                break

            ctx.content = response.content
            result.iterations = i + 1

            # 检查是否有工具调用
            if response.has_tool_calls:
                session.add_message("assistant", response.content or "", tool_calls=response.tool_calls)
                ctx.tool_calls = response.tool_calls

                await self.hook.before_tool_execution(ctx)

                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("arguments", {})
                    tool_result = await self.tools.execute(tool_name, tool_args)
                    session.add_message("tool", str(tool_result), tool_call_id=tc.get("id"))
                    result.tools_used.append(tool_name)
            else:
                # 没有工具调用，结束循环
                content = self.hook.finalize_content(ctx, response.content)
                session.add_message("assistant", content or "")
                result.content = content or ""
                break

            # Hook: after_iteration
            await self.hook.after_iteration(ctx)

        return result

    async def process_message(self, msg: InboundMessage) -> str:
        """
        处理一条来自消息总线的消息。

        这是 Channel → Agent 的主入口。
        """
        logger.info("Processing message from {}:{}", msg.channel, msg.sender_id)

        result = await self.run_once(msg.content, session_key=msg.session_key)

        # 发送响应到出站总线
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=result.content,
        ))

        return result.content

    async def run_loop(self) -> None:
        """
        永久循环：从总线取消息 → 处理 → 发布响应。

        这是 gateway 模式下的主循环。
        """
        logger.info("Agent loop started, waiting for messages...")
        while True:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
                await self.process_message(msg)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Agent loop stopped")
                break
            except Exception:
                logger.exception("Error processing message")
