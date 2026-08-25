"""Chạy lệnh ngoài — thay cho magic `!` của notebook.

Lý do tồn tại: magic `!cmd` của IPython nuốt exit code. Lệnh tải model hỏng
thì notebook vẫn chạy tiếp và ComfyUI khởi động với model thiếu, người dùng
chỉ phát hiện khi node báo lỗi. Ở đây mặc định `check=True` — hỏng là dừng
và nói rõ hỏng ở đâu.

Mọi hàm nhận argv dạng list, không nhận chuỗi. Nhờ vậy đường dẫn có dấu cách
không cần quote tay và không có đường cho shell injection.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class CommandError(RuntimeError):
    """Lệnh trả về exit code khác 0."""

    def __init__(self, argv: Sequence[str], returncode: int, output: str = "") -> None:
        self.argv = list(argv)
        self.returncode = returncode
        self.output = output
        pretty = " ".join(shlex.quote(str(a)) for a in argv)
        msg = f"Lệnh thất bại (exit {returncode}): {pretty}"
        if output.strip():
            tail = "\n".join(output.strip().splitlines()[-15:])
            msg += f"\n--- output (15 dòng cuối) ---\n{tail}"
        super().__init__(msg)


@dataclass(frozen=True)
class Result:
    argv: tuple[str, ...]
    returncode: int
    stdout: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(
    argv: Sequence[str | Path],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
    timeout: float | None = None,
) -> Result:
    """Chạy một lệnh.

    capture=False (mặc định) cho output chảy thẳng ra cell notebook, để người
    dùng thấy tiến độ tải model theo thời gian thực. capture=True khi cần đọc
    lại output (ví dụ dò URL tunnel).
    """
    args = [str(a) for a in argv]
    merged_env = None
    if env:
        merged_env = {**os.environ, **env}

    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True,
        timeout=timeout,
    )
    out = proc.stdout or ""
    if check and proc.returncode != 0:
        raise CommandError(args, proc.returncode, out)
    return Result(tuple(args), proc.returncode, out)


def run_bg(
    argv: Sequence[str | Path],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.Popen[str]:
    """Chạy nền, trả Popen để gọi bên ngoài đọc output hoặc kill.

    Dùng cho ComfyUI server và các tiến trình tunnel.
    """
    args = [str(a) for a in argv]
    merged_env = {**os.environ, **env} if env else None
    return subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def which(name: str) -> str | None:
    """Đường dẫn tuyệt đối của một lệnh, hoặc None nếu chưa cài."""
    from shutil import which as _which

    return _which(name)


def apt_install(packages: Iterable[str], *, quiet: bool = True) -> None:
    """Cài gói hệ thống. Bỏ qua gói đã có để chạy lại không tốn thời gian."""
    missing = [p for p in packages if which(p) is None]
    if not missing:
        return
    run(["apt-get", "update", "-qq"], check=False)
    cmd = ["apt-get", "install", "-y"]
    if quiet:
        cmd.append("-qq")
    run(cmd + list(missing))


def pip_install(
    args: Sequence[str],
    *,
    quiet: bool = True,
    check: bool = True,
) -> Result:
    """Gọi pip bằng chính interpreter đang chạy, không phụ thuộc PATH."""
    cmd = [sys.executable, "-m", "pip", "install"]
    if quiet:
        cmd.append("-q")
    return run(cmd + list(args), check=check)


def pip_install_requirements(path: str | Path, *, check: bool = False) -> Result | None:
    """Cài requirements.txt nếu file tồn tại.

    check=False vì requirements của custom node thường có gói hỏng hoặc xung
    đột — một node lỗi không nên làm chết cả phiên. Lỗi được in ra để thấy.
    """
    p = Path(path)
    if not p.is_file():
        return None
    return pip_install(["-r", str(p)], check=check)
