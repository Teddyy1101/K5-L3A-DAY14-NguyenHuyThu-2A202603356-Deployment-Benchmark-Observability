# Day 14 — Deployment trên Render

## URL public

URL public của agent là `https://day14-agent-la98.onrender.com`. Agent Part 6 lên trạng thái `Live` lúc 21:21 (GMT+7) ngày 25/11/2026. Key Value báo `Available`. Bản deploy dùng commit `05e8d13` trên nhánh `main`. [Kiểm tra /health](https://day14-agent-la98.onrender.com/health) · [Bản deploy trên Render](https://dashboard.render.com/web/srv-dc3et5jm8hqs738v0d60/deploys/dep-dc3et63m8hqs738v0egg)

## Cấu hình

| Mục | Giá trị cấu hình |
| --- | --- |
| Nền tảng | Render |
| Nhánh | `main` |
| Blueprint Path | `06-lab-complete/render.yaml` |
| Web Service | `day14-agent-la98`, Docker, Free, Singapore |
| Key Value | `day14-redis-la98`, Free, Singapore, kết nối nội bộ |
| Dockerfile | `06-lab-complete/Dockerfile` |
| Build context | `06-lab-complete/` |
| Health check | `GET /health` |

Blueprint đặt `ENVIRONMENT=production` và lấy `REDIS_URL` từ Key Value. `AGENT_API_KEY` được đặt khi triển khai và lưu trong phần Environment của Web Service. Dockerfile đọc `PORT` do Render cấp. Blueprint áp dụng cấu hình khi được duyệt. [Blueprint trong repo](06-lab-complete/render.yaml) · [Kết quả đồng bộ trên Render](https://dashboard.render.com/blueprint/exs-dc3eslgm7kps73e31vkg/sync/exe-dc3eslom7kps73e320e0)

## Kiểm tra URL public

Chạy trong Bash. Lấy `AGENT_API_KEY` từ phần Environment của Web Service rồi nhập ở dấu nhắc ẩn.

```bash
BASE='https://day14-agent-la98.onrender.com'
read -rsp 'API key: ' AGENT_API_KEY
printf '\n'
curl -sS -o /dev/null -w 'GET /health: %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w 'GET /ready: %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w 'POST /ask thieu key: %{http_code}\n' \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}' "$BASE/ask"
curl -sS -o /dev/null -w 'POST /ask co key: %{http_code}\n' \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}' "$BASE/ask"
unset AGENT_API_KEY
```

| Kiểm tra | Mã yêu cầu | Kết quả thực tế |
| --- | ---: | --- |
| `GET /health` | 200 | 200 |
| `GET /ready` | 200 | 200 |
| `POST /ask` thiếu key | 401 | 401 |
| `POST /ask` có key | 200 | 200 |

## Ảnh CP6

- `screenshots/dashboard.png` cần chụp màn hình Blueprint có Web Service và Key Value. [Mở Blueprint trên Render](https://dashboard.render.com/blueprint/exs-dc3eslgm7kps73e31vkg/sync/exe-dc3eslom7kps73e320e0)
- [Service đang chạy](screenshots/running.png) chụp trực tiếp phản hồi HTTP 200 từ `/health` trên Render.
- [Kết quả kiểm tra HTTP](screenshots/test.png) hiển thị bốn mã HTTP thu được từ URL public.
