"""Pinggy — qua SSH, không cần cài binary.

Bản free giới hạn 60 phút mỗi phiên. Có token thì không giới hạn và chọn
được region.
"""

from __future__ import annotations

from .base import Tunnel

REGIONS = {
    "auto": "",
    "usa": "us.",
    "europe": "eu.",
    "asia": "ap.",
    "south america": "br.",
    "australia": "au.",
}


class PinggyTunnel(Tunnel):
    name = "pinggy"

    def command(self, port: int) -> list[str]:
        prefix = REGIONS.get(self.region.lower(), "")
        common = [
            "ssh",
            "-p",
            "443",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ServerAliveInterval=30",
            "-R",
            f"0:localhost:{port}",
        ]
        if self.token:
            return common + [f"{self.token}@{prefix}pro.pinggy.io"]
        return common + ["-L", "4300:localhost:4300", "free.pinggy.io"]

    def extract_url(self, line: str) -> str | None:
        url = super().extract_url(line)
        if not url or "dashboard.pinggy.io" in url:
            return None
        return url
