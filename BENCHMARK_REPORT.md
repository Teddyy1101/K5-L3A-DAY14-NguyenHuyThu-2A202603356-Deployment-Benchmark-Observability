# Benchmark & Observability Report — Day 14

**Họ tên** Nguyễn Huy Thu

**Ngày chạy** 25/11/2026 (GMT+7)

**Môi trường** Windows, Ubuntu WSL2, Python 3.12.3, Docker Desktop Linux Engine 28.3.0.

## 1. SLO của agent

| SLI | Mục tiêu | Ý nghĩa |
| --- | ---: | --- |
| p95 latency của `POST /ask` | ≤ 500 ms | Kiểm soát độ trễ mà phần lớn người dùng trải nghiệm. |
| Tỷ lệ lỗi của `POST /ask` | ≤ 2% | Giới hạn số yêu cầu không nhận được HTTP 200. |
| Accuracy trên golden dataset | ≥ 85% | Ngưỡng quality gate của CI. Riêng bài kiểm cuối CP7 yêu cầu 100% và 0 regression. |

## 2. Benchmark hiệu năng

### Đọc metrics

`http_requests_total` là Counter đếm số request theo method, route và status. `agent_in_flight_requests` là Gauge biểu thị số request đang xử lý. `http_request_duration_seconds` là Histogram đếm độ trễ theo bucket để tính percentile. Middleware sử dụng route template và gom đường dẫn không hợp lệ vào `unmatched` để giữ số time series ổn định khi có nhiều URL khác nhau. Histogram `agent_question_length_chars` đo độ dài câu hỏi đã qua validation và giữ số bucket cố định.

Sau 23 request eval v2, `/metrics` trả `agent_question_length_chars_count 23.0` và `agent_question_length_chars_sum 1066.0`.

### 2.1 Concurrency vs latency (agent v2)

Mỗi lượt gửi 300 request vào v2 với `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. Latency trong các cột percentile tính trên request HTTP 200. RPS và tỷ lệ lỗi tính trên tất cả request.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Tỷ lệ lỗi | SLO |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4.25 | 189.5 | 223.0 | 1696.9 | 0.00% | PASS |
| 10 | 38.16 | 192.0 | 225.9 | 1703.3 | 1.67% | PASS |
| 50 | 112.70 | 210.8 | 292.2 | 1697.8 | 0.33% | PASS |
| 100 | 63.94 | 493.2 | 3057.0 | 3494.7 | 0.67% | FAIL p95 |

Thông lượng tăng đến concurrency 50 rồi giảm ở mức 100. Cả client lẫn agent chạy cùng máy. Khi có 100 request đồng thời, thời gian chờ lập lịch, xử lý kết nối và hàng đợi có thể tăng. Lượt đo này thể hiện điểm bão hòa quan sát được của cấu hình thử nghiệm. `p50`, `p95` và `p99` lần lượt là các ngưỡng mà khoảng 50%, 95% và 99% request hoàn tất trong thời gian đó.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | Avg (ms) | p95 (ms) | p99 (ms) |
| ---: | ---: | ---: | ---: |
| 0 | 193.5 | 224.8 | 254.3 |
| 0.03 | 249.6 | 228.9 | 1701.2 |
| 0.1 | 343.8 | 1693.3 | 1724.1 |

Mỗi lượt gửi 300 request ở concurrency 20. Khi tăng tỷ lệ chậm từ 0 lên 3%, trung bình tăng 56.1 ms còn p99 tăng 1446.9 ms. Ở mức 10%, số request chậm đủ nhiều để p95 vượt ngưỡng 500 ms. SLO dùng p95 để theo dõi trải nghiệm phần lớn người dùng, kèm p99 để phát hiện đuôi phân phối sớm hơn.

## 3. Benchmark chất lượng

Agent v1 chạy trên cổng 8001, v2 chạy trên 8002. Cả ba lượt dùng cùng golden dataset với `MOCK_ERROR_RATE=0` để tránh lỗi upstream ngẫu nhiên ảnh hưởng đến phép so sánh.

| Chỉ số | v1 | v2 ban đầu | v2 sau khi sửa knowledge base |
| --- | ---: | ---: | ---: |
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100% (23/23) |
| Token trung bình / câu | 57.3 | 109.1 | 113.8 |
| p95 latency (ms) | 185.5 | 331.6 | 216.7 |
| Tổng chi phí (USD) | 0.000407 | 0.000762 | 0.000792 |
| Chi phí / câu đúng (USD) | 0.00040695 | 0.00003627 | 0.00003442 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%) | PASS (ngưỡng 100%, 0 regression) |

| ID | Keyword bị thiếu | Sửa trong `KNOWLEDGE_BASE` |
| --- | --- | --- |
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm tài liệu giải thích nội dung, chữ ký và thời hạn JWT khi so sánh với API key. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm tài liệu về các chỉ số Kubernetes HPA dùng để điều chỉnh số pod. |

Retrieval làm tăng lượng token và tổng chi phí. Bản v2 đã sửa trả lời đúng cả 23 câu, nên chi phí trên mỗi câu đúng thấp hơn v1 khoảng 91.5%. p95 của v2 sau sửa cao hơn v1 31.2 ms trong lần đo này. Độ trễ mock có yếu tố ngẫu nhiên, nên chênh lệch p95 giữa hai lượt v2 chưa đủ để kết luận việc thêm tài liệu làm app nhanh hơn. [JSON load test và eval](reports/)

### Quality gate trong CI

Job chạy trên pull request sẽ khởi động v2 với `MOCK_ERROR_RATE=0`, đợi `/health` trả 200 và chạy `eval/run_eval.py --url http://localhost:8002 --min-accuracy 0.85 --baseline <report-v2-tu-nhanh-main>`. `run_eval.py` trả exit code `1` khi accuracy dưới ngưỡng hoặc một câu đã đạt ở baseline bị trượt. Job nhận exit code đó và báo thất bại. Đặt job thành required status check của nhánh `main` để GitHub chặn merge khi gate thất bại.

## 4. Observability stack (production)

### 4.1 Dashboard và bằng chứng

Locust chạy 30 users với ramp-up 5 users/s qua Nginx. Tại thời điểm lấy mẫu, dashboard cho thấy 16.7 request/s, 1.08% lỗi, p95 292.23 ms và 4 request đang xử lý. [Dashboard Grafana](screenshots/grafana-dashboard.png)

1. P95 là 292.23 ms, cao hơn latency trung bình 230.51 ms khoảng 61.72 ms. Một nhóm request chậm vẫn hiện rõ trên p99 dù p95 còn dưới 500 ms.
2. Hai instance nhận 8.22 và 8.49 request/s. Chênh lệch nhỏ trong cửa sổ đo cho thấy Nginx phân phối tải gần đều.
3. Input đạt 1291.08 token/s, output đạt 679.70 token/s. Prompt v2 chứa câu hỏi và tài liệu retrieval, còn output chứa câu trả lời. Panel Grafana xếp chồng hai series.
4. `GET http://localhost:8080/metrics` trả 404 do Nginx giới hạn endpoint metrics. Prometheus scrape trực tiếp port 8000 của agent trong mạng Docker.

### 4.2 Thí nghiệm fault injection

`promtool` 3.16.0 chạy `test rules` với `production/prometheus/alert_rules_test.yml` và trả `SUCCESS`. Test xác minh error rate 10% cần đủ thời gian mới firing, error rate 1% giữ inactive, và instance down đủ lâu làm `AgentInstanceDown` firing.

| Thí nghiệm | Cấu hình thực tế | Alert quan sát | Thời gian tới khi firing | Panel phản ánh |
| --- | --- | --- | ---: | --- |
| A | `MOCK_ERROR_RATE=0.2`, `MOCK_SLOW_RATE=0.03` | `AgentHighErrorRate` | 96.6 s | Error rate và Requests/s theo status code |
| B | Tăng `MOCK_SLOW_RATE` lên `0.3`, giữ `MOCK_ERROR_RATE=0.2` | `AgentHighLatencyP95` | 151.5 s | Latency p95 và Latency `/ask` theo percentile |

Lượt A dùng thời điểm Docker ghi nhận replica cuối khởi động làm mốc. Prometheus ghi mẫu firing đầu tiên lúc 21:47:43 (GMT+7). Lượt B dùng thời điểm áp dụng cấu hình Compose làm mốc. Trong B, tỷ lệ lỗi vượt 5% thì `AgentHighErrorRate` firing lại sau 89.5 s. Khi hai cảnh báo mục tiêu cùng firing, API Prometheus ghi 18.20% lỗi và p95 1.90 s. Chu kỳ scrape, đánh giá rule và thời gian `for` làm thời gian quan sát dài hơn ngưỡng `for` của từng rule. [Hai alert cùng firing](screenshots/prometheus-alert-firing.png)

Đã chạy thí nghiệm A và B theo yêu cầu tối thiểu của Exercise 7.6.

Với thử nghiệm E, agent v1 có thể vẫn trả HTTP 200 với latency và chi phí trong ngưỡng dù câu trả lời kém đi. Chạy eval định kỳ trên golden dataset với endpoint đang phục vụ, theo dõi accuracy theo phiên bản và cảnh báo khi giảm dưới ngưỡng hoặc xuất hiện regression.

### 4.3 Liên kết trace và log

Trace chậm `0f49aad85c59f66b410f2df31371c162` trả HTTP 200 và kéo dài 1729.87 ms. Trong các bước xử lý con, `chat mock-llm-small` chiếm 1697.41 ms (98.12% thời gian request). `agent.retrieve_context` mất khoảng 23.3 ms. [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png)

```json
{"ts":"2026-11-25T14:51:58.232579+00:00","level":"INFO","service":"observable-agent","instance":"949217a0a954","event":"llm_call","trace_id":"0f49aad85c59f66b410f2df31371c162","span_id":"9d916ab6c593d0c3","request_id":"ec0507e99a62","model":"mock-llm-small","agent_version":"v2","input_tokens":95,"output_tokens":55,"cost_usd":0.000047,"llm_ms":1696.6}
```

Trace lỗi `bba495c0c21a040fc66d4f50b675c94c` trả HTTP 503 sau 5927.08 ms. Span `chat mock-llm-small` kéo dài 5897.02 ms và ghi event `exception` với `exception.type = utils.mock_llm.LLMError`. Thông báo lỗi trong Jaeger khớp với log theo cùng `trace_id`. [Trace lỗi trong Jaeger](screenshots/jaeger-error-trace.png)

```json
{"ts":"2026-11-25T14:52:03.354690+00:00","level":"INFO","service":"observable-agent","instance":"949217a0a954","event":"llm_error","trace_id":"bba495c0c21a040fc66d4f50b675c94c","span_id":"24c312251ac5e58b","request_id":"c497482c09e0","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling

Mỗi lần chạy Locust 2 phút với 100 users và ramp-up 10 users/s. Nginx đã nhận đủ số replica trước khi bắt đầu mỗi lần đo. Bảng dùng dòng `POST /ask` của Locust, bao gồm độ trễ của các request thất bại.

| Số replica | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Tỷ lệ lỗi |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 13.34 | 200 | 11000 | 30000 | 363 | 22.41% |
| 3 | 54.95 | 190 | 260 | 1700 | 78 | 1.11% |

Scaling cải thiện p95 từ 11 giây xuống 260 ms và tăng thông lượng khoảng 4.12 lần trong phép thử này. Median thay đổi nhẹ, còn phần lớn lỗi ở cấu hình một replica là gateway timeout HTTP 504. Kết quả phù hợp với tình trạng nghẽn khi tất cả tải đi qua một replica giới hạn 0.5 CPU. Các lượt đo này chưa xác định riêng thời gian đợi CPU, Nginx và client. Với ba replica, p99 còn khoảng 1.7 giây, gần thời lượng của nhánh mock LLM bị chậm. [CSV Locust](benchmark-results/)

## 6. Kết luận

1. P95 và p99 mô tả được nhóm request chậm mà chỉ số trung bình dễ che khuất. Tỷ lệ lỗi bổ sung ngữ cảnh để đọc latency.
2. Eval và quality gate phát hiện phiên bản trả lời kém khi các chỉ số vận hành vẫn trong ngưỡng.
3. Metrics chỉ ra thời điểm phát sinh vấn đề. Trace cho biết bước xử lý chiếm thời gian, còn log JSON liên kết lỗi cụ thể qua `trace_id`.

Với production thật, bổ sung SLI đo từ ngoài load balancer để thấy cả lỗi Nginx 504. Dùng thêm cảnh báo tốc độ tiêu hao error budget theo hai cửa sổ, theo dõi hàng đợi và chạy eval định kỳ để phát hiện regression sau deploy.
