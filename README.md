# Hermes Agent (fnOS)

Hermes Core Web 控制台的**快捷入口空壳应用**。

打开即进入 Hermes Core 的 Web 控制台（`http://<NAS>:9119`），手动登录后使用。

## 前置要求

- 已安装并运行 [HermesCore](https://github.com/techysy/hermes-core-fnos-v2)（dashboard 监听 :9119）

## 说明

这是一个**纯空壳应用**：

- 没有后端进程、不占用端口
- 桌面图标通过 iframe 指向 Hermes Core 的 dashboard 端口 9119
- 打开后**手动输入账号密码登录**（admin / 安装时设置的密码）
- 生命周期脚本全部为 no-op

## 安装

App Center → 手动安装 → 选择 `HermesAgent.fpk`。

## License

MIT
