# Changelog — Hermes Agent (fnOS)
# Changelog

## [1.2.6] - 2026-10-09
- **修复**: 应用中心"重启应用"后服务消失（101:9120 拒绝连接）— `cmd/main` 末尾恒 `exit 0` 掩盖了 `status` 的真实退出码，fnOS 以脚本退出码判定应用运行状态，误判"未运行"后回收刚拉起的 proxy；改为透传 case 分支退出码（running→0 / 其他→1）
- **排查记录**: 同根因在伴生应用 dsh-dashboard 同样复现（stop→start 全周期 A/B 验证：带 exit 0 必死、去掉后进程存活），dsh-dashboard 侧另行修复

## [1.2.5] - 2026-10-09
- **修复**: NAS 重启后开机自启被陈旧 pid 文件短路 — 旧版仅 `kill -0` 判活，重启后 pid 被无关进程复用即误判"proxy 已在运行"而跳过启动，:9120 无人监听、桌面窗口打不开。现校验 `/proc/<pid>/cmdline` 确属本应用 proxy.py 才认定在跑；陈旧/复用 pid 自动清理
- **新增**: `start` 后端口健康轮询（最长 20s），进程活着但端口不通（僵尸态）自动杀掉重启，最多 3 轮；`stop` 只杀 cmdline 确认属于本应用的进程，防 pid 复用误杀
- **修复**: proxy.py 绑定 :9120 带退避重试（应对异常重启残留进程短暂占端口，即 README 踩坑记录的 "Address already in use"），最终失败非 0 退出交给 cmd/main 重试，不再"进程存活但端口没绑"
- **变更**: python3 探测扩展（兼容 python3/python312 包名与 PATH 查找）；`kill_proxy` 同时清理 pid 丢失的残留 proxy 进程

## [1.2.4] - 2026-08-20
- **修复**: proxy.py 配置目录多级兜底（不依赖单一 HERMES_CONF_DIR env，自动从 fnOS 数据目录推导）
- **修复**: cmd/main 启动时兜底创建 dashboard.conf


Agent Web 控制台的**快捷入口空壳应用**。所有版本变更记录。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本遵循 [SemVer](https://semver.org/lang/zh-CN/)。

---

## [1.2.3] — 2026-08-19

### 修复
- **连接/文件描述符泄漏**：内置代理 WebSocket 双向透传时，连接关闭后未正确释放双方 socket → 长期运行 fd 耗尽导致新连接被拒（访问失效）。已修复 `_relay` 异常/结束时关闭双方 socket、异常路径兜底关闭 backend_sock。

## [1.2.2] — 2026-08-16

### 修复
- **内置代理 POST 400**：重写 Host 头时去掉重复空行（`\r\n\r\n`），修复 POST 登录 / WS-ticket 请求返回 `400 Invalid HTTP request`，从而**聊天页 WebSocket 不再 1006**
- **升级覆盖配置**：`install_callback` 升级时**保留已有 `dashboard.conf`**，不再用默认 `127.0.0.1:9119` 覆盖用户设好的目标

## [1.2.1] — 2026-08-16

### 修复
- **升级保留配置**：`install_callback` 在升级场景（`wizard_target_ip` 为空）时保留已有 `dashboard.conf`，不覆盖为用户之前设好的目标

## [1.2.0] — 2026-08-16

### 增强
- **内置代理改用原生 socket 实现**，**修复 WebSocket 透传 1006 断连**
  - 旧版 `http.server`/`http.client` 反代有缓冲陷阱，导致聊天页/实时终端 WS 连接建立后立即被掐断（`1006 Reconnecting`）
  - 原生 socket 实现：WS 升级（101）后干净双向原始字节透传，**不丢帧、不 1006**

## [1.1.0] — 2026-08-15

### 增强
- **可配置目标**：安装向导 / 设置页填写「目标 IP/域名 + 端口」
  - 默认 `127.0.0.1:9119`（本机 Hermes Core）
  - 可改为任意机器，如 `192.168.31.31:9119`
- **内置代理转发**：桌面图标通过本机 `:9120` 由内置代理转发到配置的目标

### 修复
- **数据目录推导健壮化**：空壳应用 fnOS 无 `TRIM_PKGVAR` 时，从 `home` 软链（`/volX/@apphome/<app>`）推导卷
- **声明 python312 依赖**：`platform = all`（纯前端无架构依赖）

## [1.0.0] — 2026-08-15

### 增强
- **空壳应用**：Hermes Core Dashboard 快捷入口
- **显示名**：Hermes Agent（应用 ID HermesAgent）
- **开发者信息**：发布者/维护者更新

---

## 版本对照

| 版本 | 关键变化 |
|------|---------|
| 1.0.0 | 空壳快捷入口 |
| 1.1.0 | 可配置目标 IP+端口，内置代理转发 |
| 1.2.0 | 原生 socket WS 透传修复（1006） |
| 1.2.1 | 升级保留配置 |
| 1.2.2 | 代理 POST 400 修复 + 升级保留配置 |

<!-- 以下为 git 提交对照，供追溯 -->
<!-- 1.2.2: b38eb41 (proxy POST 400), f6a4d9f (升版) -->
<!-- 1.2.1: c0440ff (升级保留配置), b305dfc (升版) -->
<!-- 1.2.0: 1467a2b (原生socket WS), 090da6c (升版+文档) -->
<!-- 1.1.0: 14f7435 (可配置目标), ad2e4e6 (DATA_DIR), f94ec5c (python312/all), fe4a9d8 (home软链) -->
