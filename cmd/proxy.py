#!/usr/bin/env python3
"""
HermesDashboard 反向代理 — 转发到本机 Hermes Core dashboard (127.0.0.1:9119)。
dashboard 绑定 loopback (免认证), 本代理绑定 0.0.0.0 (局域网可访问), 实现局域网免登录访问。
支持 HTTP/HTTPS 普通请求 + WebSocket 升级 (dashboard Chat 需要)。
纯标准库, 无第三方依赖。

用法: python3 proxy.py [listen_port] [upstream_host] [upstream_port]
默认: 9118 -> 127.0.0.1:9119
"""
import socket
import sys
import threading

LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9118
UPSTREAM_HOST = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
UPSTREAM_PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 9119


def pipe(src, dst):
    """双向透传数据 (WebSocket 升级后 / 通用隧道)."""
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
            src.close()
        except Exception:
            pass
        try:
            dst.close()
        except Exception:
            pass


def handle(client):
    try:
        # 读取客户端请求头 (直到 \r\n\r\n)
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = client.recv(4096)
            if not chunk:
                return
            request += chunk
            if len(request) > 1_000_000:  # 1MB 上限
                return

        # 连接上游
        upstream = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=10)

        # 判断是否 WebSocket 升级
        is_ws = b"Upgrade: websocket" in request or b"upgrade: websocket" in request

        if is_ws:
            # WebSocket: 透传 (不重写 Host, 保持原始请求)
            upstream.sendall(request)
            threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
            pipe(upstream, client)
            return

        # 普通 HTTP: 重写 Host 头为 upstream (避免 dashboard 校验 Host 失败)
        # 解析请求行和 Host
        first_line_end = request.find(b"\r\n")
        first_line = request[:first_line_end]
        headers_end = request.find(b"\r\n\r\n")
        headers = request[first_line_end+2:headers_end]

        # 构造重写 Host 后的请求
        new_headers = []
        host_rewritten = False
        for line in headers.split(b"\r\n"):
            if line.lower().startswith(b"host:"):
                new_headers.append(f"Host: {UPSTREAM_HOST}:{UPSTREAM_PORT}".encode())
                host_rewritten = True
            else:
                new_headers.append(line)
        if not host_rewritten:
            new_headers.append(f"Host: {UPSTREAM_HOST}:{UPSTREAM_PORT}".encode())

        new_request = first_line + b"\r\n" + b"\r\n".join(new_headers) + b"\r\n\r\n"

        # 转发请求体 (如果有, 如 POST)
        body = request[headers_end+4:]
        upstream.sendall(new_request + body)

        # 读上游响应, 转发给客户端
        response = b""
        # 先读响应头
        while b"\r\n\r\n" not in response:
            chunk = upstream.recv(4096)
            if not chunk:
                break
            response += chunk
            if len(response) > 100_000:
                break

        # 转发响应头
        client.sendall(response)

        # 判断是否有响应体 (Content-Length 或 chunked)
        resp_head = response.split(b"\r\n\r\n")[0].lower()
        content_length = 0
        for line in resp_head.split(b"\r\n"):
            if line.startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":")[1].strip())
                except ValueError:
                    content_length = 0

        if content_length > 0:
            # 读固定长度响应体
            remaining = content_length - (len(response) - response.find(b"\r\n\r\n") - 4)
            while remaining > 0:
                chunk = upstream.recv(min(65536, remaining))
                if not chunk:
                    break
                client.sendall(chunk)
                remaining -= len(chunk)
        else:
            # chunked 或其他: 透传剩余
            while True:
                chunk = upstream.recv(65536)
                if not chunk:
                    break
                client.sendall(chunk)

        upstream.close()
        client.close()
    except Exception:
        try:
            client.close()
        except Exception:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", LISTEN_PORT))
    server.listen(128)
    print(f"[proxy] HermesDashboard 反向代理: 0.0.0.0:{LISTEN_PORT} -> {UPSTREAM_HOST}:{UPSTREAM_PORT}", flush=True)
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
