"""Registry tunnel.

Bản gốc mở 2–3 tunnel cùng lúc rồi in ra nhiều link, người dùng không biết
dùng cái nào. Ở đây chọn đúng một cái.
"""

from __future__ import annotations

from .base import Tunnel, TunnelError, TunnelHandle, wait_for_port
from .cloudflare import CloudflareTunnel
from .pinggy import PinggyTunnel

TUNNELS: dict[str, type[Tunnel]] = {
    "cloudflare": CloudflareTunnel,
    "pinggy": PinggyTunnel,
}


def build(name: str, *, region: str = "auto", token: str | None = None) -> Tunnel | None:
    """Dựng tunnel theo tên. `none` trả None (chỉ chạy local)."""
    name = name.lower().strip()
    if name in ("none", "", "off"):
        return None
    if name not in TUNNELS:
        known = ", ".join(sorted(TUNNELS) + ["none"])
        raise TunnelError(f"Tunnel không hỗ trợ: {name!r}. Đang có: {known}")
    return TUNNELS[name](region=region, token=token)


__all__ = [
    "TUNNELS",
    "Tunnel",
    "TunnelError",
    "TunnelHandle",
    "build",
    "wait_for_port",
]
