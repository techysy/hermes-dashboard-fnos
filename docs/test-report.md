# 测试报告 — Hermes Agent (fnOS)

> 记录 Hermes Agent 空壳应用的功能、跨机器代理、WebSocket 透传等测试情况。
> 版本：1.2.2（2026-08-16）

---

## 1. 测试环境

| 机器 | 角色 | IP | 说明 |
|------|------|----|------|
| 66 | fnOS NAS（反代） | 192.168.31.66 | Hermes Agent proxy :9120 → 目标 |
| 101 | fnOS NAS（反代） | 192.168.31.101 | Hermes Agent proxy :9120 → 目标 |
| 201 | 后端主机 | 192.168.31.201 | Hermes dashboard :9119 |
| 31 | 后端 VM | 192.168.31.31 | Hermes dashboard :9119 |

---

## 2. 功能测试

### 2.1 内置代理转发（HTTP）

| 场景 | 期望 | 结果 |
|------|------|------|
| 通过 9120 访问目标 `/api/status` | 200 | ✅ |
| 通过 9120 访问目标 `/login` | 200（登录页） | ✅ |
| 通过 9120 访问目标 `/chat` | 302 → 登录 | ✅ |
| 直连目标 9119（对照） | 200 | ✅ |

### 2.2 可配置目标（dashboard.conf）

| 场景 | 期望 | 结果 |
|------|------|------|
| 配置 TARGET_IP=192.168.31.201 | proxy 转发到 201:9119 | ✅ |
| 配置 TARGET_IP=192.168.31.31 | proxy 转发到 31:9119 | ✅ |
| 升级应用后配置保留 | 不覆盖为用户设的目标 | ✅ |

---

## 3. WebSocket 透传测试（关键）

> 旧版 `http.server`/`http.client` 反代有缓冲陷阱 → 聊天页 WS 1006。
> v1.2.0 起原生 socket 实现。

### 3.1 WS 握手

```
GET /api/pty?ticket=<ticket> HTTP/1.1
→ HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Sec-WebSocket-Accept: ...
```

| 场景 | 结果 |
|------|------|
| 通过 101 proxy 连 /api/pty | ✅ 101 握手成功 |
| 通过 66 proxy 连 /api/pty | ✅ 66 握手成功 |
| 连接后保持（非 1006） | ✅ |

### 3.2 完整链路测试（登录 → ticket → WS）

```
1. POST /auth/password-login → {"ok":true} 200
2. POST /api/auth/ws-ticket → {"ticket":"..."} 200
3. WS 连 /api/pty?ticket=... → 101 握手 → 收到 PTY 数据（连接保持）
```

**结果：PASS（连接保持，非 1006）**

---

## 4. 回归/故障记录

### 4.1 POST 400（已修复 v1.2.2）

**现象**：通过反代 POST 登录返回 `400 Invalid HTTP request received`，浏览器直连正常。

**根因**：proxy.py 重写 Host 头时，`head` 含结尾 `\r\n\r\n`，split 后 join 再拼 `\r\n\r\n` 产生**重复空行**，后端收到格式错误请求返回 400。

**验证**（echo server 抓包）：
- 修复前：请求头后 `\r\n\r\n\r\n\r\n`（重复空行）
- 修复后：请求头后单个 `\r\n\r\n` ✅

### 4.2 WS 1006（已修复 v1.2.0）

**现象**：聊天页持续 `Chat connection interrupted (code 1006). Reconnecting...`

**根因**：`http.server`/`http.client` 反代的缓冲陷阱（`rfile` 缓冲 + http.client 101 缓冲）导致 WS 数据丢失。

**修复**：原生 socket 实现，WS 升级后干净双向透传。

### 4.3 升级覆盖配置（已修复 v1.2.1/1.2.2）

**现象**：升级后 dashboard.conf 被覆盖成 `127.0.0.1:9119`，目标错乱 → 连接拒绝。

**根因**：`install_callback` 升级时 `wizard_target_ip` 为空，旧逻辑用默认值覆盖。

**修复**：`wizard_target_ip` 空且已有配置时保留。

---

## 5. 测试结论

| 项 | 状态 |
|----|------|
| HTTP 代理转发 | ✅ PASS |
| WebSocket 透传 | ✅ PASS（非 1006） |
| 登录 + WS-ticket 链路 | ✅ PASS |
| 升级保留配置 | ✅ PASS |
| 跨机器（66/101 → 201/31） | ✅ PASS |

**整体结论**：Hermes Agent 1.2.2 功能正常，跨机器代理 + WebSocket 聊天稳定可用。

---

## 6. 复测脚本（供回归）

```bash
# 1. HTTP
curl -s -m8 -o /dev/null -w "%{http_code}" http://<NAS>:9120/api/status
# 2. 登录（应返回 ok:true，而非 400）
curl -s -m8 -X POST -H "Content-Type: application/json" \
  -d '{"provider":"basic","username":"<user>","password":"<pw>"}' \
  http://<NAS>:9120/auth/password-login
# 3. WS-ticket
curl -s -m8 -b <cookie> -X POST http://<NAS>:9120/api/auth/ws-ticket
```
