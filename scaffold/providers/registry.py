"""
模式 5：Provider 注册表 — 静态元数据表

设计要点：
  - ProviderSpec 是一个 frozen dataclass，描述一个 Provider 的所有元数据
  - PROVIDERS 元组是唯一的注册入口，加新 Provider 只需在这里加一行
  - find_by_name() 做查找，其他模块通过这个函数获取 Provider 信息
  - 这个模式可以推广到任何需要"元数据驱动"的场景
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    """一个 LLM Provider 的元数据。"""

    name: str                        # 配置中的字段名，如 "openai"
    backend: str                     # 使用哪个后端实现："openai" | "anthropic" | "demo"
    env_key: str = ""                # API Key 的环境变量名
    display_name: str = ""           # 显示名称
    default_api_base: str = ""       # 默认 API 地址
    is_local: bool = False           # 是否本地部署


# ---- 注册表：加新 Provider 只改这里 ----

PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openai",
        backend="openai",
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        default_api_base="https://api.openai.com/v1",
    ),
    ProviderSpec(
        name="anthropic",
        backend="anthropic",
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
    ),
    ProviderSpec(
        name="deepseek",
        backend="openai",
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        default_api_base="https://api.deepseek.com",
    ),
    ProviderSpec(
        name="mimo",
        backend="openai",
        env_key="MIMO_API_KEY",
        display_name="MiMo",
        default_api_base="https://token-plan-cn.xiaomimimo.com/v1",
    ),
    ProviderSpec(
        name="demo",
        backend="demo",
        display_name="Demo (本地模拟)",
    ),
)


def find_by_name(name: str) -> ProviderSpec | None:
    """按名称查找 Provider 规格。"""
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None
