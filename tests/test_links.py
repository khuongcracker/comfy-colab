"""Kiểm mọi URL trong catalog có sống thật không.

Đây là test GỌI MẠNG nên không chạy mặc định. Chạy khi sửa catalog:

    pytest -m network

Bộ test này sinh ra từ một sự cố thật: `black-forest-labs/FLUX.1-schnell` là
repo gated trên HuggingFace, trả 401 nếu không có token. Preset `flux` từng
trỏ vào đó và sẽ hỏng với mọi người dùng chưa có HF token — không test nào
thuần logic bắt được, chỉ có gọi thật mới thấy.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from comfycolab.catalog import load_models, load_nodes

pytestmark = pytest.mark.network

TIMEOUT = 30


def head_status(url: str) -> int | str:
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "comfy-colab-test"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # noqa: BLE001 - báo nguyên nhân cho người đọc
        return f"{type(exc).__name__}"


ALL_NODES = sorted({n["repo"] for entries in load_nodes().values() for n in entries})
ALL_MODELS = sorted(load_models().items())


@pytest.mark.parametrize("repo", ALL_NODES)
def test_repo_node_con_song(repo):
    assert head_status(repo) == 200, f"repo node không truy cập được: {repo}"


@pytest.mark.parametrize("name,spec", ALL_MODELS, ids=[n for n, _ in ALL_MODELS])
def test_model_tai_duoc_khong_can_token(name, spec):
    status = head_status(spec["url"])
    assert status != 401, (
        f"{name}: nguồn GATED (401) — người dùng không có HF token sẽ hỏng. "
        f"Tìm bản mirror không gated. URL: {spec['url']}"
    )
    assert status == 200, f"{name}: HTTP {status} — {spec['url']}"
