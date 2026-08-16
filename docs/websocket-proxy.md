# WebSocket 反向代理技术总结

> Hermes Agent 内置代理的 WebSocket 透传修复技术总结。
> 背景：`http://<NAS>:9120/chat` 页面持续报 `Chat connection interrupted (code 1006). Reconnecting...`，
> 根因是反向代理不支持 / 处理不当 WebSocket 升级，修复后改为原生 socket 实现。

---

## 1. 问题现象

通过反向代理（`:9120`）访问 Agent 控制台（`/chat`）时：
- 页面登录 OK、HTTP API 正常
- 但**聊天区持续** `Chat connection interrupted (code 1006). Reconnecting...`
- 前端无限重连（WebSocket `1006` = abnormal closure，连接被异常掐断）

后端本身完全健康（直连 HTTP/WS 都正常，进程无重启）。

---

## 2. 根因：反代不支持 WebSocket 升级转发

### 2.1 旧的实现（`http.server` + `http.client`）

旧版用 `BaseHTTPRequestHandler` + `http.client.HTTPConnection` 写反代：

```python
class Handler(BaseHTTPRequestHandler):
    def _proxy(self):
        conn = http.client.HTTPConnection(*backend)
        conn.request(self.command, self.path, ...)
        resp = conn.getresponse()
        # WebSocket 升级: 透传原始字节
        if resp.status == 101 and resp.getheader("Upgrade") == "websocket":
            sock = resp.fp.raw._sock
            _relay(self.connection, sock)   # 双向 recv/sendall
```

### 2.2 为什么 1006

即使代码里有 101 → `_relay` 透传逻辑，仍有**两个缓冲陷阱**导致 WS 数据丢失：

1. **`BaseHTTPRequestHandler.rfile` 缓冲**
   - `BaseHTTPRequestHandler` 用 `self.rfile`（带缓冲）读请求
   - WS 握手后，客户端可能已发来 WS 数据帧，但这些字节可能**滞留在 `self.rfile` 缓冲区**，未被读取
   - `_relay` 直接读 `self.connection`（原始 socket）→ **漏掉 rfile 缓冲里的数据**

2. **`http.client` 的 101 响应缓冲**
   - `http.client` 收到 101 后，可能已把后端发来的 WS 首帧读进 `resp.fp` 缓冲
   - `_relay` 透传 `resp.fp.raw._sock` → **漏掉 `resp.fp` 缓冲里的数据**

两处丢数据 → WS 帧不完整 → 连接被误判中断 → **1006**。

---

## 3. 修复：原生 socket 实现

### 3.1 思路

**完全绕开** `http.server` / `http.client` 的缓冲，用原生 socket 手动处理：

1. 监听 TCP 端口，`accept()` 拿到原始客户端 socket
2. 从客户端 socket **逐字节读** HTTP 请求头（`\r\n\r\n` 为止），**不引入额外缓冲**
3. 连接后端 socket，把请求头原样转发
4. 从后端读响应头
5. **如果 `101 Switching Protocols`（WebSocket 升级）**：
   - 把 101 响应头发回客户端
   - **`_relay(客户端socket, 后端socket)`** 双向原始字节透传（无缓冲，一字节不丢）
6. 否则按普通 HTTP 转发 body

### 3.2 关键实现

```python
def _handle(conn):
    # 1. 读客户端请求头 (到 \r\n\r\n)
    req = _recv_until(conn, b"\r\n\r\n")
    # 2. 连接后端
    backend_sock = socket.create_connection(backend)
    backend_sock.sendall(req)
    # 3. 读后端响应头
    resp = _recv_until(backend_sock, b"\r\n\r\n")
    # 4. 判断是否 WS 升级
    if b"101" in resp.split(b"\r\n",1)[0] and b"upgrade: websocket" in resp.lower():
        conn.sendall(resp)
        _relay(conn, backend_sock)   # 双向原始字节透传
    else:
        # 普通 HTTP: 转发 body
        ...
```

**核心**：`_recv_until` 逐块读但**不缓冲进对象**，直接透传原始字节。这样 WS 升级后两端 socket 完全交给 `_relay`，无中间缓冲，**不丢帧**。

### 3.3 效果
- WebSocket 升级（101）后干净双向透传
- 聊天页 / 实时终端稳定，不再 1006
- HTTP 请求同样正常（原生 socket 手写 HTTP 转发）

---

## 4. 何时需要原生 socket 反代

| 场景 | 方案 |
|------|------|
| 需要 WS 升级透传的 Python 反代 | **原生 socket 实现**（本方案） |
| 有 nginx 可用 | nginx `proxy_pass` + `Upgrade`/`Connection` 头（最省事） |
| 纯 TCP 透传 | `socat TCP-LISTEN:9120,fork TCP:target:9119` |
| 普通 HTTP-only 反代 | `http.server` 足够 |

> 若必须用 Python 且要支持 WS，优先**原生 socket 或 aiohttp/starlette**，
> **不要**在 `BaseHTTPRequestHandler` 上打补丁（缓冲陷阱难绕）。

---

## 5. 相关文件

| 文件 | 说明 |
|------|------|
| `cmd/proxy.py` | 原生 socket 反代（HTTP + WebSocket 透传） |
| `cmd/main` | 启动 / 停止 proxy，读 dashboard.conf 目标 |

## 6. 验证

- 聊天页 `/chat` 无 `1006` / `Reconnecting`
- 后端日志无异常（不再有 WS 票据风暴）
- WS 冒烟测试：修复前 WS `OPEN` 后即断，修复后能保持
