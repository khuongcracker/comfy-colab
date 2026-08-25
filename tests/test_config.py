"""Config — trọng tâm là lỗi H-1 của bản gốc."""

from __future__ import annotations

import pytest

from comfycolab.config import Config, Paths, clean_label, parse_model_list


class TestCleanLabel:
    """Lỗi H-1: bản gốc dùng `.split(' ')[-1]` cho MỌI chuỗi config, nên
    đường dẫn có dấu cách bị cắt cụt."""

    def test_boc_emoji_dan_dau(self):
        assert clean_label("✨ ComfyUI") == "ComfyUI"
        assert clean_label("⚡️ fast") == "fast"
        assert clean_label("☕️ base") == "base"

    def test_duong_dan_co_dau_cach_giu_nguyen(self):
        path = "/content/drive/MyDrive/SD Data"
        assert clean_label(path) == path

    def test_tham_so_nhieu_tu_giu_nguyen(self):
        args = "--lowvram --preview-method auto"
        assert clean_label(args) == args

    def test_chuoi_thuong_khong_doi(self):
        assert clean_label("flux") == "flux"


class TestParseModelList:
    def test_xuong_dong_va_dau_phay(self):
        assert parse_model_list("a, b\nc") == ("a", "b", "c")

    def test_bo_qua_comment(self):
        assert parse_model_list("a\n# ghi chú\nb") == ("a", "b")

    def test_rong(self):
        assert parse_model_list("") == ()
        assert parse_model_list("\n\n  \n") == ()


class TestPaths:
    def test_duong_dan_dan_xuat_tu_root(self):
        p = Paths()
        assert p.comfy.name == "ComfyUI"
        assert p.custom_nodes == p.comfy / "custom_nodes"

    def test_doi_data_dir(self):
        p = Paths().with_data("/content/drive/MyDrive/Khac")
        assert p.models.as_posix() == "/content/drive/MyDrive/Khac/models"

    def test_duong_dan_co_dau_cach_khong_bi_cat(self):
        """Lỗi H-1 ở tầng đường dẫn."""
        p = Paths().with_data("/content/drive/MyDrive/Bo Nho Rieng")
        assert p.models.as_posix().endswith("/Bo Nho Rieng/models")


class TestConfigValidation:
    def test_tunnel_la_bao_loi_ngay(self):
        with pytest.raises(ValueError, match="tunnel"):
            Config(tunnel="ngrok")

    def test_port_ngoai_khoang_bao_loi(self):
        with pytest.raises(ValueError, match="port"):
            Config(port=0)

    def test_khong_co_token_mac_dinh(self):
        """Bản gốc nhúng sẵn token CivitAI của tác giả vào repo public."""
        assert Config().civitai_token is None
        assert Config().hf_token is None
