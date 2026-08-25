"""CivitAI — dùng API chính thức, không scrape HTML.

Bản gốc `wget` trang model về rồi regex tìm `"modelVersionId":(\\d+)` trong
HTML. Cách đó gãy mỗi lần CivitAI đổi markup, và khi trượt thì nó trả về một
câu tiếng Việt rồi câu đó bị dùng làm URL.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .base import Resolved, ResolveError, Resolver

_MODEL_PAGE = re.compile(r"civitai\.com/models/(\d+)")
_API_TIMEOUT = 30


class CivitaiResolver(Resolver):
    name = "civitai"

    def can_handle(self, url: str) -> bool:
        return "civitai.com" in url

    def resolve(self, url: str, *, token: str | None = None) -> Resolved:
        version_id = self._version_id(url, token)
        download = f"https://civitai.com/api/download/models/{version_id}"

        headers = {}
        if token:
            # Dùng header thay vì nhét ?token= vào URL: token không lọt vào
            # log của aria2c và không dính vào tên file khi redirect.
            headers["Authorization"] = f"Bearer {token}"
        return Resolved(url=download, headers=headers)

    # ---- nội bộ ---------------------------------------------------------

    def _version_id(self, url: str, token: str | None) -> str:
        # Đã là link tải trực tiếp.
        if "/api/download/models/" in url:
            tail = url.rstrip("/").split("/")[-1]
            return tail.split("?")[0]

        # Người dùng dán link có sẵn modelVersionId.
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "modelVersionId" in query:
            return query["modelVersionId"][0]

        # Link trang model → hỏi API lấy version mới nhất.
        m = _MODEL_PAGE.search(url)
        if not m:
            raise ResolveError(
                f"Không nhận ra dạng link CivitAI: {url}\n"
                "Dùng link trang model (civitai.com/models/...) "
                "hoặc link tải trực tiếp (civitai.com/api/download/models/...)."
            )
        model_id = m.group(1)
        data = self._api(f"https://civitai.com/api/v1/models/{model_id}", token)
        versions = data.get("modelVersions") or []
        if not versions:
            raise ResolveError(
                f"Model CivitAI {model_id} không có phiên bản nào tải được."
            )
        return str(versions[0]["id"])

    @staticmethod
    def _api(url: str, token: str | None) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "comfy-colab"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=_API_TIMEOUT) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            hint = ""
            if exc.code in (401, 403):
                hint = (
                    "\nModel này cần đăng nhập. Lấy API key ở "
                    "civitai.com/user/account rồi điền vào ô CivitAI token."
                )
            raise ResolveError(f"CivitAI trả lỗi HTTP {exc.code} cho {url}.{hint}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ResolveError(f"Không gọi được API CivitAI: {exc}") from exc
