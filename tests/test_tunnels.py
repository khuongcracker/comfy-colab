"""Tunnel — lệnh sinh ra, cách bắt URL, và hai hàm chờ.

Không mock socket/HTTP: dựng server thật trên localhost rồi đo.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
import time

import pytest

from comfycolab import tunnels
from comfycolab.tunnels import TunnelError, wait_for_port, wait_for_url
from comfycolab.tunnels.cloudflare import CloudflareTunnel
from comfycolab.tunnels.pinggy import REGIONS, PinggyTunnel


@pytest.fixture
def local_server():
    """HTTP server thật trên cổng tự chọn."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        do_HEAD = do_GET

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield port
    httpd.shutdown()
    httpd.server_close()


class TestWaitForPort:
    def test_thay_port_dang_mo(self, local_server):
        assert wait_for_port(local_server, timeout=5) is True

    def test_port_dong_thi_het_gio(self):
        # cổng gần như chắc chắn không ai nghe
        t0 = time.monotonic()
        assert wait_for_port(59999, timeout=1.5) is False
        assert time.monotonic() - t0 >= 1.4, "phải chờ đủ timeout"


class TestWaitForUrl:
    """Đo được khi test thật: cloudflared in URL trước khi nó định tuyến được."""

    def test_url_song_thi_bao_ngay(self, local_server):
        t0 = time.monotonic()
        assert wait_for_url(f"http://127.0.0.1:{local_server}/", timeout=10) is True
        assert time.monotonic() - t0 < 3, "URL sống thì không được chờ lâu"

    def test_url_chet_thi_het_gio(self):
        assert wait_for_url("http://127.0.0.1:59999/", timeout=2, interval=0.5) is False


class TestCloudflareCommand:
    def test_quick_tunnel_khong_can_token(self):
        cmd = CloudflareTunnel().command(8188)
        assert cmd[:3] == ["cloudflared", "tunnel", "--url"]
        assert "http://127.0.0.1:8188" in cmd

    def test_co_token_thi_chay_named_tunnel(self):
        cmd = CloudflareTunnel(token="abc").command(8188)
        assert cmd == ["cloudflared", "tunnel", "run", "--token", "abc"]

    def test_chi_bat_url_trycloudflare(self):
        t = CloudflareTunnel()
        # cloudflared in ra nhiều URL khác nhau, chỉ một cái là tunnel
        assert t.extract_url("INF |  https://ab-cd.trycloudflare.com  |")
        assert t.extract_url("INF https://developers.cloudflare.com/docs") is None

    def test_thieu_binary_thi_bao_loi_ro(self, monkeypatch):
        monkeypatch.setattr("comfycolab.shell.which", lambda n: None)
        with pytest.raises(TunnelError, match="cloudflared"):
            CloudflareTunnel().check_available()


class TestPinggyCommand:
    def test_free_khong_token(self):
        cmd = PinggyTunnel().command(8188)
        assert cmd[0] == "ssh" and "free.pinggy.io" in cmd
        assert "-R" in cmd and "0:localhost:8188" in cmd

    def test_co_token_va_region(self):
        cmd = PinggyTunnel(region="asia", token="tok").command(8188)
        assert "tok@ap.pro.pinggy.io" in cmd

    def test_bo_qua_link_dashboard(self):
        t = PinggyTunnel()
        assert t.extract_url("https://dashboard.pinggy.io/tunnels") is None
        assert t.extract_url("https://abc.a.free.pinggy.link") is not None

    def test_moi_region_trong_dropdown_deu_hop_le(self):
        for r in ["auto", "asia", "usa", "europe", "australia", "south america"]:
            assert r in REGIONS


class TestRegistry:
    def test_none_tra_ve_none(self):
        assert tunnels.build("none") is None
        assert tunnels.build("") is None

    def test_ten_la_bao_loi_kem_danh_sach(self):
        with pytest.raises(TunnelError, match="cloudflare"):
            tunnels.build("ngrok")

    @pytest.mark.parametrize("name", ["cloudflare", "pinggy"])
    def test_dung_duoc_ca_hai(self, name):
        assert tunnels.build(name).name == name
