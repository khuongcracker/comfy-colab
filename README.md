# comfy-colab

Chạy **ComfyUI** trên Google Colab. Notebook chỉ là giao diện — toàn bộ logic nằm trong package `comfycolab`, import được và test được bằng `pytest` trên máy thường mà không cần mở Colab.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/khuongcracker/comfy-colab/blob/main/ComfyUI_Colab.ipynb)

## Dùng

1. Bấm badge Colab ở trên.
2. Chọn preset trong form.
3. Bấm ▶︎. Lần đầu 3–8 phút tuỳ preset.
4. Link ComfyUI hiện ra trong output.

Model và ảnh xuất nằm trên Google Drive (`MyDrive/ComfyData`), không mất khi Colab ngắt.

## Preset

| Preset | Node | Model kèm | Dùng khi |
|---|---|---|---|
| `fast` | tối thiểu | không | Chỉ cần ComfyUI, tự tải model bằng Manager |
| `sd15` | base | SD 1.5 + upscaler | Test nhanh, máy yếu |
| `sdxl` | base | SDXL base + VAE + upscaler | Làm việc SDXL |
| `flux` | base | Flux schnell đủ bộ | Flux |
| `full` | full | SDXL + upscaler | Bộ node đầy đủ |

## Thêm model / node mà không sửa code

Toàn bộ nằm ở `src/comfycolab/data/`:

- **`models.yaml`** — đặt tên gọi cho model, để khỏi dán URL dài trong notebook
- **`nodes.yaml`** — các bộ custom node, có `extends` để kế thừa
- **`presets.yaml`** — combo node-set + model + phiên bản ghim

Ô **Model tải thêm** trong notebook nhận cả tên trong catalog lẫn URL trực tiếp, nên catalog chỉ là tiện lợi chứ không phải giới hạn.

## Kiến trúc

```
src/comfycolab/
├── config.py        Config dataclass — thay globals()
├── shell.py         run() bọc subprocess, CÓ check exit code
├── download.py      tải model: resolve → fetch → verify, idempotent
├── resolvers/       mỗi host một file (HF, CivitAI, direct fallback)
├── nodes.py         cài custom node theo bộ
├── layout.py        extra_model_paths.yaml + tham số dòng lệnh
├── tunnels/         base class chung + cloudflare/pinggy
├── runtime.py       điều phối: prepare() → launch()
└── data/            DỮ LIỆU: nodes / models / presets
```

Thêm một tunnel mới hoặc một host tải model mới = thêm **một file**, không đụng file cũ.

## Phát triển

```bash
pip install -e ".[dev]"
pytest
```

50 test chạy trong ~0.1s, không cần GPU, không cần Colab, không gọi mạng.

Chuẩn: sửa logic → chạy `pytest` ở máy → xanh rồi mới push. Không phải chạy lại nguyên notebook và chờ vài phút mỗi lần thử.

## Ghi công

Ý tưởng ban đầu tham khảo từ [SDVN-WebUI](https://github.com/StableDiffusionVN/SDVN-WebUI) của StableDiffusion.VN — cụ thể là hai quyết định thiết kế tốt: **tách danh sách node/model ra file dữ liệu**, và **đặt tên preset theo thời gian chờ** thay vì theo tên kỹ thuật.

Code trong repo này viết mới hoàn toàn, không sao chép. Repo gốc không có file LICENSE nên không có file nào của họ được phân phối lại ở đây; các custom node đều được clone từ repo gốc của chính tác giả node lúc chạy.

## License

MIT — xem [LICENSE](LICENSE).
