"""Resolver — trọng tâm là lỗi C-2 của bản gốc."""

from __future__ import annotations

import pytest

from comfycolab.resolvers import ResolveError, resolve


class TestDirectFallback:
    """Lỗi C-2: bản gốc trả None ngầm cho host lạ, rồi None vào lệnh shell."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/foo/bar/releases/download/v1/model.safetensors",
            "https://cdn.example.com/a/b/model.ckpt",
            "http://plain-http.example/model.pth",
        ],
    )
    def test_host_la_van_ra_url_nguyen_ven(self, url):
        assert resolve(url).url == url

    def test_khong_bao_gio_tra_none(self):
        r = resolve("https://example.com/x.safetensors")
        assert r is not None and r.url

    def test_chuoi_khong_phai_url_thi_bao_loi_ro_rang(self):
        with pytest.raises(ResolveError) as exc:
            resolve("day khong phai link")
        assert "http" in str(exc.value)


class TestHuggingFace:
    def test_blob_doi_thanh_resolve(self):
        got = resolve("https://huggingface.co/org/repo/blob/main/m.safetensors").url
        assert got == "https://huggingface.co/org/repo/resolve/main/m.safetensors"

    def test_resolve_giu_nguyen(self):
        url = "https://huggingface.co/org/repo/resolve/main/m.safetensors"
        assert resolve(url).url == url

    def test_giu_query_string(self):
        """Lỗi M-10: bản gốc cắt sạch query bằng split('?')[0]."""
        url = "https://huggingface.co/org/repo/resolve/main/m.safetensors?download=true"
        assert resolve(url).url.endswith("?download=true")

    def test_token_di_qua_header(self):
        r = resolve("https://huggingface.co/o/r/resolve/main/m.safetensors", hf_token="tok")
        assert r.headers["Authorization"] == "Bearer tok"
        assert "tok" not in r.url


class TestCivitai:
    def test_link_tai_truc_tiep_khong_goi_api(self):
        url = "https://civitai.com/api/download/models/12345"
        assert resolve(url).url == url

    def test_model_version_id_trong_query(self):
        url = "https://civitai.com/models/999?modelVersionId=4242"
        assert resolve(url).url == "https://civitai.com/api/download/models/4242"

    def test_token_khong_lot_vao_url(self):
        """Bản gốc nhét ?token=... vào URL nên token lọt vào log aria2c."""
        r = resolve("https://civitai.com/api/download/models/1", civitai_token="secret")
        assert "secret" not in r.url
        assert r.headers["Authorization"] == "Bearer secret"

    def test_link_civitai_khong_nhan_ra_thi_bao_loi(self):
        with pytest.raises(ResolveError):
            resolve("https://civitai.com/user/someone")
