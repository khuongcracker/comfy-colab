"""Chỗ lưu model và ước lượng dung lượng."""

from __future__ import annotations

import pytest

from comfycolab.catalog import load_models
from comfycolab.config import Config, Paths
from comfycolab.runtime import estimate_size_gb


class TestModelStorage:
    def test_mac_dinh_luu_tren_drive(self):
        assert Paths().models_on_drive is True
        assert Paths().models.as_posix().startswith("/content/drive/")

    def test_session_dung_dia_tam(self):
        p = Paths().with_model_storage(False)
        assert p.models.as_posix() == "/content/models"

    def test_output_luon_o_drive_du_model_o_dia_tam(self):
        """Ảnh xuất phải sống qua phiên kể cả khi model thì không."""
        p = Paths().with_model_storage(False)
        assert p.output.as_posix().startswith("/content/drive/")
        assert p.user.as_posix().startswith("/content/drive/")

    @pytest.mark.parametrize("choice,on_drive", [("drive", True), ("session", False)])
    def test_from_notebook_doc_dung_lua_chon(self, choice, on_drive):
        cfg = Config.from_notebook(node_set="fast", model_storage=choice)
        assert cfg.paths.models_on_drive is on_drive


class TestDefaultLaNhe:
    """Đường mặc định phải dựng được ComfyUI mà KHÔNG tải model nào.

    Thứ cần biết trước tiên là ComfyUI có chạy không, chứ không phải chờ
    vài GB rồi mới biết.
    """

    def test_khong_truyen_gi_thi_khong_co_model(self):
        assert Config.from_notebook().models == ()

    def test_khong_truyen_gi_thi_bo_node_toi_thieu(self):
        assert Config.from_notebook().node_set == "fast"

    def test_o_models_rong_van_hop_le(self):
        assert Config.from_notebook(node_set="base", models="   ").models == ()


class TestSizeEstimate:
    def test_moi_model_khai_size(self):
        for name, spec in load_models().items():
            assert spec["size_gb"], f"{name} thiếu size_gb — check_space sẽ tính hụt"

    def test_rong_la_khong(self):
        assert estimate_size_gb([]) == 0

    def test_url_la_khong_tinh_duoc(self):
        assert estimate_size_gb(["https://example.com/x.safetensors"]) == 0

    def test_cong_dung_tu_catalog(self):
        catalog = load_models()
        names = ["sdxl-base", "sdxl-vae"]
        expected = sum(catalog[n]["size_gb"] for n in names)
        assert estimate_size_gb(names) == pytest.approx(expected)
