#!/usr/bin/env python3
"""Hermes Agent 目标仪表盘代理 (原生 socket 版).

监听本机固定 TCP 端口 (默认 9120), 把 HTTP/WebSocket 请求反向代理到
配置的目标 agent 仪表盘 (默认 127.0.0.1:9119, 可经设置改为任意 IP:端口).

用原生 socket 实现, 避免 http.server / http.client 的缓冲问题,
保证 WebSocket 升级后 (101) 能干净地双向透传原始字节 (不丢帧, 不 1006).
"""
import os
import socket
import threading


LISTEN_PORT = int(os.environ.get("HERMES_LISTEN_PORT", "9120"))
CONF_DIR = os.environ.get("HERMES_CONF_DIR", "/tmp/hermes")


def _load_target():
    """从 dashboard.conf 读目标 IP:PORT, 默认 127.0.0.1:9119."""
    ip, port = "127.0.0.1", 9119
    conf = os.path.join(CONF_DIR, "dashboard.conf")
    try:
        with open(conf, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TARGET_IP="):
                    v = line.split("=", 1)[1].strip()
                    if v:
                        ip = v
                elif line.startswith("TARGET_PORT="):
                    v = line.split("=", 1)[1].strip()
                    if v.isdigit():
                        port = int(v)
    except OSError:
        pass
    return (ip, port)


def _recv_until(sock, marker):
    """从 socket 读取直到遇到 marker (如 b'\\r\\n\\r\\n'), 返回读取的所有字节."""
    data = b""
    while marker not in data:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    return data


def _recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _relay(sock_a, sock_b):
    """双向透传原始字节流 (WebSocket 已升级后)."""
    def pump(src, dst):
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except Exception:
                pass
    t1 = threading.Thread(target=pump, args=(sock_a, sock_b), daemon=True)
    t2 = threading.Thread(target=pump, args=(sock_b, sock_a), daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()


def _handle(conn):
    """处理单个客户端连接 (HTTP 或 WebSocket)."""
    backend = _load_target()
    try:
        conn.settimeout(30)
        # 1. 读取客户端请求头 (含请求行 + headers)
        req_head = _recv_until(conn, b"\r\n\r\n")
        if not req_head:
            return
        head_end = req_head.index(b"\r\n\r\n") + 4
        head = req_head[:head_end]
        body_buf = req_head[head_end:]  # 请求头后可能已带了部分 body

        # 2. 解析 Content-Length, 读满 body
        content_length = 0
        for line in head.split(b"\r\n"):
            low = line.lower()
            if low.startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":", 1)[1].strip())
                except ValueError:
                    content_length = 0
        body = body_buf
        if len(body) < content_length:
            body += _recv_exact(conn, content_length - len(body))
        body = body[:content_length]

        # 3. 连接后端
        backend_sock = socket.create_connection(backend, timeout=30)
        # 重写 Host 头为目标 (规避目标侧域名校验)
        lines = head.split(b"\r\n")
        out_lines = []
        host_written = False
        for line in lines:
            if line.lower().startswith(b"host:"):
                out_lines.append(f"Host: {backend[0]}:{backend[1]}".encode())
                host_written = True
            elif line.lower().startswith(b"connection:"):
                # 保留 (WS 升级需要)
                out_lines.append(line)
            else:
                out_lines.append(line)
        if not host_written:
            out_lines.append(f"Host: {backend[0]}:{backend[1]}".encode())
        # 重新拼请求
        request = b"\r\n".join(out_lines) + b"\r\n\r\n" + body
        backend_sock.sendall(request)

        # 4. 读取后端响应头
        resp_head = _recv_until(backend_sock, b"\r\n\r\n")
        if not resp_head:
            return
        r_end = resp_head.index(b"\r\n\r\n") + 4
        rhead = resp_head[:r_end]
        resp_body_buf = resp_head[r_end:]

        # 5. 判断是否 WebSocket 升级
        status_line = rhead.split(b"\r\n", 1)[0]
        is_ws = b"101" in status_line and b"websocket" in rhead.lower()

        # 6. 转发响应头给客户端
        conn.sendall(rhead)

        # 7. 后续处理
        if is_ws:
            # WebSocket: 双向透传, 把后端 socket 已缓冲的数据先转发
            if resp_body_buf:
                conn.sendall(resp_body_buf)
            _relay(conn, backend_sock)
        else:
            # 普通 HTTP: 根据 Content-Length 或 chunked 读 body 转发
            transfer_encoding = b""
            content_length = -1
            for line in rhead.split(b"\r\n"):
                low = line.lower()
                if low.startswith(b"transfer-encoding:"):
                    transfer_encoding = line.split(b":", 1)[1].strip().lower()
                elif low.startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":", 1)[1].strip())
                    except ValueError:
                        content_length = -1
            if b"chunked" in transfer_encoding:
                # 透传 chunked body (原样转发, 直到 0 chunk)
                if resp_body_buf:
                    backend_sock.sendall(b"")  # no-op
                    conn.sendall(resp_body_buf)  # 可能截断, 交给 _relay 处理剩余
                # 但 body_buf 只是部分, 需要继续读: 用 _relay 单向
                _relay_send(backend_sock, conn)
            elif content_length >= 0:
                # 固定长度 body
                out = resp_body_buf
                if len(out) < content_length:
                    out += _recv_exact(backend_sock, content_length - len(out))
                out = out[:content_length]
                conn.sendall(out)
                backend_sock.close()
                conn.close()
            else:
                # 无 body (或未知): 透传剩余
                if resp_body_buf:
                    conn.sendall(resp_body_buf)
                _relay_send(backend_sock, conn)
    except Exception as e:
        import sys
        print(f"[proxy err] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        try:
            conn.close()
        except Exception:
            pass


def _relay_send(src, dst):
    """单向透传 src -> dst 直到 EOF."""
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", LISTEN_PORT))
    server.listen(128)
    ip, port = _load_target()
    print(f"hermes agent proxy: 0.0.0.0:{LISTEN_PORT} -> {ip}:{port} (native socket)", flush=True)
    while True:
        conn, _ = server.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
