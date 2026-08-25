# Quyết định kiến trúc

Ghi lại **vì sao**, để sau này không ai (kể cả mình) vô tình quay ngược lại.

---

## ADR-001 — Viết mới thay vì fork SDVN-WebUI

**Ngày:** 25/08/2026

**Bối cảnh.** Repo gốc [SDVN-WebUI](https://github.com/StableDiffusionVN/SDVN-WebUI) chạy tốt nhưng toàn bộ engine là một cell 813 dòng, đỡ 7 backend, và **không có file LICENSE**.

**Quyết định.** Viết mới hoàn toàn, chỉ ComfyUI. Không sao chép file nào của họ.

**Vì sao.**
- Không LICENSE = mặc định *all rights reserved*. Phân phối lại file của họ trong một repo public là vùng xám pháp lý không đáng dây vào.
- 6 backend còn lại (Forge, Automatic, Kohya, Fooocus, AutoRetouch, FluxGym) chiếm khoảng 40% code mà không dùng tới.
- Fork thì phải sống chung với cấu trúc cũ, mà chính cấu trúc cũ là thứ cần bỏ.

**Đánh đổi.** Mất đường kéo update từ upstream. Chấp nhận được vì mục tiêu là toàn quyền kiểm soát.

**Ghi công** đặt trong README: hai ý tưởng tốt của họ được giữ lại (tách dữ liệu ra file, đặt tên preset theo thời gian chờ).

---

## ADR-002 — `extra_model_paths.yaml`, không symlink

**Bối cảnh.** Bản gốc dùng **cả hai** cho cùng mục đích trỏ model sang Drive: vừa ghi `extra_model_paths.yaml`, vừa `ln -s` một loạt thư mục.

**Quyết định.** Chỉ dùng `extra_model_paths.yaml` cho model. Input/output/user đi qua tham số dòng lệnh của ComfyUI.

**Vì sao.** Hai nguồn sự thật thì sẽ có ngày đá nhau, và không ai nhớ cái nào thắng. `extra_model_paths.yaml` là cơ chế chính thức, đổi đường dẫn không phải dựng lại link, và không để lại symlink chết khi Drive chưa mount.

---

## ADR-003 — Ghim frontend bằng `pip install`, không `sed` vào requirements.txt

**Bối cảnh.** Bản gốc ghim phiên bản frontend bằng:

```
sed -i '1s|.*|comfyui-frontend-package==1.39.19|' /content/ComfyUI/requirements.txt
```

**Quyết định.** Cài requirements bình thường, rồi `pip install comfyui-frontend-package==<version>` **sau**.

**Vì sao.** Lệnh `sed` kia thay dòng đầu tiên bất kể dòng đó đang là gì. Ngày ComfyUI sắp xếp lại requirements, nó xoá mất một dependency và thay bằng thứ khác — hỏng theo kiểu rất khó truy. Cài đè sau đạt cùng kết quả mà không đụng vào file của upstream.

---

## ADR-004 — Bỏ hẳn việc vá default workflow vào frontend

**Bối cảnh.** Bản gốc đọc `index.html` của frontend, regex ra tên file module đã minify, rồi `.replace()` nguyên khối default graph bên trong bundle JS.

**Quyết định.** Không làm. Bỏ tính năng đổi default workflow.

**Vì sao.** Chỉ cần frontend đổi cách bundle là `.replace()` không khớp và **im lặng không làm gì** — người dùng không biết. Đây cũng chính là lý do bản gốc buộc phải ghim cứng phiên bản frontend. Đánh đổi một tính năng nhỏ để bỏ được ràng buộc phiên bản là lời.

Muốn có workflow mặc định thì để file `.json` vào `user/default/workflows/` trên Drive — ComfyUI đọc sẵn, không cần vá gì.

---

## ADR-005 — `shell.run()` nhận argv dạng list, mặc định `check=True`

**Quyết định.** Không dùng magic `!`, không dùng `os.system`, không truyền chuỗi lệnh.

**Vì sao.**
- Magic `!` nuốt exit code → model tải hỏng mà ComfyUI vẫn khởi động. Đây là khác biệt lớn nhất so với bản gốc.
- argv dạng list nên đường dẫn có dấu cách chạy đúng mà không phải quote tay, và không có đường shell injection từ ô nhập của người dùng.
- Bản gốc phải làm `link.replace('&', '\\&')` để né shell — với argv list thì vấn đề đó biến mất.

---

## ADR-006 — Không nhúng token nào trong code

**Bối cảnh.** Bản gốc nhúng sẵn một API token CivitAI thật vào source (lặp 2 lần).

**Quyết định.** `Config.civitai_token` và `hf_token` mặc định `None`, người dùng tự nhập trong notebook. Token đi qua HTTP header, không nhét vào URL.

**Vì sao.** Token trong repo public thì ai cũng xài được hạn mức đó, và ngày nó bị thu hồi thì mọi người dùng chết cùng lúc. Đi qua header thì token không lọt vào log của aria2c.

---

## ADR-007 — Thư mục dữ liệu tên `data/`, không phải `catalog/`

**Bối cảnh.** Ban đầu đặt module `catalog.py` và thư mục dữ liệu `catalog/` cùng cấp trong package.

**Quyết định.** Đổi thư mục thành `data/`.

**Vì sao.** Tên trùng buộc Python phải phân giải giữa module và namespace package. Nó *có* chạy, nhưng là bẫy: đổi thứ tự sys.path hoặc thêm `__init__.py` là hành vi đổi. Không đáng để lại.
