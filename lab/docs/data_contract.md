# Data contract — Lab Day 10

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_export_dirty.csv` | File CSV tĩnh tại `data/raw/` | Corrupt file, sai định dạng schema header, thiếu trường bắt buộc | File không tìm thấy, File Length = 0 |
| Fake DB API (Tương lai) | REST Pull | Network timeout, API credentials hết hạn | API Throttling/Connection Error |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash id nhằm mục tiêu Idempotent |
| doc_id | string | Có | Phải nằm trong allow list |
| chunk_text | string | Có | Nội dung đoạn > 10 chars |
| effective_date | date | Có | Quy về chuẩn YYYY-MM-DD ISO |
| exported_at | datetime | Có | RFC3339 UTC kết thúc với Z |

---

## 3. Quy tắc quarantine vs drop

- Mọi Record không qua được **Cleaning Rules** sẽ bị đưa vào `quarantine` list thay vì bị drop/bới bỏ vĩnh viễn (Phòng chống thất thoát dữ liệu). 
- Các báo cáo csv Quarantine này được lưu theo `run_id` vào `artifacts/quarantine/`.
- Khi cần rà soát lại, Quality Lead sẽ kiểm tra Quarantine Data. Nếu đó là False Positive, Lead sẽ cập nhật lại rules trong `transform/cleaning_rules.py` để Merge lại.

---

## 4. Phiên bản & canonical

- Tài liệu Source of Truth cho chính sách quy định (policy refund): file `policy_refund_v4` với rule sửa "14 ngày" về "7 ngày" và đánh dấu đuôi `[cleaned...]`. 
- HR Leave: Source of truth là bản `hr_leave_policy` có thời gian `effective_date` >="2026-01-01" (quy định 12 ngày phép năm). Bản 2025 bị gỡ và cách ly.
