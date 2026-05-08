HƯỚNG DẪN TÍCH HỢP AI


Các nhóm sẽ được yêu cầu sử dụng module AI đã phát triển để trả lời các câu hỏi phân tích dựa trên dữ liệu của nhóm và các câu hỏi phân tích đã chuẩn bị sẵn, nhằm tránh lan man. Tuy nhiên, vẫn có thể được yêu cầu trả lời câu hỏi ngoài lề để đánh giá mức độ linh hoạt của AI. Lưu ý, số lượng câu hỏi tối thiểu bằng số lượng thành viên trong nhóm.

5 Gợi ý thiết kế

Phân chia cấu trúc API và Frontend.

5.1 Phần Giao diện & Tương tác người dùng (Frontend)

Công nghệ phát triển giao diện Frontend là dùng Streamlit

**Chức năng nhận yêu cầu:** Ví dụ: Một ô chat hoặc form nhập liệu để người dùng gửi yêu cầu phân tích/viết code cho AI.

**Chức năng xem & chỉnh sửa mã nguồn**.

**Chức năng phê duyệt**.

**Chức năng hiển thị kết quả**.

5.2 Phần API

**API AI (bắt buộc):**

* Tiếp nhận yêu cầu từ Front-end.
* Gửi kèm ngữ cảnh (ví dụ: cấu trúc dữ liệu hiện có) cho mô hình AI (Groq)
* Yêu cầu AI trả về cả code và giải thích tương ứng; hoặc kết quả trình bày.
* 

**API Thực thi (bắt buộc):**

* Tiếp nhận đoạn mã đã được con người “chỉnh sửa” và “phê duyệt” từ frontend.
* Thực hiện chạy code trực tiếp trên dữ liệu tại máy.
* Thu thập kết quả (ảnh biểu đồ, bảng dữ liệu, logs) để trả về cho frontend hiển thị.
* 

**API Logs (bắt buộc):**

* Lưu trữ tất cả các yêu cầu, mã nguồn, kết quả phân tích và giải thích.
