# Channels 模块整体流程

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         ChannelManager                          │
│  职责：管理所有渠道的生命周期，调度消息                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  __init__(config)                                               │
│      │                                                          │
│      ├─► discover_enabled()        ← 自动发现所有渠道             │
│      │       │                                                  │
│      │       ├─► discover_channel_names()  ← pkgutil 扫描目录    │
│      │       │       └─► pkgutil.iter_modules(channels/)        │
│      │       │           返回: ["cli_channel", "demo_channel"]  │
│      │       │                                                  │
│      │       ├─► load_channel_class()  ← 动态导入单个渠道         │
│      │       │       └─► importlib.import_module()              │
│      │       │           └─► inspect + issubclass 过滤          │
│      │       │               返回: CliChannel 类                │
│      │       │                                                  │
│      │       ├─► discover_plugins()  ← entry_points 外部插件     │
│      │       │       └─► importlib.metadata.entry_points()      │
│      │       │                                                  │
│      │       └─► 按 config_channels 白名单过滤                   │
│      │           返回: {name: class} 字典                       │
│      │                                                          │
│      ├─► 实例化每个渠道: cls(bus, config)                        │
│      └─► 存入 self.channels 字典                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  start()                                                        │
│      └─► 并发启动所有渠道的 start() 协程                          │
│                                                                 │
│  stop()                                                         │
│      └─► 并发停止所有渠道的 stop() 协程                           │
│                                                                 │
│  run()                                                          │
│      └─► _dispatch_outbound() 循环                               │
│              │                                                  │
│              ├─► bus.consume_outbound()   ← 从总线取出站消息      │
│              │   队列为空时挂起等待                               │
│              │                                                  │
│              ├─► 按 msg.channel 找到目标渠道                     │
│              │                                                  │
│              └─► _send_with_retry(msg)                          │
│                      └─► channel.send(msg)  ← 发送到外部平台     │
│                          失败重试 3 次                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 消息流转

```
用户发送消息
  │
  ▼
┌─────────────┐  publish_inbound()   ┌───────────┐
│  渠道层      │ ────────────────────▶│  inbound  │
│  (CLI/TG/..)│                      │   队列    │
└─────────────┘                      └─────┬─────┘
                                           │
                                  consume_inbound()
                                           │
                                           ▼
                                     ┌───────────┐
                                     │  Agent    │
                                     │  处理消息  │
                                     └─────┬─────┘
                                           │
                                 publish_outbound()
                                           │
                                           ▼
┌─────────────┐  consume_outbound()  ┌───────────┐
│  渠道层      │ ◀───────────────────│  outbound │
│  (CLI/TG/..)│                      │   队列    │
└─────────────┘                      └───────────┘
  │
  ▼
用户收到回复
```

## 自动发现机制

```
channels/
├── base.py           ← ABC 基类（不被发现）
├── registry.py       ← 发现引擎（不被发现）
├── manager.py        ← 管理器（不被发现）
├── channels.md       ← 本文件（不被发现）
├── cli_channel.py    ← ✅ 命名匹配 *_channel → 被发现
└── demo_channel.py   ← ✅ 命名匹配 *_channel → 被发现
```

**命名约定**：文件名以 `_channel` 结尾的模块会被自动扫描和加载。

## 核心设计思想

| 概念 | 实现方式 | 作用 |
|------|----------|------|
| 约定优于配置 | 文件名 `*_channel` | 放文件就能被发现，无需注册 |
| 动态导入 | `importlib.import_module()` | 运行时按名字加载模块 |
| 类型检查 | `issubclass(cls, BaseChannel)` | 只接受实现了接口的类 |
| 开放扩展 | `entry_points` | 第三方包可插拔接入 |
| 白名单过滤 | `config_channels` | 配置控制启用哪些渠道 |
| 错误隔离 | `try/except` 包裹每个加载 | 单个渠道失败不影响其他 |

## 文件职责

| 文件 | 行数 | 职责 |
|------|------|------|
| `base.py` | ~40 | 定义 BaseChannel ABC（接口契约） |
| `registry.py` | ~80 | 自动发现 + 动态加载渠道类 |
| `manager.py` | ~80 | 组装渠道、调度出站消息、重试发送 |
| `cli_channel.py` | ~25 | 示例：终端交互渠道 |
| `demo_channel.py` | ~25 | 示例：自动发送演示消息的渠道 |
