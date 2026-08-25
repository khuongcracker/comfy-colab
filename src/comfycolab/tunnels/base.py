"""Lớp nền cho tunnel.

Bản gốc có 6 hàm `*_thread(port)` và cả 6 chép tay cùng một vòng lặp chờ port
(L233, 254, 270, 296, 311, 350). Sửa logic chờ là phải sửa 6 chỗ. Ở đây vòng
chờ nằm đúng một nơi, mỗi dịch vụ chỉ khai báo lệnh của nó và cách bắt URL.
"""

from __future__ import annotations

import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass

_URL = re.compile(r"https://[^\s\"'<>]+")


class TunnelError(RuntimeError):
    pass


@dataclass
class TunnelHandle:
    """Tunnel đang chạy."""

    name: str
    process: subprocess.Popen[str] | None
    url: str | None = None

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def wait_for_port(port: int, *, host: str = "127.0.0.1", timeout: float = 600.0) -> bool:
    """Chờ tới khi có thứ gì đó lắng nghe trên port. True nếu kịp."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


class Tunnel:
    """Một dịch vụ đưa port local ra Internet.

    Thêm dịch vụ mới = thêm một class ở thư mục này, khai báo `command()`,
    rồi đăng ký trong `tunnels/__init__.py`.
    """

    name = "base"

    def __init__(self, *, region: str = "auto", token: str | None = None) -> None:
        self.region = region
        self.token = token

    # ---- phần con phải cài đặt ------------------------------------------

    def command(self, port: int) -> list[str]:
        raise NotImplementedError

    def extract_url(self, line: str) -> str | None:
        """Bắt URL công khai từ một dòng output. None nếu dòng đó không phải."""
        match = _URL.search(line)
        return match.group(0) if match else None

    def check_available(self) -> None:
        """Ném TunnelError nếu thiếu binary/token. Mặc định không kiểm tra."""

    # ---- phần dùng chung -------------------------------------------------

    def start(self, port: int, *, wait_timeout: float = 600.0) -> TunnelHandle:
        """Chờ port sống rồi mở tunnel. Trả về handle có `.url` khi bắt được."""
        from .. import shell

        self.check_available()
        handle = TunnelHandle(name=self.name, process=None)

        def worker() -> None:
            if not wait_for_port(port, timeout=wait_timeout):
                print(f"⚠ {self.name}: chờ quá {wait_timeout:.0f}s mà port {port} chưa mở.")
                return
            try:
                proc = shell.run_bg(self.command(port))
            except FileNotFoundError:
                print(f"⚠ {self.name}: chưa cài binary, bỏ qua tunnel.")
                return
            handle.process = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                url = self.extract_url(line)
                if url and not handle.url:
                    handle.url = url
                    print(f"\n🔗 Mở ComfyUI tại: {url}\n")

        threading.Thread(target=worker, daemon=True, name=f"tunnel-{self.name}").start()
        return handle
