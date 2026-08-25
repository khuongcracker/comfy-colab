"""Phân giải spec model và layout."""

from __future__ import annotations

import pytest

from comfycolab.config import Paths
from comfycolab.download import DownloadError, parse_spec
from comfycolab.layout import MODEL_DIRS, launch_args, render_extra_model_paths


class TestParseSpec:
    def test_ten_trong_catalog(self):
        spec = parse_spec("sdxl-base")
        assert spec.url.startswith("https://")
        assert spec.dest_dir == "checkpoints"
        assert spec.source == "catalog:sdxl-base"

    def test_ten_catalog_co_dir_rieng(self):
        assert parse_spec("flux-vae").dest_dir == "vae"

    def test_url_truc_tiep(self):
        spec = parse_spec("https://example.com/m.safetensors")
        assert spec.url == "https://example.com/m.safetensors"
        assert spec.source == "url"

    def test_cu_phap_dat_ten_file(self):
        spec = parse_spec("https://example.com/x?a=1@=ten.safetensors")
        assert spec.filename == "ten.safetensors"
        assert spec.url == "https://example.com/x?a=1"

    def test_tu_them_duoi_safetensors(self):
        assert parse_spec("https://e.com/x@=ten").filename == "ten.safetensors"

    def test_ten_la_bao_loi_kem_goi_y(self):
        with pytest.raises(DownloadError) as exc:
            parse_spec("khong-ton-tai")
        assert "models.yaml" in str(exc.value)

    def test_dong_rong_bao_loi(self):
        with pytest.raises(DownloadError):
            parse_spec("   ")


class TestLayout:
    def test_yaml_chua_moi_thu_muc_model(self):
        text = render_extra_model_paths(Paths())
        for name in MODEL_DIRS:
            assert f"{name}: {name}" in text

    def test_yaml_tro_dung_base_path(self):
        paths = Paths().with_data("/content/drive/MyDrive/Test")
        text = render_extra_model_paths(paths)
        # posix cố định, không phụ thuộc OS đang chạy test
        assert "base_path: /content/drive/MyDrive/Test/models" in text

    def test_yaml_luon_posix_du_test_tren_windows(self):
        text = render_extra_model_paths(Paths().with_data("/content/drive/MyDrive/Co Dau Cach"))
        assert "\\" not in text
        assert "/Co Dau Cach/models" in text

    def test_launch_args_co_extra_model_paths(self):
        args = launch_args(Paths(), 8188)
        assert "--extra-model-paths-config" in args
        assert "--port" in args and "8188" in args

    def test_extra_args_tach_dung_kieu_shell(self):
        args = launch_args(Paths(), 8188, '--lowvram --note "co dau cach"')
        assert "--lowvram" in args
        assert "co dau cach" in args, "chuỗi trong nháy phải giữ nguyên"
