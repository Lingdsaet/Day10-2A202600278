# Quality report — Lab Day 10 (nhóm)

**run_id:** 2026-04-15T08-57Z (run fix) / 2026-04-15T08-53Z (run inject)
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Inject) | Sau (Fix) | Ghi chú |
|--------|----------------|-----------|---------|
| raw_records | 13 | 13 | File có corrupt duplicate chunk + 14 days rule |
| cleaned_records | 5 | 4 | Fix loại bỏ chunk 14 days bằng quarantine sau khi được clean trùng |
| quarantine_records | 8 | 9 | Ở run sau (khi fix), đã áp dụng các rule chuẩn |
| Expectation halt? | Có (FAIL: refund_no_stale_14d_window, unique_doc_id_effective_date_pair) | Không (PASS Toàn Bộ) | Ở run trước, ta phải dùng flag `--skip-validate` để ép qua |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm hoặc dẫn link tới `artifacts/eval/before_fix.csv` và `artifacts/eval/after_fix.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Inject Bad Data):** 
`q_refund_window,Khách hàng có... kề từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 14 ngày làm việc... kể từ xác nhận đơn...,contains_expected: no,hits_forbidden: yes,,3`
**Sau (Đã Fix):**
`q_refund_window,Khách hàng có... kể từ khi xác nhận đơn?,policy_refund_v4,...,contains_expected: yes,hits_forbidden: no,,3`

**Văn bản chứng minh:** Trước khi fix, đoạn pipeline tải lên bản chunk "14 ngày làm việc" mà không sửa đổi dẫn tới retrieval bị dính cấm (`hits_forbidden`=yes, `contains_expected`=no). Sau khi áp dụng fix, đoạn text chứa "14" tự động được làm sạch thành "7 ngày làm việc", gỡ được hit forbidden và model đọc lấy được "7 ngày" đúng như đáp án mong chờ.

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước:** `contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes`
**Sau:** `contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes` (Chunk HR Version 2025 bị quarantine hiệu quả nhờ Rule 3 (ngay cả trên raw input xấu) hạn chế xung đột phiên bản nghỉ phép).

---

## 3. Freshness & monitor

Kết quả `freshness_check`: **FAIL**
Trong log: `{"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.969, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`
**Giải thích SLA**: Khai báo SLA là 24 giờ. Vì chúng ta dùng dữ liệu tĩnh của bài hướng dẫn (từng được xuất ngày `2026-04-10T08:00:00Z`), độ trễ vượt qua hạn mức quy định (120 giờ) cho nên log báo FAIL. Đây là điều bình thường vì theo ngữ cảnh snapshot tĩnh thì không tránh khỏi cảnh báo này, nếu áp dụng trên thực tế thì manifest sẽ PASS dựa theo thời gian xuất CSV hàng ngày.

---

## 4. Corruption inject (Sprint 3)

Mô tả cố ý làm hỏng dữ liệu: 
Nhóm đã sửa file `policy_export_dirty.csv` để đưa thông tin "14 ngày làm việc" vào các dòng 1 và 2 (thuộc `policy_refund_v4`), và loại bỏ nhãn "lỗi migration" khỏi dòng 3 để nó đánh lừa Rule 1.  
Khi chạy `python etl_pipeline.py run --no-refund-fix --skip-validate`, các dòng có thông tin sai lệch "14 ngày" rò rỉ vào Data Platform vì hệ thống bypass việc kiểm duyệt lỗi (dù E3 và E8 báo FAIL).
Trong lần chạy chính thức (Bỏ qua flag no-refund-fix), hệ thống tự động Fix window về 7 ngày, sau đó deduplicate (thay vì lọt lưới 2 chunks vào index). Do đó sau run chuẩn (Fix), model clean hoạt động ổn định và query được đáp số "7 ngày".  

---

## 5. Hạn chế & việc chưa làm

- Cần tích hợp Great Expectations thay cho class Python nội bộ để cung cấp báo cáo Data Quality hoàn chỉnh bằng GUI.
- ...
