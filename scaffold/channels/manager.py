"""
渠道管理器 — 协调所有渠道的启停和消息路由。

设计要点：
  - _init_channels() 用自动发现机制初始化渠道，只导入启用的
  - _dispatch_outbound() 是一个永久循环，从总线取出站消息路由到对应渠道
  - _send_with_retry() 指数退避重试，发送失败不丢消息
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from loguru import logger

from scaffold.bus.events import OutboundMessage
from scaffold.bus.queue import EventBus
from scaffold.channels.base import BaseChannel
from scaffold.channels.registry import discover_enabled, discover_channel_names

_SEND_RETRY_DELAYS = (1, 2, 4)


class ChannelManager:
    """
    管理所有渠道的生命周期和消息路由。

    用法：
        manager = ChannelManager(config, bus)
        await manager.start_all()   # 启动所有渠道 + 出站分发器
    """

    def __init__(self, config: dict[str, Any], bus: EventBus) -> None:
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None

        self._init_channels()

    def _init_channels(self) -> None:
        """自动发现并初始化启用的渠道。"""
        channel_config = self.config.get("channels", {})
        enabled_names = {
            name for name, cfg in channel_config.items()
            if isinstance(cfg, dict) and cfg.get("enabled", False)
        }

        if not enabled_names:
            logger.info("No channels enabled in config")
            return

        names = discover_channel_names()
        for name, cls in discover_enabled(enabled_names, _names=names).items():
            section = channel_config.get(name, {})
            try:
                channel = cls(section, self.bus)
                self.channels[name] = channel
                logger.info("{} channel enabled", cls.display_name)
            except Exception as e:
                logger.warning("{} channel init failed: {}", name, e)

    async def start_all(self) -> None:
        """启动所有渠道和出站消息分发器。"""
        if not self.channels:
            logger.warning("No channels enabled")
            return

        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())

        tasks = [
            asyncio.create_task(self._start_channel(name, ch))
            for name, ch in self.channels.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        try:
            await channel.start()
        except Exception:
            logger.exception("Failed to start channel {}", name)

    async def stop_all(self) -> None:
        """停止所有渠道和分发器。"""
        if self._dispatch_task:
            self._dispatch_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._dispatch_task

        for name, channel in self.channels.items():
            try:
                await channel.stop()
            except Exception:
                logger.exception("Error stopping {}", name)

    async def _dispatch_outbound(self) -> None:
        """永久循环：从总线取出站消息，路由到对应渠道。"""
        logger.info("Outbound dispatcher started")
        while True:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(), timeout=1.0
                )
                channel = self.channels.get(msg.channel)
                if channel:
                    await self._send_with_retry(channel, msg)
                else:
                    logger.warning("Unknown channel: {}", msg.channel)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _send_with_retry(self, channel: BaseChannel, msg: OutboundMessage) -> None:
        """指数退避重试发送。"""
        for attempt, delay in enumerate(_SEND_RETRY_DELAYS):
            try:
                await channel.send(msg)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == len(_SEND_RETRY_DELAYS) - 1:
                    logger.exception("Failed to send to {} after {} attempts", msg.channel, attempt + 1)
                    return
                logger.warning("Send failed (attempt {}): {}, retrying in {}s", attempt + 1, e, delay)
                await asyncio.sleep(delay)

    def get_channel(self, name: str) -> BaseChannel | None:
        return self.channels.get(name)
