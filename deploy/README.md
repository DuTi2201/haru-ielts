# Haru trên một VM GCP — một lệnh

Thay cho Railway. Một VM (Debian + Docker) chạy: Postgres 18 + pgvector, Redis, API, worker (kèm beat) và
Caddy (HTTPS tự động). **Mã nguồn** được đóng gói và gửi lên bằng ssh; **dữ liệu** được khôi phục từ bản sao
lưu đêm gần nhất trong bucket GCS riêng (`backup/latest.json`) — do chính worker tạo ra mỗi đêm.

## Lần đầu (một lần)

1. Mở một terminal có `gcloud` đã đăng nhập vào đúng dự án: **Cloud Shell** (console.cloud.google.com, biểu tượng `>_`)
   hoặc máy Mac cài Google Cloud CLI (`gcloud auth login`, `gcloud config set project <ID>`).
2. Đưa thư mục backend vào đó (giải nén gói `.tar.gz`; Cloud Shell: menu ⋮ → Upload).
3. Tạo file bí mật **trên máy đó** (không vào git, không gửi cho ai):
   ```
   cp deploy/env.prod.example .env.prod      # rồi điền; xem ghi chú trong file
   ```
   Cách nhanh: Railway → project Haru → service `api` → Variables → Raw Editor → copy hết → dán vào `.env.prod`,
   xóa `DATABASE_URL`, `REDIS_URL`, `PORT`, `RAILWAY_*` (có để lại cũng bị bỏ qua).
   Riêng khóa service-account (`AUDIO_GCS_CREDENTIALS`) phải ở **một dòng, trong dấu nháy đơn** — Docker biến `\n`
   trong dấu nháy kép thành xuống dòng thật và làm hỏng JSON. Cách sửa chắc chắn:
   ```
   python3 deploy/gcs-key-line.py key.json >> .env.prod      # hoặc: pbpaste | python3 deploy/gcs-key-line.py >> .env.prod
   ```
4. Chạy:
   ```
   ./deploy/haru-gcp.sh up
   ```
   Script kiểm tra `.env.prod` trước (chưa tốn tiền), hiện kế hoạch + chi phí, hỏi một lần, rồi: bật Compute API →
   mở cổng 80/443 (+22) → giữ IP tĩnh → tạo VM → chờ cài Docker → gửi mã nguồn + `.env.prod` → build → **khôi phục
   dữ liệu** → bật api/worker/Caddy → kiểm tra `https://<ip>.sslip.io/healthz`. Lần đầu khoảng 10–15 phút.

Xong, script in địa chỉ API. Đặt nó làm `VITE_API_BASE_URL` của frontend (Lovable), **Publish frontend trước** (bản mới
có component bảng ngữ pháp), rồi mới dùng. `CORS_ORIGINS` trong `.env.prod` phải có tên miền Lovable đã publish.

## Hằng ngày

| Việc | Lệnh |
|---|---|
| Sửa code xong, đẩy lên | `./deploy/haru-gcp.sh ship` (đóng gói → build → chạy lại; dữ liệu giữ nguyên, tự `alembic upgrade head`) |
| Xem tình hình | `./deploy/haru-gcp.sh status` |
| Xem log | `./deploy/haru-gcp.sh logs api -f` (hoặc `worker`, `db`, `caddy`) |
| Sao lưu ngay lên bucket | `./deploy/haru-gcp.sh backup-now` |
| Thay dữ liệu bằng một bản sao lưu | `./deploy/haru-gcp.sh restore [--day 2026-10-20]` |
| Vào VM | `./deploy/haru-gcp.sh ssh` (trên VM: `sudo haru ps`, `sudo haru logs -f worker`) |
| Xóa tất cả (VM, đĩa, IP, firewall) | `./deploy/haru-gcp.sh destroy` — bucket và bản sao lưu không bị đụng tới |

Tùy chọn: `--yes` (không hỏi), `--fresh` (bắt đầu bằng database **trống**, không khôi phục), `--dry-run` (chỉ in lệnh
gcloud sẽ chạy). Biến môi trường: `HARU_PROJECT`, `HARU_ZONE`, `HARU_MACHINE` (mặc định `e2-small`, 2 GB RAM; nếu OOM
hoặc chậm: `e2-medium`), `HARU_DISK_GB`, `HARU_DOMAIN` (tên miền riêng trỏ A-record về IP của VM).

## Dữ liệu đi như thế nào, và điều cần biết

- Khôi phục chỉ xảy ra **lần đầu** (chưa có file `/opt/haru/.initialized` trên VM). Các lần `ship` sau không đụng vào database.
- Thứ tự an toàn: Postgres/Redis lên → nạp bản sao lưu vào database tạm `haru_restore` (đã kiểm tra SHA-256 từng file) →
  chỉ khi nạp xong mới đổi tên thành `haru` → **sau đó** mới bật worker. Lý do: worker khởi động trên database trống sẽ ghi
  đè bản sao lưu của ngày hôm nay bằng cái trống. Nếu khôi phục lỗi, database cũ không bị đụng tới và không có gì được bật.
  Database cũ nằm lại dưới tên `haru_old` (xóa khi chắc chắn: `sudo haru exec db psql -U haru -d postgres -c "DROP DATABASE haru_old"`).
- Dữ liệu mới nhất = bản sao lưu đêm gần nhất (03:00 giờ VN). Những gì xảy ra sau đó trên Railway (đã tắt) không còn.
- Không có bản sao lưu trong bucket, hoặc khóa sai → script dừng và báo rõ; muốn chạy với database trống thì thêm `--fresh`.
- Bốn bảng cache âm thanh không nằm trong bản sao lưu; âm thanh sinh lại khi cần (tốn Chirp/Gemini như bình thường). Bài
  giảng (audio) của các thẻ ngữ pháp đã đổi nội dung cần được sinh lại sau lần deploy đầu.
- VM tự sao lưu mỗi đêm lên bucket (worker + beat), và mỗi lần worker khởi động.

## Bảo mật

- Bí mật chỉ có ở: `.env.prod` trên máy anh và `/opt/haru/.env.prod` (quyền 600) trên VM. Gói mã nguồn loại trừ `.git`,
  `.env*`; script dừng nếu thấy file `.env` lọt vào gói.
- VM **không gắn service account** của GCP: kể cả bị xâm nhập, nó không với tới dự án của anh (khóa bucket đi theo `.env.prod`).
- Chỉ Caddy mở cổng (80/443). Postgres/Redis không mở ra ngoài; mật khẩu Postgres do VM tự sinh (`/opt/haru/compose.env`).
- API vẫn công khai trên Internet (frontend Lovable cần gọi được), giống khi ở Railway; bảo vệ bằng JWT + giới hạn tần suất trong ứng dụng.
- Cổng 22 mặc định mở cho mọi IP (đăng nhập bằng khóa, không mật khẩu). Muốn chặt hơn: `HARU_SSH_SOURCE_RANGES=<ip của anh>/32`.

## Sự cố thường gặp

- `HTTPS does not answer yet`: chờ 1–2 phút (xin chứng chỉ), xem `logs caddy`; cần cổng 80 và 443 mở và tên miền trỏ đúng IP.
- Build chậm/chết do thiếu RAM: `HARU_MACHINE=e2-medium` (tạo mới) hoặc nâng cấp VM trong console rồi `ship` lại.
- VM chưa sẵn sàng: `./deploy/haru-gcp.sh ssh` rồi `sudo tail -50 /var/log/haru-startup.log`.
- Đổi `.env.prod` (ví dụ đổi giọng Chirp): sửa file rồi `./deploy/haru-gcp.sh ship`.
