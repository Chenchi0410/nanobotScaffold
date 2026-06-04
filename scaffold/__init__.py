"""
脚手架演示项目 — 从 nanobot 提取的 6 个通用架构模式

模式清单：
  1. 插件自动发现 (pkgutil + ABC)     → channels/, providers/, agent/tools/
  2. 消息总线解耦 (asyncio.Queue)     → bus/
  3. 生命周期 Hook (CompositeHook)   → agent/hook.py
  4. 策略 + 重试链 (Provider)         → providers/
  5. 配置驱动工厂 (Factory)           → config/, providers/factory.py
  6. Facade 门面 (SDK 入口)           → facade.py
"""

__version__ = "0.1.0"
