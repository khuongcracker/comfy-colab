"""Giao diện chung cho việc biến một link người dùng dán vào thành link tải thật."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Resolved:
    """Kết quả phân giải một link."""

    url: str
    filename: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.url or not self.url.startswith(("http://", "https://")):
            raise ValueError(f"URL sau khi phân giải không hợp lệ: {self.url!r}")


class Resolver:
    """Một host tải model.

    Thêm host mới = thêm một class ở thư mục này rồi đăng ký trong
    `resolvers/__init__.py`. Không phải sửa file nào khác.
    """

    name = "base"

    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    def resolve(self, url: str, *, token: str | None = None) -> Resolved:
        raise NotImplementedError


class ResolveError(RuntimeError):
    """Không phân giải được link — nói rõ lý do thay vì trả None."""
