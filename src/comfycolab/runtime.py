"""Điều phối một phiên: chuẩn bị -> cài -> chạy.

Mỗi bước đều idempotent. Chạy lại cell không clone lại, không tải lại, không
cài lại — chỉ làm phần còn thiếu.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from . import layout, nodes, shell, tunnels
from .catalog import load_presets
from .config import Config
from .download import download_all

COMFY_REPO = "https://github.com/comfyanonymous/ComfyUI"


def _step(title: str) -> None:
    print(f"\n\033[1;36m▸ {title}\033[0m")


# ---------------------------------------------------------------- chuẩn bị


def mount_drive(paths_data: Path) -> bool:
    """Mount Google Drive. Trả False nếu không chạy trong Colab."""
    try:
        from google.colab import drive  # type: ignore
    except ImportError:
        print("  Không phải môi trường Colab — bỏ qua mount Drive.")
        return False

    mount_point = "/content/drive"
    if os.path.ismount(mount_point) or Path(mount_point, "MyDrive").is_dir():
        print("  Drive đã mount sẵn.")
    else:
        drive.mount(mount_point)

    paths_data.mkdir(parents=True, exist_ok=True)
    print(f"  Dữ liệu: {paths_data}")
    return True


def install_system_deps(*, need_tunnel: str = "cloudflare") -> None:
    """aria2c để tải nhanh, cloudflared nếu dùng tunnel đó."""
    shell.apt_install(["aria2"])

    if need_tunnel == "cloudflare" and shell.which("cloudflared") is None:
        deb = "/tmp/cloudflared.deb"
        url = (
            "https://github.com/cloudflare/cloudflared/releases/latest/"
            "download/cloudflared-linux-amd64.deb"
        )
        shell.run(["curl", "-fsSL", "-o", deb, url])
        shell.run(["dpkg", "-i", deb])


# ------------------------------------------------------------------ ComfyUI


def install_comfy(cfg: Config) -> Path:
    """Clone ComfyUI và cài requirements. Bỏ qua nếu đã có."""
    comfy = cfg.paths.comfy
    if not (comfy / "main.py").is_file():
        comfy.parent.mkdir(parents=True, exist_ok=True)
        shell.run(["git", "clone", "--depth", "1", COMFY_REPO, str(comfy)])
    else:
        print("  ComfyUI đã có sẵn.")

    if cfg.comfy_commit:
        # Ghim commit: cần lịch sử đầy đủ nên fetch thêm.
        shell.run(["git", "fetch", "--unshallow"], cwd=comfy, check=False)
        shell.run(["git", "checkout", cfg.comfy_commit], cwd=comfy)
        print(f"  Ghim commit {cfg.comfy_commit[:8]}")

    shell.pip_install(["-r", str(comfy / "requirements.txt")])

    if cfg.frontend_version:
        # Ghim frontend SAU khi cài requirements.
        #
        # Bản gốc làm việc này bằng `sed -i '1s|.*|...'` trên requirements.txt
        # — thay dòng đầu tiên bất kể dòng đó đang là gì. Ngày ComfyUI sắp
        # xếp lại file, lệnh đó xoá mất một dependency.
        shell.pip_install(
            [f"comfyui-frontend-package=={cfg.frontend_version}"]
        )
        print(f"  Ghim frontend {cfg.frontend_version}")

    return comfy


def prepare(cfg: Config) -> None:
    """Toàn bộ phần cài đặt, không khởi chạy."""
    _step("Mount Drive")
    if cfg.mount_drive:
        mount_drive(cfg.paths.data)
    else:
        cfg.paths.data.mkdir(parents=True, exist_ok=True)
        print(f"  Dữ liệu (local): {cfg.paths.data}")

    _step("Cài công cụ hệ thống")
    install_system_deps(need_tunnel=cfg.tunnel)

    _step("Dựng cây thư mục dữ liệu")
    layout.ensure_data_tree(cfg.paths)
    print(f"  Model: {cfg.paths.models}")

    _step("Cài ComfyUI")
    install_comfy(cfg)

    _step(f"Cài custom node (bộ '{cfg.node_set}')")
    results = nodes.install_set(cfg.node_set, cfg.paths.custom_nodes)
    print("  " + nodes.summarise(results))

    if cfg.models:
        _step(f"Tải model ({len(cfg.models)} mục)")
        download_all(
            list(cfg.models),
            cfg.paths.models,
            civitai_token=cfg.civitai_token,
            hf_token=cfg.hf_token,
        )
    else:
        _step("Tải model")
        print("  Không có model nào trong preset — tải sau bằng ComfyUI-Manager.")

    _step("Trỏ ComfyUI về Drive")
    target = layout.write_extra_model_paths(cfg.paths)
    print(f"  {target}")


# ------------------------------------------------------------------- chạy


def launch(cfg: Config | None = None, **kwargs: object) -> None:
    """Cài (nếu cần) rồi chạy ComfyUI, giữ cell sống.

    Gọi được hai kiểu:
        launch(Config.from_notebook(preset="flux"))
        launch(preset="flux", tunnel="cloudflare")
    """
    if cfg is None:
        cfg = Config.from_notebook(**kwargs)  # type: ignore[arg-type]

    started = time.monotonic()
    prepare(cfg)
    print(f"\n\033[1;32m✔ Cài đặt xong sau {time.monotonic() - started:.0f}s\033[0m")

    tunnel = tunnels.build(
        cfg.tunnel, region=cfg.tunnel_region, token=cfg.tunnel_token
    )
    if tunnel:
        _step(f"Mở tunnel ({tunnel.name})")
        tunnel.start(cfg.port)
        print("  Đang chờ ComfyUI sẵn sàng, link sẽ hiện ngay bên dưới...")
    else:
        print(f"\n  Chạy local, không tunnel: http://127.0.0.1:{cfg.port}")

    _step("Khởi chạy ComfyUI")
    argv = [sys.executable, "main.py"] + layout.launch_args(
        cfg.paths, cfg.port, cfg.extra_args
    )
    # Chạy foreground: cell sống chừng nào server còn sống. Dừng bằng nút
    # stop của Colab — không cần pkill (bản gốc dùng `pkill -f main.py`,
    # giết luôn mọi tiến trình khác trùng tên).
    shell.run(argv, cwd=cfg.paths.comfy, check=False)


def list_presets() -> None:
    """In các preset đang có — tiện gọi trong notebook."""
    for name, spec in sorted(load_presets().items()):
        models = spec.get("models") or []
        note = spec.get("note", "")
        print(f"  {name:<8} nodes={spec['nodes']:<6} models={len(models):<2} {note}")
