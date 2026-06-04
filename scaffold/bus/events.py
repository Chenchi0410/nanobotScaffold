"""
模式 2：事件定义 — 消息总线的数据结构

设计要点：
  - 用 @dataclass 定义轻量级事件，不要用 dict
  - InboundMessage / OutboundMessage 分别表示入站和出站
  - metadata: dict 用于传递平台特定数据，保持核心字段简洁
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Event:
    """通用事件基类，用于演示。"""

    type: str
    data: Any = None
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InboundMessage:
    """从外部渠道收到的消息。"""

    channel: str          # 来源渠道：telegram, discord, cli ...
    sender_id: str        # 发送者 ID
    chat_id: str          # 会话 ID
    content: str          # 消息文本
    timestamp: datetime = field(default_factory=datetime.now)
    ## 核心字段放确定的信息，metadata 放可选的、不固定的附加信息。
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def session_key(self) -> str:
        """用于标识会话的唯一键。"""
        return f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """发往外部渠道的消息。"""

    channel: str
    chat_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
