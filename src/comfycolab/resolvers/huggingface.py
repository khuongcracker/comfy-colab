"""HuggingFace."""

from __future__ import annotations

from .base import Resolved, Resolver


class HuggingFaceResolver(Resolver):
    name = "huggingface"

    def can_handle(self, url: str) -> bool:
        return "huggingface.co" in url

    def resolve(self, url: str, *, token: str | None = None) -> Resolved:
        # Link người ta copy từ trình duyệt là /blob/ (trang xem file).
        # Link tải thật là /resolve/.
        if "/blob/" in url:
            url = url.replace("/blob/", "/resolve/", 1)

        # Bản gốc cắt sạch query bằng `url.split("?")[0]`, làm mất cả những
        # param HuggingFace cần. Ở đây giữ nguyên query.
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return Resolved(url=url, headers=headers)
