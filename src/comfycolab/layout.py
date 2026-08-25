"""Nối ComfyUI với dữ liệu trên Drive.

Bản gốc vừa dùng `extra_model_paths.yaml` (cơ chế chính thức của ComfyUI)
vừa tạo symlink cho cùng mục đích, nên có hai nguồn sự thật đá nhau. Ở đây
chia rõ:

  - MODEL  -> `extra_model_paths.yaml`. ComfyUI đọc trực tiếp, không cần
             symlink, và người dùng đổi đường dẫn không phải dựng lại link.
  - INPUT / OUTPUT / USER -> tham số dòng lệnh của ComfyUI.

Không còn symlink nào cả. Ít thứ hỏng hơn.
"""

from __future__ import annotations

from pathlib import Path

from .config import Paths

# Thư mục con trong models/ mà ComfyUI biết.
#
# Lấy từ `folder_names_and_paths` trong folder_paths.py của ComfyUI — chỉ
# những khoá trỏ vào `models_dir`. KHÔNG đưa `custom_nodes` và `datasets`
# vào đây: chúng nằm dưới base_path chứ không phải models_dir, khai nhầm là
# ComfyUI đi tìm custom node trên Drive.
#
# Kiểm lại khi ComfyUI cập nhật:
#   grep -oE 'folder_names_and_paths\["[a-z0-9_]+"\] = \(\[os\.path\.join\(models_dir' \
#     folder_paths.py | grep -oE '"[a-z0-9_]+"'
MODEL_DIRS = (
    "audio_encoders",
    "background_removal",
    "checkpoints",
    "classifiers",
    "clip_vision",
    "configs",
    "controlnet",
    "detection",
    "diffusers",
    "diffusion_models",
    "embeddings",
    "frame_interpolation",
    "geometry_estimation",
    "gligen",
    "hypernetworks",
    "latent_upscale_models",
    "loras",
    "model_patches",
    "optical_flow",
    "photomaker",
    "style_models",
    "text_encoders",
    "upscale_models",
    "vae",
    "vae_approx",
)

# Tên cũ. ComfyUI có `map_legacy()` chuyển `unet` -> `diffusion_models` và
# `clip` -> `text_encoders`, nên khai thêm ở đây giúp thư mục Drive lỡ đặt
# tên cũ vẫn được quét.
LEGACY_DIRS = ("clip", "unet")

DATA_DIRS = ("input", "output", "user")


def ensure_data_tree(paths: Paths) -> None:
    """Tạo cây thư mục dữ liệu trên Drive nếu chưa có."""
    for name in MODEL_DIRS:
        (paths.models / name).mkdir(parents=True, exist_ok=True)
    for name in DATA_DIRS:
        (paths.data / name).mkdir(parents=True, exist_ok=True)


def render_extra_model_paths(paths: Paths) -> str:
    """Sinh nội dung extra_model_paths.yaml trỏ về Drive.

    `is_default: false` để model tải thẳng vào /content vẫn dùng được, Drive
    chỉ là nguồn bổ sung.
    """
    # .as_posix() để output xác định: dự án chỉ chạy trên Colab (Linux),
    # nhưng hay được sửa/test trên Windows. Không có nó thì test ở máy
    # Windows sinh ra "\content\..." và không phản ánh thứ chạy thật.
    lines = [
        "# Sinh tự động bởi comfy-colab. Sửa tay ở đây sẽ bị ghi đè.",
        "comfy_colab:",
        f"    base_path: {paths.models.as_posix()}",
        "    is_default: false",
    ]
    for name in MODEL_DIRS + LEGACY_DIRS:
        lines.append(f"    {name}: {name}")
    return "\n".join(lines) + "\n"


def write_extra_model_paths(paths: Paths) -> Path:
    target = paths.extra_model_paths
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_extra_model_paths(paths), encoding="utf-8")
    return target


def launch_args(paths: Paths, port: int, extra: str = "") -> list[str]:
    """Tham số dòng lệnh cho main.py của ComfyUI."""
    args = [
        "--listen",
        "127.0.0.1",
        "--port",
        str(port),
        "--preview-method",
        "auto",
        "--extra-model-paths-config",
        paths.extra_model_paths.as_posix(),
        "--input-directory",
        paths.input.as_posix(),
        "--output-directory",
        paths.output.as_posix(),
        "--user-directory",
        paths.user.as_posix(),
    ]
    if extra.strip():
        # Tách theo quy tắc shell để "--a b" và '--x "y z"' đều đúng.
        import shlex

        args.extend(shlex.split(extra))
    return args
