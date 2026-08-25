"""Cloudflare Quick Tunnel — không cần tài khoản, không giới hạn thời gian."""

from __future__ import annotations

from .base import Tunnel, TunnelError


class CloudflareTunnel(Tunnel):
    name = "cloudflare"

    def check_available(self) -> None:
        from .. import shell

        if shell.which("cloudflared") is None:
            raise TunnelError(
                "Chưa cài cloudflared. Gọi comfycolab.runtime.install_tunnel_deps() trước."
            )

    def command(self, port: int) -> list[str]:
        if self.token:
            # Tunnel có tài khoản: domain cố định, không đổi mỗi lần chạy.
            return ["cloudflared", "tunnel", "run", "--token", self.token]
        return [
            "cloudflared",
            "tunnel",
            "--url",
            f"http://127.0.0.1:{port}",
            "--no-autoupdate",
        ]

    def extract_url(self, line: str) -> str | None:
        # cloudflared in ra nhiều URL (docs, metrics). Chỉ lấy domain tunnel.
        if "trycloudflare.com" not in line:
            return None
        return super().extract_url(line)
