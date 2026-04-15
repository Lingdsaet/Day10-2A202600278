# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Cá nhân (Phan Hoài Linh)  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Phan Hoài Linh | Toàn bộ (Ingest / Clean / Embed / Monitor) | phanlinhfbi@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** Lab Day 10 - antrepo  

---

> **Nộp tại:** `reports/group_report.md`  

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**
Pipeline đọc dữ liệu thô từ `data/raw/policy_export_dirty.csv`, tiến hành làm sạch tại module `transform/cleaning_rules.py` và chạy tập hợp kiểm thử Validation Suite (Expectations) trong `quality/expectations.py` để phát hiện lỗi từ các chunk. Sau khi dữ liệu thỏa mãn các Data Quality rules (exit code sạch), pipeline publish vào Chroma Database thông qua logic định danh `chunk_id` độc nhất. Nhờ cơ chế phân tích này, pipeline cho phép quá trình upsert hoạt động mang tính idempotent (cho dù rerun bao nhiêu lần thì Vector DB vẫn không bị phình). Mỗi run đều xuất ra log `run_id`, đếm record raw/quarantine, và ghi dấu manifest JSON. Nếu môi trường offline/không có GPU, pipeline đã thiết lập Fallback sử dụng mã băm hash tĩnh để thay thế cho Embeddings, đảm bảo lệnh vòng đời ETL chạy đến cùng (end-to-end).

**Lệnh chạy một dòng:**
`python etl_pipeline.py run`

---

## 2. Cleaning & expectation (150–200 từ)

### 2a. Bảng metric_impact

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule R4: `draft_content` (quarantine marker nháp/draft) | raw có 1 chunk draft sau khi inject | chunk draft bị quarantine (`quarantine_...csv`), cleaned còn ít hơn 1 bản ghi | log script hiện `quarantine_records` tăng thêm 1 |
| Rule R5: `chunk_too_short` (quarantine < 10 chars) | raw có 1 chunk "Ngắn" dưới 10 ký tự | chunk ngắn bị quarantine, tránh lọt vào store | log script hiện `quarantine_records` tăng |
| Rule R6: `future_exported_at` (quarantine tương lai) | raw có 1 chunk tương lai | chunk bị quarantine tương tự | log script hiện `quarantine_records` tăng |
| Expectation E9 mới: `no_draft_content` (halt) | FAIL nếu tắt R4 trên raw đã inject | PASS khi bật đầy đủ R4 trên run chuẩn `python etl_pipeline.py run` | log script đối chiếu pipeline execution |
| Expectation E10 mới: `exported_at_not_in_future` (halt) | FAIL nếu tắt R6 trên raw đã inject | PASS khi bật đầy đủ R6 | log pipeline execution |

**Rule chính (baseline + mở rộng):**
- Baseline: allowlist `doc_id`, chuẩn hoá `effective_date`, quarantine HR stale, dedupe, fix refund 14→7.
- Rule mở rộng: Cách ly marker lỗi version/migration cũ (policy-v3), xóa noise FAQ sync, chuẩn hóa date time ISO UTC (có đuôi Z). Loại rác Draft và rác kích thước ngắn.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**
Trước khi thiết lập chạy rule, `E3: refund_no_stale_14d_window` báo FAIL với violations=1 (Do tôi đã force chèn 1 dòng 14 ngày vào CSV và chạy kèm cờ bypass `no-refund-fix`). Để fix, chỉ cần tháo cờ bypass cho chương trình chạy chuẩn mực lại, rule sẽ override 14 về 7 ngày.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**
Nhóm đã cố tình chỉnh file input `data/raw/policy_export_dirty.csv` để chèn thêm quy định "14 ngày làm việc" mà không có dấu hiệu migration (để né Rule của baseline). Sau đó chạy Data Pipeline bằng command cố ý bypass: `python etl_pipeline.py run --no-refund-fix --skip-validate`. Do đó pipeline đẩy sai dữ liệu lên Embed.

**Kết quả định lượng (từ CSV / bảng):**
Kết quả thu được đo lường tại file `artifacts/eval/before_fix.csv` cho thấy câu hỏi `q_refund_window` đã Retrieval Dính vào chunk có nội dung xấu "14 ngày làm việc".
Do đó chỉ số evaluation ghi nhận xấu:
- `contains_expected: no`
- `hits_forbidden: yes`

Sau đó nhóm chạy lại lệnh Fix `python etl_pipeline.py run`. Rule đã làm sạch 14 ngày về 7 ngày, sau đó dedupe hoàn chỉnh.
Kết quả thu được từ `after_fix.csv`:
- `contains_expected: yes`
- `hits_forbidden: no`

Chứng minh cho thấy sau khi fix, RAG Agent không còn bị nhiễm độc Context và sẽ hoạt động tốt khi được truy vấn.

---

## 4. Freshness & monitoring (100–150 từ)

**Kết quả `freshness_check`**: Báo FAIL (Ví dụ: `{"age_hours": 120.969, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`).
**Giải thích SLA**: Nhóm cài đặt tham chiếu SLA của Data Pipeline độ trễ là 24 giờ. Lý do trạng thái trả về FAIL là vì dữ liệu tĩnh lấy từ template khoá học là dữ liệu xuất của ngày 10/04/2026. Ở thời điểm chạy bài tập là 15/04/2026, pipeline kiểm tra khoảng cách thời gian từ `exported_at` mới nhất và phát hiện nó đã già đi hơn 120 giờ. Điều này là đặc tính dự tính, nếu chạy Live Data mỗi ngày thì SLA Fail sẽ thật sự là một Alert cần cấp cứu gấp.

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu do Pipeline Transform ngày 10 này trực tiếp cung cấp collection vector cho ứng dụng RAG Multi Agent ở Day 09. Nhóm đã quyết định override tái sử dụng chung định dạng `day10_kb` để Agent kết nối vào đọc ngữ cảnh. Nhờ có khả năng Quarantine dữ liệu lạc hậu và nhiễu từ bộ lọc hôm nay, Agent Day 09 khi trả lời các câu hỏi về Ticket SLA hay Chính sách Hoàn tiền sẽ lấy được thông tin Canonical thay vì đọc nhầm phiên bản Policy lỗi thời.

---

## 6. Rủi ro còn lại & việc chưa làm

- Cần setup hệ thống orchestrator tự động như Airflow/Dagster để chạy pipeline hàng giờ.
- Viết CI Coverage cho Unit Test của Transformation Rules.

---

## Peer Review (3 Câu hỏi phần E Slide)
Theo yêu cầu peer review, nhóm ghi nhận như sau về các câu hỏi (Q1: Schema Validation vs Data Quality; Q2: Vì sao tách Clean và Embed; Q3: Khi nào cần human-in-the-loop):
1. Schema Validation giống như kiểm tra Format (vd String thay vì Int), còn Data Quality kiểm tra mặt logic ngữ nghĩa (vd Ngày sinh không được ở Tương Lai).
2. Tách Clean và Embed ra rạch ròi vì Embed cực kỳ tốn tài nguyên GPU và chi phí API, do đó chỉ đưa dữ liệu tối sạch, tối giản lên Embed để không nạp rác.
3. Cần thiết kế Human In The Loop khi model gặp phải dữ liệu Unclassified (Unknown Pattern/ Out of Schema) khiến Module Expectation không chắc chắn là nó thuộc diện Pass hay Fail. Quản trị viên Data Platform sẽ kiểm tra thủ công (Quarantine Review) và cho Merge.
