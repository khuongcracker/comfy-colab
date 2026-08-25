"""Chỗ lưu model và ước lượng dung lượng."""

from __future__ import annotations

import pytest

from comfycolab.catalog import load_models, load_presets
from comfycolab.config import Config, Paths
from comfycolab.runtime import estimate_size_gb

# Drive miễn phí của Google. Preset vượt ngưỡng này phải nói rõ trong note.
DRIVE_FREE_GB = 15.0


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

    @pytest.mark.parametrize("choice,on_drive", [("drive", True), ("session", False)])
    def test_from_notebook_doc_dung_lua_chon(self, choice, on_drive):
        cfg = Config.from_notebook(preset="fast", model_storage=choice)
        assert cfg.paths.models_on_drive is on_drive


class TestSizeEstimate:
    def test_moi_model_khai_size(self):
        for name, spec in load_models().items():
            assert spec["size_gb"], f"{name} thiếu size_gb — check_space sẽ tính hụt"

    def test_preset_rong_la_khong(self):
        assert estimate_size_gb([]) == 0

    def test_url_la_khong_tinh_duoc(self):
        assert estimate_size_gb(["https://example.com/x.safetensors"]) == 0

    def test_tong_preset_khop_model(self):
        catalog = load_models()
        for name, spec in load_presets().items():
            names = spec.get("models") or []
            expected = sum(catalog[m]["size_gb"] for m in names if m in catalog)
            assert estimate_size_gb(names) == pytest.approx(expected)

    def test_preset_vuot_drive_free_phai_canh_bao_trong_note(self):
        """Ai thêm preset nặng mà quên ghi chú thì test này chặn lại."""
        for name, spec in load_presets().items():
            size = estimate_size_gb(spec.get("models") or [])
            if size > DRIVE_FREE_GB:
                note = (spec.get("note") or "").lower()
                assert "session" in note, (
                    f"preset {name!r} cần ~{size:.1f} GB (> {DRIVE_FREE_GB} GB Drive "
                    "free) nhưng note không nhắc chọn Model storage = session"
                )
