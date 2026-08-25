"""Fallback cho mọi host còn lại.

Đây chính là chỗ bản gốc thủng: `check_link()` chỉ `return` trong hai nhánh
huggingface / civitai, nên link GitHub release, S3, hay bất kỳ host nào khác
rơi xuống đáy hàm và nhận `None` ngầm — rồi `None` được nội suy thẳng vào
lệnh shell. Resolver này nhận mọi thứ còn lại và trả link nguyên vẹn.
"""

from __future__ import annotations

from .base import Resolved, Resolver


class DirectResolver(Resolver):
    name = "direct"

    def can_handle(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def resolve(self, url: str, *, token: str | None = None) -> Resolved:
        return Resolved(url=url)
