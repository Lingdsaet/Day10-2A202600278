# Báo cáo cá nhân - Phan Hoài Linh

**Vai trò chính:** Toàn bộ phận (Ingestion, Cleaning/Quality, Embed, Monitoring)

## 1. Phần phụ trách cụ thể
Vì thực hiện dự án một mình, tôi đảm nhận toàn bộ các tác vụ của Pipeline Data Observability:
- **Ingestion & Storage**: Định cấu hình hàm đọc `load_raw_csv` bắt lỗi byte BOM UTF-8 và thiết lập lưu trữ ID.
- **Cleaning & Analytics**: Phân loại và viết 3 Rules làm sạch mới (`draft_content`, `chunk_too_short`, `future_exported_at`); viết 2 Expectation Halt cho chất lượng.
- **Embed & Vector Index**: Xử lý logic Idempotent để đẩy chunk data lên ChromaDB không bị duplicates; Code chức năng Prune các dư lượng Vector cũ nằm ngoài danh sách Clean.
- **Monitor**: Cấu hình cơ chế check độ trễ (`freshness_check`), báo cáo log metadata qua manifest. Code luôn phiên bản nâng cấp Bonus: đo lường Freshness SLA qua 2 biên (nguồn export đến khi ETL chạy `ingest_to_publish_lag`, và từ lúc ETL đẩy lên Vector cho đến hiện tại `publish_age_hours`).

## 2. Quyết định kỹ thuật
Một quyết định quan trọng của tôi là thiết lập Severity Level cho việc Validate Data. Tôi chọn cấp độ **HALT** cho tất cả các Exception mới chèn vào (thay vì WARN). Vì đối với môi trường LLM Agent kết nối với cấu trúc Retrieval Day 09, dữ liệu có độ lệch như "14 ngày làm việc" (sai Policy) hoặc "Bản Draft nháp" gây hậu quả nghiêm trọng khi Agent trả lời sai với người thực. Thà đường ống ETL Halt và chờ người vận hành kiểm tra, còn hơn tự động nhét rác vào RAG.

## 3. Sự cố / Anomaly phát hiện & fix
Trong lúc thử nghiệm Expectation `unique_doc_id_effective_date_pair`, tôi nhận thấy hệ thống liên tục trả về Failed do cùng 1 cặp `doc_id` và `effective_date` có quá nhiều chunk trùng lặp về ngữ nghĩa hoặc bị lọt lưới. 
**Cách Fix**: Tôi đã kích hoạt và bổ sung bộ lọc HashSet Duplicate Filter nội suy bên trong vòng lặp `clean_rows` (`transform/cleaning_rules.py`). Nó tự động nhận diện Duplicate content để quarantine các bản sao con sinh ra sai lầm. Nhờ đó, Vector Index chỉ bao gồm dữ liệu độc nhất (100% Unique Contexts).

## 4. Evidence (Before / After)
- **Trước khi fix (Inject Bypass)**: Khi cố tình bỏ qua check (`--no-refund-fix`), Evaluation bằng script cho thấy thuật toán Semantic Search đọc nhầm Policy lỗi, trả về Context Rác: `contains_expected: no`, `hits_forbidden: yes`. Đồng thời E3 Expectation báo lỗi Violation=1.
- **Sau khi fix (Run Chuẩn)**: Pipeline filter 14 ngày làm việc và định hình lại bản ghi, Chroma DB upsert đúng Data, thuật toán Semantic Search trả đúng kết quả sạch: `contains_expected: yes`, `hits_forbidden: no`. E3 Expectation Pass.

## 5. Cải tiến (Action in 2h)
Trọng tâm cải tiến của tôi trong thời gian 2 giờ kế tiếp sẽ là:
- Loại bỏ Validation Assert chay bằng Python và thay bằng `Pydantic` Data Models hoặc `Great Expectations` SDK. Điều này giúp tôi thiết lập Type Checking mạnh tay hơn ở khâu Schema Validation ngay tại Ingestion thay vì chờ Cleaned Rows Output.
- Xây dựng Slack Bot Alert: Khi module Monitoring gặp Check `fresness` văng FAIL hoặc Halt, Push ngay Message báo cáo lỗi đến kênh IT.
