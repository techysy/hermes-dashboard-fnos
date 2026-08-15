#!/usr/bin/env python3
"""Hermes Agent 目标仪表盘代理.

监听本机固定 TCP 端口 (默认 9120), 把 HTTP/WebSocket 请求反向代理到
配置的目标 agent 仪表盘 (默认 127.0.0.1:9119, 可经设置改为任意 IP:端口,
如 192.168.31.31:9119). 这样 fnOS 桌面 iframe 始终指向本机端口, 由本代理转发到目标.

支持 HTTP 与 WebSocket (升级后原始字节透传).
"""
import http.client
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 本机监听端口 (桌面 iframe 指向此端口)
LISTEN_PORT = int(os.environ.get("HERMES_LISTEN_PORT", "9120"))
# 配置目录 (cmd/main 传入, 数据区)
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


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        """把请求转发到目标 agent."""
        backend = _load_target()
        try:
            conn = http.client.HTTPConnection(*backend, timeout=30)
            body = None
            length = self.headers.get("Content-Length")
            if length and length.isdigit():
                body = self.rfile.read(int(length))
            # 重写 Host 头为目标 (规避目标侧域名校验)
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
            headers["Host"] = f"{backend[0]}:{backend[1]}"
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(k, v)
            # WebSocket 升级: 透传原始字节
            if resp.status == 101 and resp.getheader("Upgrade", "").lower() == "websocket":
                self.end_headers()
                sock = resp.fp.raw._sock if hasattr(resp.fp.raw, "_sock") else resp.fp.raw
                _relay(self.connection, sock)
                return
            data = resp.read()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except Exception as e:
            try:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(("proxy error: %s" % e).encode())
            except Exception:
                pass

    def do_GET(self):    self._proxy()  # noqa: N802
    def do_POST(self):   self._proxy()  # noqa: N802
    def do_PUT(self):    self._proxy()  # noqa: N802
    def do_DELETE(self): self._proxy()  # noqa: N802
    def do_OPTIONS(self):self._proxy()  # noqa: N802
    def do_HEAD(self):   self._proxy()  # noqa: N802

    def log_message(self, *args):
        pass


class TcpServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    server = TcpServer(("0.0.0.0", LISTEN_PORT), Handler)
    ip, port = _load_target()
    print(f"hermes agent proxy: 0.0.0.0:{LISTEN_PORT} -> {ip}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
