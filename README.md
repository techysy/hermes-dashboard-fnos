# Hermes Agent (fnOS)

Hermes Core Dashboard 的**快捷入口空壳应用**，提供**反向代理**，局域网免登录访问 Hermes Core 的 Web 控制台。

打开即进入 Hermes Core 的 dashboard（经反向代理 `0.0.0.0:9118 → 本机 127.0.0.1:9119`），无需登录、无需记端口。

## 前置要求

- 已安装并运行 [HermesCore](https://github.com/techysy/hermes-core-fnos)（v0.9.9.9+，dashboard 监听 127.0.0.1:9119 免认证）

## 说明

空壳应用提供**反向代理**：

- **dashboard 绑定 127.0.0.1（loopback）免认证**（v0.20.0 废弃 `--insecure`，绑定 0.0.0.0 强制认证；loopback 免认证）
- **本空壳反向代理 `0.0.0.0:9118 → 127.0.0.1:9119`**，让局域网设备经 9118 免登录访问 dashboard
- 桌面图标 iframe 指向 `:9118`（反向代理端口）
- 代理脚本：`cmd/proxy.py`（Python 标准库，支持 HTTP + WebSocket）
- 生命周期：`cmd/main` 启动/停止代理

## 端口

| 端口 | 说明 |
|------|------|
| 9118 | 空壳反向代理（局域网可访问，免登录入口） |
| → 127.0.0.1:9119 | HermesCore dashboard（loopback 免认证） |

## 安装

App Center → 手动安装 → 选择 `HermesDashboard.fpk`。

## License

MIT
