"""Catalog — dữ liệu phải đọc được và nhất quán."""

from __future__ import annotations

import pytest

from comfycolab.catalog import load_models, load_nodes
from comfycolab.nodes import repo_dir_name


class TestNodes:
    def test_doc_duoc_cac_bo(self):
        sets = load_nodes()
        assert {"fast", "base", "full", "none"} <= set(sets)

    def test_extends_ke_thua_that(self):
        sets = load_nodes()
        fast = {n["repo"] for n in sets["fast"]}
        base = {n["repo"] for n in sets["base"]}
        assert fast < base, "base phải bao trùm fast"

    def test_khong_trung_repo_trong_mot_bo(self):
        for name, entries in load_nodes().items():
            repos = [e["repo"] for e in entries]
            assert len(repos) == len(set(repos)), f"bộ {name} có repo trùng"

    def test_moi_repo_deu_la_url_git(self):
        for name, entries in load_nodes().items():
            for e in entries:
                assert e["repo"].startswith("https://"), f"{name}: {e['repo']}"

    def test_bo_none_rong(self):
        assert load_nodes()["none"] == []


class TestRepoDirName:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/rgthree/rgthree-comfy", "rgthree-comfy"),
            ("https://github.com/foo/bar.git", "bar"),
            ("https://github.com/foo/bar/", "bar"),
        ],
    )
    def test_tach_ten_thu_muc(self, url, expected):
        assert repo_dir_name(url) == expected


class TestModels:
    def test_moi_model_co_url_va_dir(self):
        for name, spec in load_models().items():
            assert spec["url"].startswith("https://"), name
            assert spec["dir"], name

