# Hermes Agent (fnOS)

[![Release](https://img.shields.io/github/v/release/techysy/hermes-dashboard-fnos)](https://github.com/techysy/hermes-dashboard-fnos/releases)
[![Platform](https://img.shields.io/badge/platform-all-blue)](https://github.com/techysy/hermes-dashboard-fnos)
[![License](https://img.shields.io/github/license/techysy/hermes-dashboard-fnos)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/techysy/hermes-dashboard-fnos)](https://github.com/techysy/hermes-dashboard-fnos/commits/main)

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
> 🛠️ **白屏健壮化修复（v1.2.4）**：见 [`docs/whitescreen-hardening-v1.2.4.md`](docs/whitescreen-hardening-v1.2.4.md)
> ⚠️ **自启失败排障（v1.2.4）**：见下方「踩坑记录」
> 📋 **更新日志**：见 [CHANGELOG.md](CHANGELOG.md)
> 🧪 **测试报告**：见 [docs/test-report.md](docs/test-report.md)

## ⚠️ 踩坑记录

### 自启失败：Address already in use（端口占用）— v1.2.5 已根治

> **v1.2.5 起自动修复**：`cmd/main` 启动改为校验进程 cmdline 身份 + 端口健康轮询 + 失败自动清理重试（含被残留进程占用端口时的 `pkill` 清理），`proxy.py` 绑定带退避重试且失败即退出交给外层重试。升级 fpk 后重启 NAS 即可，无需手动干预。以下为旧版（≤v1.2.4）手动排障记录：

**症状**：NAS 重启后应用状态 running，但 `:9120` 无法访问；`proxy.log` 报 `OSError: [Errno 98] Address already in use`

**根因**：异常关机 / 重启时旧 proxy 进程残留（pid 文件丢失但进程还活着），appcenter 自启拉起新 proxy 时 bind 失败退出，而 appcenter 仍认为启动成功。另一变体：重启后 pid 文件残留且 pid 号被无关进程复用，旧版 `kill -0` 误判"已在运行"直接跳过启动，同样导致 `:9120` 无人监听。

**排查**：

```bash
# 看端口被谁占
sudo ss -tlnp | grep 9120
# 看 proxy.log 是否有 bind 失败
grep -n "already in use" /vol4/@appdata/HermesAgent/proxy.log
```

**临时修复**：杀掉残留进程后重启应用

```bash
sudo pkill -f "HermesAgent/cmd/proxy.py"
# 应用中心 → Hermes Agent → 重启
```

### 其他历史坑

| 版本 | 坑 | 详见 |
|------|-----|------|
| v1.2.5 | 重启后陈旧 pid 被复用 → 开机自启短路（已根治） | [CHANGELOG](CHANGELOG.md) |
| v1.2.3 | WebSocket 长连接 fd 泄漏 → 长期运行拒绝新连接 | [CHANGELOG](CHANGELOG.md) |
| v1.2.2 | POST 400（Host 头重复空行）→ 聊天页 WS 1006 | [CHANGELOG](CHANGELOG.md) |
| v1.2.2 | 升级覆盖 dashboard.conf 用户配置 | [CHANGELOG](CHANGELOG.md) |
| v1.2.0 | http.server 反代缓冲陷阱 → WS 1006 断连 | [websocket-proxy.md](docs/websocket-proxy.md) |

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
