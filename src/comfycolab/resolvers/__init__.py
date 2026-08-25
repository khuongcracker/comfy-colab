"""Registry resolver.

Thứ tự có ý nghĩa: host cụ thể xét trước, `DirectResolver` luôn đứng cuối vì
nó nhận mọi link http(s).
"""

from __future__ import annotations

from .base import Resolved, ResolveError, Resolver
from .civitai import CivitaiResolver
from .direct import DirectResolver
from .huggingface import HuggingFaceResolver

RESOLVERS: list[Resolver] = [
    HuggingFaceResolver(),
    CivitaiResolver(),
    DirectResolver(),  # phải luôn ở cuối
]


def resolve(url: str, *, civitai_token: str | None = None, hf_token: str | None = None) -> Resolved:
    """Phân giải một URL thành link tải thật.

    Luôn trả về `Resolved` hoặc ném `ResolveError` — không bao giờ trả None.
    """
    for r in RESOLVERS:
        if r.can_handle(url):
            token = civitai_token if r.name == "civitai" else hf_token if r.name == "huggingface" else None
            return r.resolve(url, token=token)
    raise ResolveError(
        f"Không phải link tải được: {url!r}. "
        "Cần URL bắt đầu bằng http:// hoặc https://, "
        "hoặc tên model có trong data/models.yaml."
    )


__all__ = ["RESOLVERS", "Resolved", "ResolveError", "Resolver", "resolve"]
