# Day 14 Lab — Mission Answers

## Part 1 — Localhost vs Production (CP1)

### Exercise 1.1 — Các vấn đề trong bản develop

1. **Thông tin xác thực ghi trực tiếp trong mã nguồn.** `OPENAI_API_KEY` và thông tin kết nối database là giá trị minh họa. Nếu dùng thông tin thật theo cách này, người có quyền đọc repo hoặc lịch sử Git có thể lấy được chúng. [develop/app.py](01-localhost-vs-production/develop/app.py#L17)
2. **Log in nội dung câu hỏi và giá trị key.** Khi log được thu thập tập trung, những dữ liệu này có thể xuất hiện trong hệ thống log. Các dòng `print()` hiện tại cũng thiếu trường thống nhất để lọc theo loại sự kiện. [develop/app.py](01-localhost-vs-production/develop/app.py#L33)
3. **Chỉ lắng nghe trên `localhost`.** Nếu chạy trong container, tiến trình chỉ nhận kết nối trên loopback của container. Reverse proxy hoặc dịch vụ khác gọi qua địa chỉ mạng của container sẽ không kết nối được. [develop/app.py](01-localhost-vs-production/develop/app.py#L51)
4. **Cổng `8000` cố định.** Nếu nền tảng cấp một cổng khác qua biến `PORT`, ứng dụng vẫn chạy trên 8000 và nền tảng có thể không truy cập được. [develop/app.py](01-localhost-vs-production/develop/app.py#L52)
5. **Tự tải lại mã nguồn luôn bật.** `reload=True` cho phép tiến trình theo dõi thay đổi file và khởi động lại ứng dụng. Hành vi này hữu ích khi phát triển nhưng có thể gây gián đoạn nếu file thay đổi lúc đang phục vụ. [develop/app.py](01-localhost-vs-production/develop/app.py#L53)
6. **Thiếu endpoint liveness và readiness.** Bản develop chỉ có `GET /` và `POST /ask`. Hệ thống deploy không có probe riêng để kiểm tra app còn sống và xác định khi nào app sẵn sàng nhận traffic. [develop/app.py](01-localhost-vs-production/develop/app.py#L25)

### Exercise 1.2 — Chạy bản develop

Chạy app bằng `python app.py` trong `01-localhost-vs-production/develop/` trên Ubuntu/WSL2. Gửi câu hỏi qua query string.

```bash
curl -i -X POST 'http://localhost:8000/ask?question=Hello'
```

Terminal trả về HTTP 200 cùng câu trả lời của mock LLM.

```http
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 1.3 — So sánh với bản production

Bản production được chạy cục bộ trong `01-localhost-vs-production/production/`. App nhận `question` trong body JSON. Các lệnh sau tái hiện ba kiểm tra HTTP đã thực hiện.

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Hello"}'
```

| Kiểm tra | Mã HTTP quan sát được | Kết quả |
| --- | --- | --- |
| `GET /health` | 200 | `status` là `ok`, response có thông tin uptime và phiên bản. |
| `GET /ready` | 200 | Body là `{"ready":true}`. |
| `POST /ask` | 200 | Body JSON có `question`, `answer` từ mock LLM và `model`. |

| Tiêu chí | Develop | Production | Vì sao quan trọng? |
| --- | --- | --- | --- |
| Cấu hình | Key nằm trong code và cổng được đặt trực tiếp thành `8000`. [app.py](01-localhost-vs-production/develop/app.py#L17), [port](01-localhost-vs-production/develop/app.py#L52) | Đọc key, `HOST`, `PORT` và `DEBUG` từ môi trường. Uvicorn dùng `settings.port`. [config.py](01-localhost-vs-production/production/config.py#L17), [app.py](01-localhost-vs-production/production/app.py#L197) | Có thể thay đổi cổng và cấp thông tin xác thực theo từng môi trường khi deploy cùng một bản code. |
| Health check | Chưa có `/health` và `/ready`. [app.py](01-localhost-vs-production/develop/app.py#L25) | `/health` báo trạng thái process. `/ready` trả 503 nếu cờ readiness chưa bật. [health](01-localhost-vs-production/production/app.py#L135), [readiness](01-localhost-vs-production/production/app.py#L152) | Load balancer có thể kiểm tra readiness trước khi chuyển traffic đến instance còn đang khởi động. |
| Logging | `print()` in câu hỏi, key và câu trả lời. [app.py](01-localhost-vs-production/develop/app.py#L33) | Dùng `logging` và ghi các trường như tên sự kiện, độ dài câu hỏi và độ dài câu trả lời. [app.py](01-localhost-vs-production/production/app.py#L111) | Có thể lọc log theo sự kiện và hạn chế ghi nội dung nhạy cảm khi tra lỗi. |
| Shutdown | Không khai báo hook dọn tài nguyên của ứng dụng khi dừng. [app.py](01-localhost-vs-production/develop/app.py#L13) | Đăng ký lifecycle bằng `lifespan`; khi shutdown, app đặt cờ `is_ready=False` và ghi log. Uvicorn đảm nhiệm trình tự dừng server. [lifespan](01-localhost-vs-production/production/app.py#L40), [shutdown](01-localhost-vs-production/production/app.py#L64) | Lifecycle cho phép dọn tài nguyên khi thay instance. Graceful shutdown cho request đang xử lý cơ hội hoàn thành trước khi process thoát. |

## Part 2 — Docker Containerization (CP2)

### Exercise 2.1 — Dockerfile develop

1. **Base image.** `FROM python:3.11` bắt đầu từ image Python 3.11. [Dockerfile develop](02-docker/develop/Dockerfile#L8)
2. **Working directory.** `WORKDIR /app` đặt thư mục làm việc bên trong image thành `/app`. Các đường dẫn tương đối trong các lệnh sau được tính từ thư mục này. [Dockerfile develop](02-docker/develop/Dockerfile#L11)
3. **Thứ tự `COPY`.** Dockerfile copy `requirements.txt` và cài dependencies trước khi copy mã ứng dụng. Khi chỉ sửa `app.py`, Docker có thể dùng lại layer cài packages nếu dependencies và các bước trước đó giữ nguyên. [Dockerfile develop](02-docker/develop/Dockerfile#L14)
4. **`CMD` và `ENTRYPOINT`.** `CMD` cung cấp lệnh mặc định hoặc đối số mặc định cho `ENTRYPOINT`; đối số chạy container có thể ghi đè `CMD`. `ENTRYPOINT` chọn chương trình chính của container và có thể đổi bằng `--entrypoint`. Bản develop dùng `CMD ["python", "app.py"]`. [Dockerfile develop](02-docker/develop/Dockerfile#L30)

### Exercise 2.2 — Build và chạy container develop

Build context là gốc repo để Dockerfile thấy `02-docker/develop/` và `utils/mock_llm.py`. Container publish cổng 8000. Endpoint develop nhận `question` qua query string.

Docker Hub trả `429` trong lần lấy base image đầu tiên. Hai image dùng để đo ở Exercise 2.3 được build từ Dockerfile của repo bằng Docker Desktop Linux engine, với base images cùng tag lấy qua mirror `mirror.gcr.io`. [Google Artifact Registry](https://docs.cloud.google.com/artifact-registry/docs/pull-cached-dockerhub-images)

Khi chạy `my-agent:develop` trên Docker Desktop, Python báo `accessing a corrupted shared library`. Để hoàn tất kiểm tra HTTP, build cùng Dockerfile với base image Python `3.11-bookworm` qua `--build-context` và gắn tag `my-agent:develop-bookworm`. Bản này trả **200 OK** ở cả `GET /health` và `POST /ask`. Body của `/health` có `"container":true`. [Docker build context](https://docs.docker.com/build/concepts/context/#example-pin-or-override-images)

```bash
curl -i -X POST 'http://127.0.0.1:8000/ask?question=What%20is%20Docker'
```

```http
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3 — Multi-stage build

Stage `builder` cài các công cụ build và Python dependencies. Stage `runtime` bắt đầu từ `python:3.11-slim`, copy packages đã cài cùng mã ứng dụng và chạy dưới user `appuser`. Công cụ build và cache cài đặt nằm ở stage đầu. Sự khác biệt kích thước còn đến từ base image đầy đủ ở bản develop và base slim ở bản production. [Dockerfile production](02-docker/production/Dockerfile#L16), [runtime](02-docker/production/Dockerfile#L36)

| Image | Cột `SIZE` từ `docker images my-agent` | Byte từ `docker image inspect` |
| --- | ---: | ---: |
| `my-agent:develop` | 1,67 GB | 426.319.261 |
| `my-agent:advanced` | 240 MB | 57.408.373 |

Dùng cùng phép đo theo byte từ `docker image inspect` cho hai image, mức giảm là `(426319261 − 57408373) / 426319261 × 100 = 86,53%`.

### Exercise 2.4 — Stack Docker Compose

```text
Client → Nginx (:80) → agent (:8000, mạng nội bộ)
                         ├── Redis (:6379)
                         └── Qdrant (:6333)
```

Nginx chuyển tiếp request HTTP vào agent. Redis được cấu hình làm dịch vụ cache và Qdrant làm vector database. Các mũi tên bên dưới agent thể hiện dependency trong cấu hình Compose. Compose đợi Redis và Qdrant healthy rồi mới khởi động agent. Phần hỏi đáp của lab dùng mock LLM. [docker-compose.yml](02-docker/production/docker-compose.yml#L22), [nginx.conf](02-docker/production/nginx/nginx.conf#L40)

Project `k5-day14-docker` dùng image runtime đã build ở Exercise 2.3 và các image Redis, Qdrant, Nginx đúng tag trong Compose. Các image đã có sẵn cục bộ nên stack được bật với `--no-build --pull never`. Kết quả `docker compose ps` ghi nhận Nginx đang chạy, còn agent, Redis và Qdrant đều healthy.

| Request qua Nginx | Kết quả thực tế |
| --- | --- |
| `GET http://127.0.0.1/health` | `200 OK`, header `Server: nginx`, body báo `status: ok` và phiên bản agent `2.0.0`. |
| `POST http://127.0.0.1/ask` với JSON `{"question":"Explain microservices"}` | `200 OK`, header `Server: nginx`, body chứa câu trả lời của mock LLM. |

Trích response của `POST /ask` qua Nginx.

```http
HTTP/1.1 200 OK
Server: nginx
Content-Type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

## Part 3 — Cloud Deployment (CP6)

### Exercise 3.2 — Cấu hình Render

Agent Part 6 đang chạy trên Render. Kiểm tra từ URL public cho kết quả `/health` **200**, `/ready` **200**, `POST /ask` thiếu key **401**, và có key **200**. [URL public](https://day14-agent-la98.onrender.com) · [Kết quả kiểm tra](DEPLOYMENT.md)

Render đặt tên Web Service `day14-agent-la98` và Key Value `day14-redis-la98` trên gói Free tại Singapore. Agent build từ Dockerfile của `06-lab-complete/`. Render lấy URL Redis nội bộ qua `fromService`, kiểm tra `/health` và nhận `AGENT_API_KEY` trong lúc triển khai. [Blueprint Render](06-lab-complete/render.yaml)

| Mục | Railway | Render |
| --- | --- | --- |
| Định dạng và phạm vi | TOML cấu hình builder và deploy cho agent. | Blueprint YAML khai báo cả Web Service lẫn Key Value. |
| Container và probe | `builder = "DOCKERFILE"` và `healthcheckPath = "/health"`. | `runtime: docker`, đường dẫn Dockerfile và build context, cùng `healthCheckPath: /health`. |
| Redis và API key | Tạo Redis trong project rồi đặt biến tham chiếu và API key trên Dashboard. | Blueprint cấp `REDIS_URL` qua `fromService`; `sync: false` yêu cầu nhập API key trên Dashboard. |

[Cấu hình Railway](06-lab-complete/railway.toml) · [Cấu hình Render](06-lab-complete/render.yaml)

### Exercise 3.3 — Pipeline Cloud Run

1. Cloud Build cài dependencies và chạy `pytest` trong bước `test`.
2. Bước `build` tạo Docker image và gắn tag theo `COMMIT_SHA` cùng tag `latest`.
3. Bước `push` đưa image lên registry, sau đó `gcloud run deploy` chọn tag theo commit để triển khai.
4. `service.yaml` mô tả cổng, giới hạn tài nguyên, autoscaling, probe và biến lấy từ Secret Manager.

[cloudbuild.yaml](03-cloud-deployment/production-cloud-run/cloudbuild.yaml) · [service.yaml](03-cloud-deployment/production-cloud-run/service.yaml)

## Part 4 — API Security (CP3)

Hai bản mẫu được chạy lần lượt trên Ubuntu/WSL2 tại `127.0.0.1:8003` để tránh dùng chung cổng 8000 với các checkpoint khác. Mỗi bản dùng venv và `requirements.txt` của thư mục tương ứng. Key và JWT secret dùng cho kiểm thử được đặt qua biến môi trường.

### Exercise 4.1 — Xác thực bằng API key

Gửi cùng body JSON `{"question":"Hello"}` đến `POST /ask` của bản develop. Khi thiếu header `X-API-Key`, kết quả là:

```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

Khi gửi header `X-API-Key` đúng giá trị đã cấu hình, kết quả là:

```http
HTTP/1.1 200 OK
content-type: application/json

{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 4.2 — Lấy JWT

Gửi `POST /auth/token` với tài khoản demo `student` trên bản production. Endpoint trả **HTTP 200** và cấp `access_token`. Các request gọi agent gửi token qua header `Authorization: Bearer <đã che>`. Server xác minh chữ ký và hạn sử dụng trước khi lấy thông tin người dùng và vai trò từ token.

### Exercise 4.3 — Kiểm tra rate limit

Gửi 20 request liên tiếp tới `POST /ask` với cùng JWT. Lượt **1–10** trả **200**, lượt **11–20** trả **429**. Cửa sổ giới hạn của tài khoản `student` có 60 giây và cho phép 10 request. [rate_limiter.py](04-api-gateway/production/rate_limiter.py#L86)

Trích response của lượt 11.

```http
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
content-type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4 — Cost guard

1. Sau khi xác thực và kiểm tra rate limit, endpoint gọi `check_budget(username)` trước khi gọi mock LLM. Khi chi phí tích lũy của người dùng đã chạm ngân sách ngày, hàm trả **402**. Nếu tổng chi phí chạm ngân sách chung, hàm trả **503**. [app.py](04-api-gateway/production/app.py#L145), [cost_guard.py](04-api-gateway/production/cost_guard.py#L60)
2. Sau khi có câu trả lời, endpoint ước lượng token đầu vào và đầu ra. `record_usage()` cộng số token, số request và chi phí theo đơn giá của từng loại token. Bản mẫu lưu số liệu trong bộ nhớ của tiến trình. [app.py](04-api-gateway/production/app.py#L150), [cost_guard.py](04-api-gateway/production/cost_guard.py#L93)
3. Rate limit kiểm soát tần suất gọi API. Cost guard kiểm soát ngân sách dựa trên lượng token và đơn giá, kể cả khi người dùng gửi ít request nhưng prompt hoặc câu trả lời dài. Hai kiểm tra bảo vệ hai giới hạn khác nhau.

## Part 5 — Scaling & Reliability (CP4)

### Exercise 5.1 — Liveness và readiness

Bản develop được chạy trong Ubuntu/WSL2 trên cổng 8004 để tách khỏi các bài trước. `GET /health` trả **200** với `"status":"ok"`, còn `GET /ready` trả **200** với `"ready":true`.

Liveness cho biết tiến trình còn phản hồi. Readiness cho biết instance đã hoàn tất khởi tạo và có thể nhận traffic. Ở bản develop, hook `lifespan` đặt cờ readiness khi khởi tạo xong và hạ cờ khi shutdown. [app.py](05-scaling-reliability/develop/app.py#L42), [health](05-scaling-reliability/develop/app.py#L104), [readiness](05-scaling-reliability/develop/app.py#L147)

### Exercise 5.2 — Graceful shutdown

Gửi `POST /ask?question=Hello` và gửi `SIGTERM` cho tiến trình agent khoảng 0,5 giây sau khi bắt đầu request. Request đang xử lý vẫn nhận **HTTP 200**. Uvicorn hoàn tất shutdown và tiến trình trả exit code **0**.

Trích log quan sát được.

```text
INFO:     Shutting down
INFO:     127.0.0.1:37922 - "POST /ask?question=Hello HTTP/1.1" 200 OK
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1447]
CP4_SHUTDOWN_EXIT_CODE=0
```

### Exercise 5.3 — Stateless design

Mỗi process có vùng nhớ riêng. Nếu lịch sử hội thoại nằm trong RAM của agent, request kế tiếp có thể được load balancer chuyển tới một instance chưa có lịch sử của session đó. Khi process khởi động lại, bộ nhớ cũ cũng mất. Bản production lưu dữ liệu theo `session_id` trong Redis để mọi instance đọc cùng một lịch sử. [save_session](05-scaling-reliability/production/app.py#L59), [load_session](05-scaling-reliability/production/app.py#L68)

### Exercise 5.4 — Load balancing

Chạy project Compose `k5-day14-scaling` với `--scale agent=3`, dùng image đã build từ Dockerfile production và Redis, Nginx đã có cục bộ. `docker compose ps` báo cả ba instance agent và Redis đều healthy. Gọi `GET http://127.0.0.1:8080/health` qua Nginx nhận **200** và header `X-Served-By: 172.19.0.5:8000`. [Nginx upstream](05-scaling-reliability/production/nginx.conf#L9)

### Exercise 5.5 — Kiểm tra session qua nhiều instance

Chạy nguyên bản `python3 test_stateless.py` trong `05-scaling-reliability/production/`. Năm lần gọi `POST /chat` cùng session được chuyển theo thứ tự sau.

| Request | Instance trả lời |
| ---: | --- |
| 1 | `instance-0e8596` |
| 2 | `instance-9e941b` |
| 3 | `instance-3ab63b` |
| 4 | `instance-0e8596` |
| 5 | `instance-9e941b` |

Đọc history qua Nginx sau lượt thứ năm trả đủ **10 tin nhắn**, gồm năm câu hỏi và năm câu trả lời. Kết quả xác nhận ba instance dùng chung trạng thái session trong Redis khi Nginx phân phối request. Stack được dừng sau kiểm thử.

Trong lượt thử bổ sung, truy vấn history ngay sau khi dừng một instance bị timeout với giới hạn chờ 8 giây của client. Ở lượt chạy lại, sau khi dừng instance đã trả lời câu hỏi đầu và reload Nginx, history vẫn có **2 tin nhắn**. Câu hỏi tiếp theo được một instance khác trả lời, giữ nguyên session và tăng history lên **4 tin nhắn**. Lượt này xác nhận trạng thái trong Redis còn nguyên sau khi một agent dừng.

## Part 6 — Production-ready Agent (CP5)

Agent đọc cấu hình từ biến môi trường và hỗ trợ file `.env` khi chạy local. `GET /health` kiểm tra tiến trình. `GET /ready` ping Redis để xác định app có thể nhận request mới. `POST /ask` yêu cầu `X-API-Key`, kiểm tra số request trong cửa sổ 60 giây và kiểm tra ngân sách ngày trước khi gọi mock LLM.

Rate limiter dùng sorted set trong Redis và kiểm tra, ghi lượt vào cùng một thao tác nguyên tử. Cost guard ghi chi phí ước tính vào Redis, với hạn dùng đến nửa đêm UTC. Hai Uvicorn worker dùng chung Redis. Agent ghi log JSON và đóng kết nối Redis trong hook shutdown.

Dockerfile dùng hai stage, base image slim và user non-root. Compose đặt agent và Redis trên cùng mạng. Cấu hình deploy CP5 dùng Railway với health check tại `/health` và cổng do nền tảng cấp qua `PORT`.

### Kết quả bộ chấm

Chạy lại nguyên bản `python check_production_ready.py` ngày 25/11/2026 trong `06-lab-complete/` trên Ubuntu/WSL2 với Docker 28.3.0. Image đo được **63 MB**, `docker stop` hoàn tất trong **1,2 giây**, exit code **0**. Kiểm tra runtime xác nhận rate limit vẫn còn sau khi restart agent, budget nhỏ trả 402 và SIGTERM vẫn cho request đang chạy trả 200.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

### Kiểm tra bằng Docker Compose

Chạy agent và Redis qua Docker Compose với cổng host 8005. Khi Redis đang chạy, cả hai probe trả **200**, `POST /ask` hợp lệ trả **200**, và request thiếu `question` trả **422**. Sau khi dừng Redis của stack kiểm thử, `/health` vẫn trả **200**, còn `/ready` và `POST /ask` trả **503**. Stack tạm đã được dọn sau kiểm thử.
