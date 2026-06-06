"""
CLI 入口 — 展示三种运行模式。

用法：
    python -m scaffold demo     # 自动演示模式（Demo Provider）
    python -m scaffold chat     # 交互式终端对话
    python -m scaffold sdk      # SDK 调用示例

配置文件：~/.scaffold/config.json
    {
      "provider": "mimo",
      "model": "mimo-v2.5-pro",
      "api_key": "tp-xxx"
    }
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from loguru import logger

from scaffold.facade import Nanobot

_CONFIG_PATH = Path.home() / ".scaffold" / "config.json"


def _load_provider_config() -> dict:
    """
    加载 Provider 配置。

    优先级：环境变量 > 配置文件 > 默认 demo
    """
    # 1. 尝试从配置文件读取
    file_config = {}
    if _CONFIG_PATH.exists():
        try:
            file_config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load config: {}", e)

    # 2. 环境变量覆盖
    api_key = os.environ.get("MIMO_API_KEY") or file_config.get("api_key", "")
    model = os.environ.get("SCAFFOLD_MODEL") or file_config.get("model", "mimo-v2.5-pro")
    provider = file_config.get("provider", "mimo")

    # 3. 有 api_key 就用真实模型，否则 demo
    if api_key:
        return {"provider": provider, "model": model, "api_key": api_key}
    return {"provider": "demo", "model": "demo-model"}


async def run_demo() -> None:
    """自动演示：展示所有脚手架模式如何协同工作。"""
    print("=" * 60)
    print("  脚手架演示 — 自动模式")
    print("=" * 60)

    # 模式 6：通过 Facade 创建（一行代码）
    bot = Nanobot.from_config()

    # 直接调用（不经过消息总线）
    questions = ["hello", "help", "tools"]
    for q in questions:
        print(f"\n📝 问题: {q}")
        result = await bot.run(q)
        print(f"🤖 回答: {result.content}")
        print(f"   工具: {result.tools_used}")
        print(f"   迭代: {result.iterations}")


async def run_chat() -> None:
    """交互式对话：通过消息总线。"""
    print("=" * 60)
    print("  脚手架演示 — 交互模式")
    print("  输入 'quit' 退出")
    print("=" * 60)

    from scaffold.agent.loop import AgentLoop
    from scaffold.bus.queue import EventBus
    from scaffold.agent.tools.loader import ToolLoader
    from scaffold.agent.tools.registry import ToolRegistry
    from scaffold.agent.hook import CompositeHook, LogHook
    from scaffold.providers.factory import make_provider

    config = _load_provider_config()
    print(f"  Provider: {config['provider']}, Model: {config['model']}")

    bus = EventBus()
    provider = make_provider(config)

    tools = ToolRegistry()
    ToolLoader().load(tools)

    hook = CompositeHook([LogHook()])
    loop = AgentLoop(provider=provider, bus=bus, tools=tools, hook=hook, config=config)

    # 启动 Agent 处理循环
    agent_task = asyncio.create_task(loop.run_loop())

    # 启动出站打印循环
    async def print_responses():
        while True:
            try:
                msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
                print(f"\n🤖 Agent: {msg.content}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    print_task = asyncio.create_task(print_responses())

    # CLI 输入循环
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("\nYou: ")
            )
            line = line.strip()
            if not line or line.lower() in ("quit", "exit", "q"):
                break
            await bus.publish_inbound(
                __import__("scaffold.bus.events", fromlist=["InboundMessage"]).InboundMessage(
                    channel="cli", sender_id="user", chat_id="chat", content=line
                )
            )
        except (EOFError, KeyboardInterrupt):
            break

    agent_task.cancel()
    print_task.cancel()
    print("\nGoodbye!")


async def run_sdk() -> None:
    """SDK 调用示例。"""
    print("=" * 60)
    print("  SDK 调用示例")
    print("=" * 60)

    config = _load_provider_config()
    print(f"  Provider: {config['provider']}, Model: {config['model']}")

    bot = Nanobot.from_config(config)

    # 简单调用
    result = await bot.run("hello")
    print(f"Response: {result.content}")

    # 带 Hook 的调用
    from scaffold.agent.hook import AgentHook, AgentHookContext

    class TimingHook(AgentHook):
        async def before_iteration(self, ctx: AgentHookContext):
            import time
            self.start = time.time()

        async def after_iteration(self, ctx: AgentHookContext):
            import time
            elapsed = time.time() - self.start
            print(f"  ⏱️ Iteration {ctx.iteration} took {elapsed:.2f}s")

    result = await bot.run("test message", hooks=[TimingHook()])
    print(f"Response: {result.content}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"

    if mode == "demo":
        asyncio.run(run_demo())
    elif mode == "chat":
        asyncio.run(run_chat())
    elif mode == "sdk":
        asyncio.run(run_sdk())
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python -m scaffold.cli [demo|chat|sdk]")


if __name__ == "__main__":
    main()
