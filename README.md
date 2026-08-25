# comfy-colab

**Cơ sở để chạy ComfyUI trên Google Colab.** Notebook chỉ là giao diện — toàn bộ logic nằm trong package `comfycolab`, import được và test được bằng `pytest` trên máy thường mà không cần mở Colab.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/khuongcracker/comfy-colab/blob/main/ComfyUI_Colab.ipynb)

## Dùng

1. Bấm badge Colab ở trên.
2. Bấm ▶︎. Khoảng 2–4 phút.
3. Link ComfyUI hiện ra trong output.

Mặc định **không tải model nào** — mục tiêu là ComfyUI chạy được trước đã. Model thì tải bằng **ComfyUI-Manager** ngay trong giao diện, hoặc dán URL vào ô `Models`.

Ảnh xuất, input và setting luôn nằm trên Google Drive (`MyDrive/ComfyData`) nên không mất khi Colab ngắt.

## Bộ custom node

| Bộ | Số node | Gồm gì |
|---|---|---|
| `fast` (mặc định) | 4 | ComfyUI-Manager, rgthree, Custom-Scripts, use-everywhere |
| `base` | 10 | thêm controlnet_aux, UltimateSDUpscale, TiledDiffusion, Inpaint-CropAndStitch, KJNodes, essentials |
| `full` | 15 | thêm Impact-Pack, WAS, IPAdapter_plus, VideoHelperSuite, RMBG |
| `none` | 0 | ComfyUI trần |

`fast` đã có ComfyUI-Manager nên thêm node gì cũng làm được ngay trong giao diện, không cần sửa gì ở đây.

## Model

Ô **Models** trong notebook nhận:

- URL HuggingFace / CivitAI / link trực tiếp — ngăn nhau bằng dấu phẩy
- `<url>@=ten.safetensors` để tự đặt tên file
- Tên lối tắt khai trong `src/comfycolab/data/models.yaml` (tuỳ chọn, xoá thoải mái)

Thư mục đích mặc định là `checkpoints`. Loại khác (vae, lora, text_encoders…) thì khai `dir` trong `models.yaml`, hoặc dùng Manager cho nhanh.

### Chỗ lưu model

| Lựa chọn | Chỗ lưu | Sức chứa | Sống qua phiên |
|---|---|---|---|
| `drive` (mặc định) | `MyDrive/ComfyData/models` | Drive free **15 GB** | có |
| `session` | `/content/models` | đĩa tạm Colab **~80 GB** | không, mất khi ngắt |

Model nặng (Flux fp8 ~17 GB) không vừa Drive free — chọn `session`. Tool tự cộng dung lượng và cảnh báo trước khi tải.

> ⚠️ Thêm model vào `models.yaml` thì **chỉ dùng nguồn không gated**. Repo HuggingFace gated (phải bấm đồng ý license) trả 401 nếu không có token, và người dùng sẽ không hiểu vì sao hỏng. Chạy `pytest -m network` để kiểm.

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
└── data/            DỮ LIỆU: nodes.yaml, models.yaml
```

Thêm một tunnel mới hoặc một host tải model mới = thêm **một file**, không đụng file cũ.

Lý do đằng sau từng quyết định nằm ở [docs/DECISIONS.md](docs/DECISIONS.md).

## Phát triển

```bash
pip install -e ".[dev]"

pytest                # 65 test logic, ~0.1s, không cần mạng/GPU/Colab
pytest -m network     # kiểm URL trong catalog còn sống (~20s)
```

Chuẩn: sửa logic → chạy `pytest` ở máy → xanh rồi mới push. Không phải chạy lại nguyên notebook và chờ vài phút mỗi lần thử.

## Ngoài phạm vi (cố ý)

- **Chỉ ComfyUI.** Không đỡ Forge / Automatic1111 / Kohya / Fooocus.
- **Chỉ Colab.** Có giả định `/content` và Google Drive.
- **Không cong vênh model.** Tool này lo phần hạ tầng; model là việc của người dùng, thay đổi tuỳ ý.

## Ghi công

Ý tưởng ban đầu tham khảo từ [SDVN-WebUI](https://github.com/StableDiffusionVN/SDVN-WebUI) của StableDiffusion.VN — cụ thể là quyết định thiết kế tốt nhất của họ: **tách danh sách node/model ra file dữ liệu** để thêm bớt không cần sửa code.

Code trong repo này viết mới hoàn toàn, không sao chép. Repo gốc không có file LICENSE nên không có file nào của họ được phân phối lại ở đây; các custom node đều được clone từ repo gốc của chính tác giả node lúc chạy.

## License

MIT — xem [LICENSE](LICENSE).
