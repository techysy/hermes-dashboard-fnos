# Hermes Agent 白屏健壮化修复记录

> 2026-08-20 v1.2.4
> 仓库：`techysy/hermes-dashboard-fnos`

---

## 问题现象

fnOS 应用中心打开 Hermes Agent 白屏。根因排查见 `docs/fnos应用白屏故障排查与修复记录.md`（朋友机器实测）。

核心问题：**proxy.py 通过 `HERMES_CONF_DIR` env 定位 `dashboard.conf`，env 一旦没设对就读错/读不到配置，静默 fallback 到 `127.0.0.1:9119`**。

- 正常路径（appcenter 经 cmd/main 启动）：`cmd/main` 设 `HERMES_CONF_DIR=${DATA_DIR}` → 正确。
- 异常路径（手动/dsh/其他方式裸启动 proxy）：`HERMES_CONF_DIR` 未设 → 用默认 `/tmp/hermes/dashboard.conf`（通常不存在）→ 静默 fallback 127.0.0.1 → 白屏。

## 修复内容（v1.2.4）

### 1. proxy.py — 配置目录多级兜底 `_resolve_conf_dir()`

不再只依赖单一 env，按优先级自动推导配置目录：

```
1. HERMES_CONF_DIR env（显式指定）
2. TRIM_PKGVAR env（fnOS 注入的数据目录）→ <data>/dashboard.conf
3. 常见 fnOS 数据目录（/vol*/@appdata/<App>，从 TRIM_APPNAME 推导）
4. 当前工作目录
5. 默认 /tmp/hermes（最后兜底）
```

即使裸启动（无 `HERMES_CONF_DIR`），只要进程环境带 `TRIM_APPNAME`（fnOS 通常注入），就能自动找到 `/volX/@appdata/HermesAgent/dashboard.conf`。已在 101 实测：`resolved conf dir: /vol4/@appdata/HermesAgent`。

### 2. proxy.py — 读配置失败不再静默

读不到 `dashboard.conf` 时打印：
```
[proxy] WARN: cannot read config <路径>; using default 127.0.0.1:9119
```

### 3. proxy.py — 启动日志打印实际配置文件路径

```
hermes agent proxy: 0.0.0.0:9120 -> <ip>:<port> (conf=<路径>) (native socket)
```

一眼看出 proxy 读了哪个配置文件、目标是什么，避免"配置改了但进程没读"的困惑。

### 4. cmd/main — 启动时兜底创建 dashboard.conf

`start()` 里先 `mkdir -p ${DATA_DIR}`，若 `dashboard.conf` 不存在则写默认 `127.0.0.1:9119`，避免空配置。

## 关键机制说明

**proxy.py 不绑定目标 IP**：它绑定的是监听端口 `LISTEN_PORT`（9120），目标地址是**每次请求时**从 `dashboard.conf` 实时读取的（`_load_target()` 在 `_handle()` 和 `main()` 中调用）。所以：

- 改配置理论上**不需要重启 proxy**——下一请求就会读到新值。
- "旧进程绑定初始化 127.0.0.1"的猜测不准确——进程不是绑定目标，而是**读错了配置目录**（`CONF_DIR=/tmp/hermes`）导致永远用默认 127.0.0.1。

## 验证

- 多级兜底：无 `HERMES_CONF_DIR` 裸启动，正确解析到 `/vol4/@appdata/HermesAgent`。
- `bash -n cmd/main` + `python3 -m py_compile cmd/proxy.py` 通过。

## 发布

- Release v1.2.4：`HermesAgent-1.2.4-all.fpk` + `HermesAgent-1.2.4-iframe-all.fpk`
- 交付目录 `/vol1/1000/fnOS App/fpk/HermesAgent/` 已归档旧版

## 通用教训

任何靠 env 定位配置的 fnOS 应用脚本，都应：
1. **多级兜底推导配置路径**（env → fnOS 标准数据目录 → 工作目录），不依赖单一 env。
2. **读配置失败/找不到时必须打日志**，不能静默 fallback（否则排障时以为配置改了但进程读了别处）。
3. **启动日志打印实际用的配置路径**，便于核验。
