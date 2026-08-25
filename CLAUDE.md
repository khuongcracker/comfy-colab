# comfy-colab

Chạy ComfyUI trên Google Colab. Notebook mỏng + package Python test được.

## Stack

- Python ≥3.10, chỉ phụ thuộc `pyyaml` lúc chạy
- `pytest` cho test (bao gồm `--doctest-modules`)
- Layout `src/` — package thật ở `src/comfycolab/`
- Không phụ thuộc thư viện của ComfyUI; chỉ gọi `main.py` của nó qua subprocess

## Lệnh

```bash
pip install -e ".[dev]"
pytest                 # 65 test logic, ~0.1s, không cần mạng/GPU/Colab
pytest -m network      # kiểm URL trong catalog còn sống (~20s)
pytest -k resolver     # chạy nhóm
```

## Ranh giới quan trọng

- **`shell.run()` mặc định `check=True`.** Đừng quay lại dùng `os.system` hay magic `!`. Cả điểm khác biệt với bản gốc nằm ở chỗ lệnh hỏng phải nổ chứ không im lặng.
- **Mọi lệnh nhận argv dạng list, không nhận chuỗi.** Nhờ vậy đường dẫn có dấu cách chạy đúng và không có đường shell injection.
- **`DirectResolver` phải luôn đứng cuối `RESOLVERS`** — nó nhận mọi link http(s). Chèn resolver mới vào TRƯỚC nó.
- **Không hardcode đường dẫn.** Tất cả dẫn xuất từ `Paths`. Không viết `/content/ComfyUI` ở bất kỳ đâu ngoài `Paths`.
- **Không nhúng token vào code.** `Config.civitai_token` / `hf_token` mặc định là `None` và phải do người dùng nhập.
- **Chỉ thêm model từ nguồn KHÔNG gated.** Repo HuggingFace gated trả 401 nếu thiếu token và người dùng không hiểu vì sao hỏng. `pytest -m network` bắt được — chạy nó sau mỗi lần sửa `models.yaml`.
- **Preset nặng hơn 15 GB phải ghi "session" trong `note`.** Có test chặn (`test_storage.py`).

## Model paths: chỉ một cơ chế

Model trỏ về Drive bằng `extra_model_paths.yaml` (cơ chế chính thức của ComfyUI). **Không dùng symlink** cho model. Input/output/user đi qua tham số dòng lệnh.

Bản gốc dùng cả hai cùng lúc nên có hai nguồn sự thật đá nhau — đừng lặp lại.

## Chỗ lưu model

Drive free chỉ **15 GB**, đĩa tạm Colab khoảng **80 GB**. `Paths.models_on_drive` quyết định model nằm đâu; output/input/user thì **luôn** ở Drive để không mất.

`runtime.check_space()` cộng `size_gb` trong `models.yaml` rồi cảnh báo trước khi tải. Hạn chế: Drive mount qua FUSE nên `disk_usage` có thể trả dung lượng đĩa nền chứ không phải hạn mức Drive — coi là lưới an toàn, không phải bảo đảm.

## Ghim phiên bản

`comfy_commit` và `frontend_version` trong `presets.yaml`, để trống là lấy mới nhất. Frontend được ghim bằng `pip install` **sau** khi cài requirements — không sửa `requirements.txt` của ComfyUI.

## Ngoài phạm vi (cố ý)

- Chỉ đỡ **ComfyUI**. Không đỡ Forge / Automatic1111 / Kohya / Fooocus / FluxGym.
- **Không cong vênh model.** Đây là tool hạ tầng. Model là việc của người dùng và sẽ thay đổi — đừng thêm lại lớp preset bó node với model (xem ADR-008). `models.yaml` chỉ là lối tắt tuỳ chọn, xoá sạch vẫn phải chạy.
- **Đường mặc định phải nhẹ.** Bấm chạy là chỉ dựng ComfyUI, không tải model nào. Có test chặn (`test_storage.py::TestDefaultLaNhe`).
- Chỉ chạy **Colab**. Có giả định `/content` và Google Drive. Muốn đỡ RunPod/local thì phải bóc giả định đó ra khỏi `Paths` trước.
- Không vá frontend JS. Bản gốc string-replace vào bundle đã minify để đổi default workflow — bỏ hẳn, quá giòn.

## Chưa kiểm chứng

Toàn bộ phần side effect (`runtime.py`: mount Drive, clone, cài node, chạy server) **chưa chạy thật trên Colab**. Test hiện tại chỉ phủ phần logic thuần. Lần chạy Colab đầu tiên phải coi là smoke test.
