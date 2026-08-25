"""Cấu hình một phiên chạy — thay cho `globals()` của bản gốc.

Bản gốc nhét mọi tuỳ chọn vào namespace toàn cục rồi chuẩn hoá bằng
`globals()[key].split(' ')[-1]`, khiến mọi chuỗi có dấu cách bị cắt cụt
(đường dẫn Drive kiểu "SD Data" thành "Data"). Ở đây cấu hình là một object
bất biến, truyền tường minh, và việc bóc emoji chỉ áp đúng vào nhãn dropdown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

# Nhãn dropdown của Colab hay có emoji dẫn đầu: "✨ ComfyUI", "☕️ base".
# Chỉ bóc phần đó, không đụng tới phần còn lại của chuỗi.
_LABEL_PREFIX = re.compile(r"^\s*(?:[^\w\s/\\.\-]+\s*)+", re.UNICODE)


def clean_label(value: str) -> str:
    """Bóc emoji/ký hiệu dẫn đầu khỏi nhãn dropdown.

    >>> clean_label("✨ ComfyUI")
    'ComfyUI'
    >>> clean_label("⚡️ comfy_flux_fast(3min)")
    'comfy_flux_fast(3min)'
    >>> clean_label("/content/drive/MyDrive/SD Data")   # giữ nguyên dấu cách
    '/content/drive/MyDrive/SD Data'
    """
    return _LABEL_PREFIX.sub("", value).strip()


@dataclass(frozen=True)
class Paths:
    """Mọi đường dẫn của một phiên. Không hardcode ở bất kỳ chỗ nào khác."""

    root: Path = Path("/content")
    data: Path = Path("/content/drive/MyDrive/ComfyData")

    @property
    def comfy(self) -> Path:
        return self.root / "ComfyUI"

    @property
    def custom_nodes(self) -> Path:
        return self.comfy / "custom_nodes"

    @property
    def models(self) -> Path:
        """Thư mục model trên Drive — sống qua các phiên Colab."""
        return self.data / "models"

    @property
    def output(self) -> Path:
        return self.data / "output"

    @property
    def input(self) -> Path:
        return self.data / "input"

    @property
    def user(self) -> Path:
        """Setting + workflow đã lưu của ComfyUI."""
        return self.data / "user"

    @property
    def extra_model_paths(self) -> Path:
        return self.comfy / "extra_model_paths.yaml"

    def with_data(self, data: str | Path) -> "Paths":
        return replace(self, data=Path(data))


@dataclass(frozen=True)
class Config:
    """Một phiên chạy ComfyUI trên Colab."""

    paths: Paths = field(default_factory=Paths)

    # Bộ node sẽ cài, tra trong data/nodes.yaml
    node_set: str = "fast"

    # Model tải thêm: tên trong data/models.yaml, hoặc URL trực tiếp.
    models: tuple[str, ...] = ()

    # Tunnel đưa ComfyUI ra ngoài: cloudflare | pinggy | none
    tunnel: str = "cloudflare"
    tunnel_region: str = "auto"
    tunnel_token: str | None = None

    port: int = 8188
    extra_args: str = ""

    # Ghim phiên bản — để trống là lấy mới nhất.
    comfy_commit: str | None = None
    frontend_version: str | None = None

    # Token tải model. KHÔNG có giá trị mặc định: bản gốc nhúng sẵn token
    # CivitAI của tác giả vào repo public, ai cũng xài được hạn mức đó và
    # ngày nó bị thu hồi thì mọi người chết cùng lúc.
    civitai_token: str | None = None
    hf_token: str | None = None

    mount_drive: bool = True

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"port không hợp lệ: {self.port}")
        if self.tunnel not in ("cloudflare", "pinggy", "none"):
            raise ValueError(
                f"tunnel không hỗ trợ: {self.tunnel!r} "
                "(chọn: cloudflare, pinggy, none)"
            )

    # ---- dựng từ input của notebook -------------------------------------

    @classmethod
    def from_notebook(
        cls,
        *,
        preset: str = "fast",
        data_dir: str = "/content/drive/MyDrive/ComfyData",
        models: str = "",
        tunnel: str = "cloudflare",
        tunnel_region: str = "auto",
        extra_args: str = "",
        mount_drive: bool = True,
        civitai_token: str = "",
        hf_token: str = "",
        **overrides: object,
    ) -> "Config":
        """Dựng Config từ các ô @param của notebook.

        Nhận chuỗi thô kiểu Colab (có thể kèm emoji), tự chuẩn hoá. Ô `models`
        nhận nhiều dòng hoặc ngăn bằng dấu phẩy.
        """
        from .catalog import load_presets

        preset_name = clean_label(preset)
        presets = load_presets()
        if preset_name not in presets:
            known = ", ".join(sorted(presets))
            raise KeyError(f"preset không có: {preset_name!r}. Đang có: {known}")

        spec = presets[preset_name]
        cfg = cls(
            paths=Paths().with_data(data_dir.strip() or Paths().data),
            node_set=spec.get("nodes", "fast"),
            models=tuple(spec.get("models", ())) + parse_model_list(models),
            tunnel=clean_label(tunnel).lower(),
            tunnel_region=clean_label(tunnel_region).lower(),
            extra_args=extra_args.strip(),
            mount_drive=mount_drive,
            civitai_token=civitai_token.strip() or None,
            hf_token=hf_token.strip() or None,
            comfy_commit=spec.get("comfy_commit"),
            frontend_version=spec.get("frontend_version"),
        )
        return replace(cfg, **overrides) if overrides else cfg


def parse_model_list(raw: str) -> tuple[str, ...]:
    """Tách ô nhập model thành danh sách.

    Chấp nhận xuống dòng, dấu phẩy, và cho phép comment bằng '#'.
    URL có sẵn dấu phẩy trong query string là chuyện hiếm nhưng vẫn xử được
    bằng cách xuống dòng thay vì dùng phẩy.

    >>> parse_model_list("a, b\\n# bỏ qua\\nc")
    ('a', 'b', 'c')
    >>> parse_model_list("")
    ()
    """
    items: list[str] = []
    for line in raw.splitlines():
        line = line.split("#", 1)[0]
        for part in line.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return tuple(items)
