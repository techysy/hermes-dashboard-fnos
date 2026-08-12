# Hermes Dashboard (fnOS)

Hermes Core Dashboard 的**快捷入口空壳应用**。

打开即进入 Hermes Core 的 Web 控制台（`http://<NAS>:9119`），无需记端口。

## 前置要求

- 已安装并运行 [HermesCore](https://github.com/techysy/hermes-core-fnos)（dashboard 监听 :9119）

## 说明

这是一个**纯空壳应用**：

- 没有后端进程、不占用端口
- 桌面图标通过 iframe 指向 Hermes Core 的 dashboard 端口 9119
- 生命周期脚本全部为 no-op

## 安装

App Center → 手动安装 → 选择 `HermesDashboard.fpk`。

## License

MIT
