# Hermes Agent (fnOS)

Agent Web 控制台的**快捷入口空壳应用**，可在安装向导 / 设置页指定**目标 IP 与端口**，打开任意 Agent 的仪表盘。

打开即进入配置的目标 Web 控制台（默认 Hermes Core `127.0.0.1:9119`），手动登录后使用。

## ✨ 功能

- **可配置目标**：安装向导 / fnOS 设置页填写「目标 IP / 域名 + 端口」
  - 默认 `127.0.0.1:9119`（本机 Hermes Core）
  - 可改为任意机器，如 `192.168.31.31:9119`（VM 上的 Agent）
- **内置代理转发**：桌面图标通过本机 `:9120` 由内置代理转发到配置的目标（支持 HTTP / WebSocket）
  - **原生 socket 实现**，WebSocket 升级后干净双向透传，不丢帧、不 1006 断连
  - 适合聊天页 / 实时终端等依赖 WebSocket 的 Agent 控制台
- 桌面 iframe 打开配置目标的 Web 控制台

> 🔧 **WebSocket 透传技术说明**：见 [`docs/websocket-proxy.md`](docs/websocket-proxy.md)

## 前置要求

- 目标 Agent 服务已运行（如 [HermesCore](https://github.com/techysy/hermes-core-fnos-v2) dashboard 监听 :9119）
- 目标机器与 NAS 网络互通

## 配置

| 项 | 默认 | 说明 |
|----|------|------|
| 目标 IP | `127.0.0.1` | Agent 仪表盘地址（本机或其它机器） |
| 目标端口 | `9119` | Agent 仪表盘端口 |
| 本机入口 | `9120` | 桌面图标打开的本机端口（内置代理监听） |

> 配置保存到数据区 `dashboard.conf`。修改后重启应用生效。

## 安装

App Center → 手动安装 → 选择 `HermesAgent.fpk`。

## License

MIT
