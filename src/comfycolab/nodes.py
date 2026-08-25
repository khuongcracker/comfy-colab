"""Cài custom node.

Sửa các lỗi của bản gốc:
  - `for list in lists` nằm ngoài guard `isfile` -> NameError khi thiếu file.
  - Hai lệnh `ln -s` nằm trong vòng lặp node nên chạy lại N lần.
  - Node lỗi làm chết cả phiên: ở đây một node hỏng chỉ ghi log và đi tiếp.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import shell
from .catalog import load_nodes


@dataclass
class NodeResult:
    repo: str
    status: str  # installed | skipped | failed
    detail: str = ""


def repo_dir_name(repo_url: str) -> str:
    """Tên thư mục git tạo ra khi clone.

    >>> repo_dir_name("https://github.com/rgthree/rgthree-comfy")
    'rgthree-comfy'
    >>> repo_dir_name("https://github.com/foo/bar.git")
    'bar'
    """
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def install_set(
    set_name: str,
    custom_nodes_dir: Path,
    *,
    extra_repos: list[str] | None = None,
) -> list[NodeResult]:
    """Cài một bộ node theo tên trong nodes.yaml."""
    sets = load_nodes()
    if set_name not in sets:
        known = ", ".join(sorted(sets))
        raise KeyError(f"Không có bộ node {set_name!r}. Đang có: {known}")

    entries = list(sets[set_name])
    for repo in extra_repos or []:
        repo = repo.strip()
        if repo:
            entries.append({"repo": repo, "requirements": True, "ref": None})

    custom_nodes_dir.mkdir(parents=True, exist_ok=True)
    results: list[NodeResult] = []
    for entry in entries:
        results.append(_install_one(entry, custom_nodes_dir))
    return results


def _install_one(entry: dict, custom_nodes_dir: Path) -> NodeResult:
    repo = entry["repo"]
    target = custom_nodes_dir / repo_dir_name(repo)

    if target.exists():
        print(f"  ✔ đã có: {target.name}")
        return NodeResult(repo, "skipped")

    try:
        argv = ["git", "clone", "--depth", "1"]
        if entry.get("ref"):
            argv += ["--branch", str(entry["ref"])]
        argv += [repo, str(target)]
        shell.run(argv, capture=True)
    except shell.CommandError as exc:
        print(f"  ✘ clone hỏng: {repo}")
        return NodeResult(repo, "failed", str(exc))

    if entry.get("requirements", True):
        req = target / "requirements.txt"
        if req.is_file():
            # check=False: requirements của custom node hay xung đột nhau.
            # Một node cài hụt dependency vẫn tốt hơn là chết cả phiên.
            result = shell.pip_install_requirements(req, check=False)
            if result is not None and not result.ok:
                print(f"  ⚠ {target.name}: requirements cài không trọn")
                return NodeResult(repo, "installed", "requirements failed")

    print(f"  ✔ cài xong: {target.name}")
    return NodeResult(repo, "installed")


def summarise(results: list[NodeResult]) -> str:
    installed = sum(1 for r in results if r.status == "installed")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = [r for r in results if r.status == "failed"]
    line = f"Node: {installed} cài mới, {skipped} đã có"
    if failed:
        names = ", ".join(repo_dir_name(r.repo) for r in failed)
        line += f", {len(failed)} HỎNG ({names})"
    return line
