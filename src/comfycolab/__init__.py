"""comfy-colab — chạy ComfyUI trên Google Colab.

Notebook chỉ là giao diện. Toàn bộ logic nằm ở đây, import được và test được
trên máy thường mà không cần Colab.

    from comfycolab import Config, launch
    launch(Config.from_notebook(preset="flux"))
"""

from __future__ import annotations

__version__ = "0.1.0"

from .config import Config, Paths
from .runtime import launch, list_presets, prepare

__all__ = ["Config", "Paths", "launch", "list_presets", "prepare", "__version__"]
