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
    # url đã có KHÔNG có nghĩa là dùng được ngay — xem wait_for_url().
    ready: bool = False

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


def wait_for_url(url: str, *, timeout: float = 60.0, interval: float = 3.0) -> bool:
    """Dò xem URL công khai đã đi được chưa. Best-effort, không bảo đảm.

    Đo được khi test thật: cloudflared in URL ra ngay, nhưng Cloudflare cần
    thêm ~15-30s mới định tuyến tới nó. Bấm sớm là gặp lỗi rồi tưởng hỏng.

    False KHÔNG có nghĩa là tunnel hỏng. Đã gặp trường hợp DNS của mạng đang
    dùng chưa phân giải được subdomain trycloudflare mới (router trả
    "Non-existent domain" trong khi 1.1.1.1 trả bình thường) — lúc đó tunnel
    vẫn chạy tốt với người dùng ở mạng khác. Vì vậy chỗ gọi phải in link ra
    dù hàm này trả về gì.

    Bất kỳ phản hồi HTTP nào cũng tính là thông, kể cả 4xx/5xx: lúc đó
    traffic ĐÃ về tới server local, nó trả gì là việc của ComfyUI.
    """
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "comfy-colab"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.HTTPError:
            return True  # có phản hồi = đường đã thông
        except Exception:
            time.sleep(interval)
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
                    print(f"\n🔗 Link: {url}")
                    print("   Cloudflare cần ~15-30s để định tuyến, chờ chút...")
                    if wait_for_url(url):
                        handle.ready = True
                        print(f"\n\033[1;32m✅ Mở ComfyUI tại: {url}\033[0m\n")
                    else:
                        # Không dám khẳng định là hỏng: hay gặp nhất là DNS của
                        # mạng đang dùng chưa biết subdomain mới.
                        print(
                            f"\n\033[1;32m🔗 Mở ComfyUI tại: {url}\033[0m\n"
                            "   (chưa tự xác nhận được đường đi — cứ mở thử.\n"
                            "    Báo 'không tìm thấy máy chủ' thì là DNS mạng của bạn\n"
                            "    chưa nhận subdomain mới: đổi DNS sang 1.1.1.1 hoặc\n"
                            "    8.8.8.8, hoặc mở bằng mạng 4G để kiểm chứng.)\n"
                        )

        threading.Thread(target=worker, daemon=True, name=f"tunnel-{self.name}").start()
        return handle
