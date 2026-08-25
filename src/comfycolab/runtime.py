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
from .catalog import load_models, load_nodes
from .config import Config
from .download import download_all

COMFY_REPO = "https://github.com/comfyanonymous/ComfyUI"


def _step(title: str) -> None:
    print(f"\n\033[1;36m▸ {title}\033[0m")


def estimate_size_gb(models: tuple[str, ...] | list[str]) -> float:
    """Ước lượng tổng dung lượng model, theo `size_gb` khai trong models.yaml.

    URL trực tiếp không biết trước dung lượng nên tính là 0 — đây là ước lượng
    để cảnh báo sớm, không phải con số chính xác.
    """
    catalog = load_models()
    return sum(catalog[m]["size_gb"] or 0 for m in models if m in catalog)


def check_space(cfg: Config) -> None:
    """Cảnh báo TRƯỚC khi tải, thay vì để aria2c chết vì hết chỗ sau 10 phút.

    Hạn chế đã biết: Drive mount qua FUSE nên `disk_usage` có thể trả dung
    lượng của đĩa nền chứ không phải hạn mức Drive thật. Khi đó cảnh báo sẽ
    không nổ dù Drive đã đầy — coi đây là lưới an toàn, không phải bảo đảm.
    """
    import shutil

    need = estimate_size_gb(cfg.models)
    if need <= 0:
        return

    target = cfg.paths.models
    target.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(target).free / 1e9

    where = "Drive" if cfg.paths.models_on_drive else "đĩa tạm của phiên"
    print(f"  Cần ~{need:.1f} GB, còn trống {free:.1f} GB trên {where}.")

    if need > free * 0.95:
        hint = ""
        if cfg.paths.models_on_drive:
            hint = (
                "\n  → Đổi Model storage sang 'session' trong notebook: đĩa tạm "
                "Colab rộng hơn nhiều, đổi lại model mất khi ngắt phiên."
            )
        print(
            "\n\033[1;33m⚠ Nhiều khả năng KHÔNG ĐỦ CHỖ.\033[0m "
            f"Cần ~{need:.1f} GB mà chỉ còn {free:.1f} GB.{hint}\n"
        )


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
    shell.apt_install({"aria2": "aria2c"})

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
    keep = "giữ qua phiên" if cfg.paths.models_on_drive else "MẤT khi ngắt phiên"
    print(f"  Model : {cfg.paths.models.as_posix()}  ({keep})")
    print(f"  Output: {cfg.paths.output.as_posix()}")

    _step("Cài ComfyUI")
    install_comfy(cfg)

    _step(f"Cài custom node (bộ '{cfg.node_set}')")
    results = nodes.install_set(cfg.node_set, cfg.paths.custom_nodes)
    print("  " + nodes.summarise(results))

    if cfg.models:
        _step(f"Tải model ({len(cfg.models)} mục)")
        check_space(cfg)
        download_all(
            list(cfg.models),
            cfg.paths.models,
            civitai_token=cfg.civitai_token,
            hf_token=cfg.hf_token,
        )
    else:
        _step("Tải model")
        print("  Không có model nào — tải sau bằng ComfyUI-Manager trong giao diện.")

    _step("Trỏ ComfyUI về Drive")
    target = layout.write_extra_model_paths(cfg.paths)
    print(f"  {target}")


# ------------------------------------------------------------------- chạy


def launch(cfg: Config | None = None, **kwargs: object) -> None:
    """Cài (nếu cần) rồi chạy ComfyUI, giữ cell sống.

    Gọi được hai kiểu:
        launch(Config.from_notebook(node_set="base"))
        launch(node_set="base", tunnel="cloudflare")
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


def list_node_sets() -> None:
    """In các bộ node đang có — tiện gọi trong notebook."""
    for name, entries in sorted(load_nodes().items()):
        names = ", ".join(e["repo"].rsplit("/", 1)[-1] for e in entries) or "(trống)"
        print(f"  {name:<6} {len(entries):>2} node  {names}")
