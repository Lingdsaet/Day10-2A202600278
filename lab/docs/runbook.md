# Runbook — Lab Day 10 (incident tối giản)

---

## 1. Symptom (Triệu chứng)
- User / Agent IT Helpdesk cho biết họ đang nhận được quy định đổi trả hàng trong "14 ngày làm việc" thay vì quy định chuẩn là "7 ngày".
- Lệnh Check Freshness báo cáo kết quả `FAIL` liên tục hiển thị chữ đỏ trên log pipeline thông báo `freshness_sla_exceeded`.

---

## 2. Detection (Phát hiện)
- Hệ thống Monitoring phát hiện metric **E3 Expectation** `refund_no_stale_14d_window` đã bị bypass.  
- Evaluation report từ `eval_retrieval.py` cho thấy `hits_forbidden = yes` cho câu hỏi `q_refund_window`.
- Timestamp Age của Manifest ghi nhận ngưỡng thời gian. Kể từ bản cập nhật Bonus, hệ thống phát hiện theo 2 boundaries: `ingest_to_publish_lag_hours` tính khoảng cách giữa việc file export nằm chờ cho tới khi pipeline nạp, và `publish_age_hours` tính khoảng thời gian từ lúc nạp lên vector tới thời điểm hiện tại. Nếu Age vượt quá 24h, hệ thống kích hoạt.

---

## 3. Diagnosis (Chẩn đoán)

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác thực `skipped_validate` đang là true hoặc false, kiểm tra xem `no_refund_fix` có vô ý bị kích hoạt hay không. |
| 2 | Mở `artifacts/quarantine/*.csv` theo `run_id` | Xem liệu có bản ghi có "14 ngày" nào bị rò rỉ mà không chui vào đây hay không; rà soát xem liệu có bản ghi Exported từ tương lai. |
| 3 | Chạy `python eval_retrieval.py` | Kiểm tra lại chỉ số Retrievals có match với file golden `test_questions.json`. |

---

## 4. Mitigation (Khắc phục tạm thời)
- Ngưng sử dụng index embedding cũ: Treo banner "Hệ thống RAG đang nâng cấp cấu hình dữ liệu" trên UI client Agent Day 09.
- Chạy lại pipeline chuẩn: `python etl_pipeline.py run` (Bỏ cờ bypass) để ghi đè, clean và upsert Index Vector sạch 100%.

---

## 5. Prevention (Ngăn chặn)
- Thiết lập module Expectation Suite (hoặc tích hợp thêm Great Expectations) ở Class **Halt** mặc định, nghiêm cấm lập trình viên đặt `--skip-validate` trên hệ thống Production.
- Đồng bộ SLA với Data Owner về chu kì đổ dữ liệu `exported_at` để Freshness không bị báo động giả mạo. Gắn thêm cảnh báo (Slack Monitor Alert) vào Pipeline Exit Status != 0.
