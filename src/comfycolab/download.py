"""Tải model — một đường đi duy nhất, có kiểm tra kết quả.

Khác biệt so với bản gốc:
  - Có `check`: tải hỏng thì dừng và nói rõ, không âm thầm chạy tiếp rồi để
    ComfyUI khởi động với model thiếu.
  - Idempotent: file đã có và đủ lớn thì bỏ qua, chạy lại notebook không tải lại.
  - Token đi qua header, không nhét vào URL.
  - Không còn `link.replace('&', '\\&')` — argv dạng list nên không cần escape.
"""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from . import shell
from .catalog import load_models
from .resolvers import ResolveError, resolve

# File nhỏ hơn ngưỡng này gần như chắc chắn là trang lỗi HTML hoặc tải dở,
# không phải model. Bắt sớm còn hơn để ComfyUI nổ lúc load.
MIN_MODEL_BYTES = 64 * 1024

# Cú pháp đặt tên file: "<url>@=<tên>". Giữ tương thích với cách repo gốc làm
# để bro dán lại link cũ vẫn chạy.
NAME_DELIM = "@="


@dataclass(frozen=True)
class ModelSpec:
    """Một model cần tải, đã phân giải xong đích đến."""

    url: str
    dest_dir: str
    filename: str | None = None
    source: str = ""


class DownloadError(RuntimeError):
    pass


def parse_spec(raw: str, *, default_dir: str = "checkpoints") -> ModelSpec:
    """Biến một dòng người dùng nhập thành ModelSpec.

    Nhận ba dạng:
      - tên có trong models.yaml           -> "sdxl-base"
      - URL trực tiếp                      -> "https://..."
      - URL kèm tên file mong muốn         -> "https://...@=ten.safetensors"
    """
    raw = raw.strip()
    if not raw:
        raise DownloadError("Dòng model rỗng.")

    url_part, _, name_part = raw.partition(NAME_DELIM)
    url_part = url_part.strip()
    filename = name_part.strip() or None
    if filename and not _has_model_ext(filename):
        filename += ".safetensors"

    if url_part.startswith(("http://", "https://")):
        return ModelSpec(
            url=url_part, dest_dir=default_dir, filename=filename, source="url"
        )

    catalog = load_models()
    if url_part in catalog:
        entry = catalog[url_part]
        return ModelSpec(
            url=entry["url"],
            dest_dir=entry["dir"],
            filename=filename or entry["filename"],
            source=f"catalog:{url_part}",
        )

    known = ", ".join(sorted(catalog))
    raise DownloadError(
        f"Không hiểu {url_part!r}.\n"
        f"Phải là URL http(s), hoặc một tên trong models.yaml: {known}"
    )


def _has_model_ext(name: str) -> bool:
    return name.endswith((".safetensors", ".ckpt", ".gguf", ".pt", ".pth", ".bin"))


def _guess_filename(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    name = os.path.basename(path)
    return name or "model.safetensors"


def download_model(
    spec: ModelSpec,
    models_root: Path,
    *,
    civitai_token: str | None = None,
    hf_token: str | None = None,
    force: bool = False,
) -> Path:
    """Tải một model về `models_root/<dest_dir>/`. Trả về đường dẫn file."""
    try:
        resolved = resolve(spec.url, civitai_token=civitai_token, hf_token=hf_token)
    except ResolveError as exc:
        raise DownloadError(f"[{spec.source or spec.url}] {exc}") from exc

    target_dir = models_root / spec.dest_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = spec.filename or resolved.filename
    known_name = filename is not None
    if not filename:
        filename = _guess_filename(resolved.url)
    target = target_dir / filename

    if not force and target.is_file() and target.stat().st_size >= MIN_MODEL_BYTES:
        size_mb = target.stat().st_size / 1024 / 1024
        print(f"  ✔ đã có, bỏ qua: {spec.dest_dir}/{filename} ({size_mb:.0f} MB)")
        return target

    print(f"  ↓ tải {spec.dest_dir}/{filename}")
    _fetch(resolved.url, target_dir, filename, resolved.headers, use_name=known_name)

    final = target if target.is_file() else _newest_in(target_dir)
    if final is None or not final.is_file():
        raise DownloadError(
            f"Tải xong nhưng không thấy file ở {target_dir}. "
            f"Nguồn: {resolved.url}"
        )
    if final.stat().st_size < MIN_MODEL_BYTES:
        size = final.stat().st_size
        final.unlink(missing_ok=True)
        raise DownloadError(
            f"File tải về chỉ {size} byte — gần như chắc chắn là trang lỗi "
            f"chứ không phải model.\nNguồn: {resolved.url}\n"
            "Nếu là model CivitAI cần đăng nhập, điền CivitAI token vào notebook."
        )
    return final


def _fetch(
    url: str,
    directory: Path,
    filename: str,
    headers: dict[str, str],
    *,
    use_name: bool,
) -> None:
    """Tải bằng aria2c (nhiều kết nối), fallback curl nếu chưa có aria2c."""
    if shell.which("aria2c"):
        argv: list[str] = [
            "aria2c",
            "--console-log-level=warn",
            "--summary-interval=10",
            "-c",  # tiếp tục file dở
            "-x",
            "8",
            "-s",
            "8",
            "-k",
            "1M",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "-d",
            str(directory),
        ]
        if use_name:
            argv += ["-o", filename]
        for key, value in headers.items():
            argv += ["--header", f"{key}: {value}"]
        argv.append(url)
        shell.run(argv)
        return

    argv = ["curl", "-fL", "--retry", "3", "--retry-delay", "2"]
    for key, value in headers.items():
        argv += ["-H", f"{key}: {value}"]
    if use_name:
        argv += ["-o", str(directory / filename)]
    else:
        argv += ["-O", "-J", "--output-dir", str(directory)]
    argv.append(url)
    shell.run(argv)


def _newest_in(directory: Path) -> Path | None:
    """File mới nhất trong thư mục — dùng khi để server tự đặt tên."""
    files = [p for p in directory.iterdir() if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def download_all(
    specs: list[str],
    models_root: Path,
    *,
    civitai_token: str | None = None,
    hf_token: str | None = None,
) -> list[Path]:
    """Tải cả danh sách. Lỗi được gom lại và báo một lần ở cuối.

    Một model hỏng không nên chặn các model còn lại — nhưng cũng không được
    im lặng. Nên: tải hết những gì tải được, rồi ném lỗi kèm danh sách hỏng.
    """
    done: list[Path] = []
    failed: list[str] = []
    for raw in specs:
        try:
            spec = parse_spec(raw)
            done.append(
                download_model(
                    spec,
                    models_root,
                    civitai_token=civitai_token,
                    hf_token=hf_token,
                )
            )
        except DownloadError as exc:
            print(f"  ✘ {exc}")
            failed.append(raw)

    if failed:
        raise DownloadError(
            "Không tải được "
            f"{len(failed)}/{len(specs)} model: {', '.join(failed)}\n"
            "Sửa lại ô Models rồi chạy lại cell. Model đã tải xong sẽ được bỏ qua."
        )
    return done
