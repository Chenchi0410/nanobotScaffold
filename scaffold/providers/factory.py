"""
模式 5：Provider 工厂 — 根据配置动态创建实例

设计要点：
  - make_provider() 是唯一的创建入口
  - 先从 registry 查找 ProviderSpec（元数据）
  - 再根据 spec.backend 路由到具体的 Provider 类
  - 新增 Provider 只需：1) registry 加一行 2) 这里加一个 elif
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from scaffold.providers.base import LLMProvider
from scaffold.providers.registry import find_by_name


def make_provider(config: dict[str, Any]) -> LLMProvider:
    """
    根据配置创建 LLM Provider 实例。

    API Key 优先级：config["api_key"] > 环境变量（spec.env_key）

    config 示例：
        {
            "provider": "mimo",
            "model": "mimo-v2.5-pro",
            "api_key": "tp-xxx"
        }
    """
    provider_name = config.get("provider", "demo")
    spec = find_by_name(provider_name)

    if spec is None:
        logger.warning("Unknown provider '{}', falling back to demo", provider_name)
        from scaffold.providers.demo_provider import DemoProvider
        return DemoProvider()

    backend = spec.backend
    # API Key 优先级：config > 环境变量
    api_key = config.get("api_key") or os.environ.get(spec.env_key, "")

    if backend == "openai":
        from scaffold.providers.openai_provider import OpenAIProvider
        model = config.get("model") or ""
        kwargs = {"api_key": api_key, "api_base": spec.default_api_base}
        if model:
            kwargs["default_model"] = model
        return OpenAIProvider(**kwargs)

    elif backend == "anthropic":
        from scaffold.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key)

    elif backend == "demo":
        from scaffold.providers.demo_provider import DemoProvider
        return DemoProvider()

    else:
        raise ValueError(f"Unknown backend: {backend}")
