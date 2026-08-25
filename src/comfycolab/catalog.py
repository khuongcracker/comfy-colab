"""Đọc catalog — lớp dữ liệu tách hẳn khỏi code.

Thêm node, thêm model, thêm preset chỉ cần sửa file YAML trong `data/`,
không đụng một dòng Python nào. Đây là ý tưởng đúng nhất của bản gốc (họ để
node ở .txt, model ở .json) và được giữ nguyên tinh thần, chỉ gom về một
định dạng có schema thay vì ba định dạng rời.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


class CatalogError(RuntimeError):
    pass


def _load_yaml(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    if not path.is_file():
        raise CatalogError(f"Thiếu file catalog: {path}")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - Colab luôn có pyyaml
        raise CatalogError(
            "Cần pyyaml để đọc catalog. Cài bằng: pip install pyyaml"
        ) from exc
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise CatalogError(f"{name} phải là mapping ở cấp cao nhất.")
    return data


@functools.lru_cache(maxsize=None)
def load_nodes() -> dict[str, list[dict[str, Any]]]:
    """Các bộ custom node, theo tên bộ.

    Mỗi bộ có thể `extends` một bộ khác để khỏi chép lại danh sách.
    """
    raw = _load_yaml("nodes.yaml")
    sets: dict[str, list[dict[str, Any]]] = {}

    def build(name: str, seen: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
        if name in sets:
            return sets[name]
        if name in seen:
            raise CatalogError(f"nodes.yaml có vòng lặp extends ở bộ {name!r}.")
        if name not in raw:
            known = ", ".join(sorted(raw))
            raise CatalogError(f"Không có bộ node {name!r}. Đang có: {known}")

        spec = raw[name] or {}
        items: list[dict[str, Any]] = []
        parent = spec.get("extends")
        if parent:
            items.extend(build(parent, seen | {name}))

        for entry in spec.get("nodes") or []:
            items.append(_normalise_node(entry, name))

        # Khử trùng theo repo, giữ thứ tự xuất hiện đầu tiên.
        deduped: list[dict[str, Any]] = []
        seen_repos: set[str] = set()
        for item in items:
            if item["repo"] in seen_repos:
                continue
            seen_repos.add(item["repo"])
            deduped.append(item)

        sets[name] = deduped
        return deduped

    for key in raw:
        build(key)
    return sets


def _normalise_node(entry: Any, set_name: str) -> dict[str, Any]:
    if isinstance(entry, str):
        return {"repo": entry, "requirements": True, "ref": None}
    if isinstance(entry, dict):
        repo = entry.get("repo")
        if not repo:
            raise CatalogError(f"Node trong bộ {set_name!r} thiếu khoá 'repo'.")
        return {
            "repo": repo,
            "requirements": entry.get("requirements", True),
            "ref": entry.get("ref"),
        }
    raise CatalogError(f"Mục node không hợp lệ trong bộ {set_name!r}: {entry!r}")


@functools.lru_cache(maxsize=None)
def load_models() -> dict[str, dict[str, Any]]:
    """Model có tên sẵn → URL + thư mục đích."""
    raw = _load_yaml("models.yaml")
    out: dict[str, dict[str, Any]] = {}
    for name, spec in raw.items():
        if isinstance(spec, str):
            spec = {"url": spec}
        if not isinstance(spec, dict) or "url" not in spec:
            raise CatalogError(f"Model {name!r} phải có khoá 'url'.")
        out[name] = {
            "url": spec["url"],
            "dir": spec.get("dir", "checkpoints"),
            "filename": spec.get("filename"),
            "size_gb": spec.get("size_gb"),
            "note": spec.get("note"),
        }
    return out


@functools.lru_cache(maxsize=None)
def load_presets() -> dict[str, dict[str, Any]]:
    """Preset = một combo node-set + model + phiên bản ghim."""
    raw = _load_yaml("presets.yaml")
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            raise CatalogError(f"Preset {name!r} phải là mapping.")
        if "nodes" not in spec:
            raise CatalogError(f"Preset {name!r} thiếu khoá 'nodes'.")
    return raw


def clear_cache() -> None:
    """Quên catalog đã đọc — dùng khi sửa YAML giữa phiên."""
    load_nodes.cache_clear()
    load_models.cache_clear()
    load_presets.cache_clear()
