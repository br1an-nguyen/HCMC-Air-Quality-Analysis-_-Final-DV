1. Thiết kế Nút kích hoạt (The Launcher / Chat Head)

Đây là điểm chạm đầu tiên của người dùng, nằm cố định (`position: fixed`) ở góc màn hình (thường là góc dưới bên phải).

- **Avatar-based Icon:** Thay vì dùng icon bong bóng chat truyền thống, hãy sử dụng hình ảnh đại diện (avatar) của bot (như chú gấu Ice Bear trong ảnh). Viền avatar có thể thêm một lớp stroke mỏng hoặc shadow để nổi bật trên mọi nền website.
- **Notification Badge (Chấm thông báo):** Đặt ở góc trên bên phải (top-right) của avatar bằng `position: absolute`. Chấm đỏ nổi bật chứa số lượng tin nhắn chưa đọc (hoặc kết quả code/biểu đồ vừa chạy xong) để thu hút sự chú ý.

### 2. Thiết kế Cửa sổ Chat (The Chat Panel)

Khi người dùng click vào Chat Head, một cửa sổ giao diện sẽ mở ra. Đối với widget, dạng **Popover** là phù hợp nhất.

- **Cấu trúc Card / Popover:** Khung chat nổi lên ngay phía trên icon kích hoạt. Bo góc mềm mại (VD: `rounded-xl` hoặc `rounded-2xl` trong Tailwind CSS) và đổ bóng (`box-shadow`) đủ sâu để tạo cảm giác cửa sổ đang nằm trên một layer hoàn toàn khác so với trang web.
- **Header (Phần đầu):**
  - Hiển thị lại Avatar, tên Chatbot và trạng thái hoạt động (chấm xanh lá cây thể hiện Online).
  - Cụm nút điều khiển ở góc phải: Thu nhỏ (Minimize - gom lại thành Chat Head) và Đóng (Close).
- **Message Area (Khu vực tin nhắn):**
  - **Bubble Style:** Tin nhắn của người dùng nằm bên phải, nền màu nổi (ví dụ: Xanh dương hoặc màu brand của bạn). Tin nhắn của bot nằm bên trái, nền xám nhạt để dễ phân biệt.
  - **Rich Content:** Vì chatbot của bạn có thể trả về code hoặc biểu đồ, cần thiết kế sẵn các block hiển thị đặc biệt cho đoạn mã (có nút Copy) và khung chứa hình ảnh/biểu đồ (dễ dàng zoom hoặc xem chi tiết). Hỗ trợ popup lên một cửa sổ zoom trong trường hợp người dùng bấm vào xem các chart được tạo trong đoạn chat.
  - **Interactive Cards:** Tích hợp trực tiếp các nút duyệt (Approve/Reject) ngay trong bong bóng chat của bot để hoàn thiện luồng duyệt thực thi mã.
- **Input Area (Khu vực nhập liệu):** Nằm dưới cùng, bao gồm ô text-input có khả năng tự động mở rộng chiều cao (auto-resize textarea) khi gõ văn bản dài, nút đính kèm tệp và nút Gửi (Send).

### 3. Tương tác và Hiệu ứng (Interactions & Animations)

Để tạo cảm giác mượt mà giống Messenger, phần UX/Animation rất quan trọng:

- **Mở/Đóng Popover:** Khi click, cửa sổ chat không nên hiện ra ngay lập tức mà nên có hiệu ứng `scale` (phóng to từ vị trí icon lên) kết hợp `fade-in`. Khi đóng lại thì thu nhỏ dần về phía icon.
- **Trạng thái "Đang gõ" (Typing Indicator):** Sử dụng animation 3 dấu chấm nhảy múa quen thuộc để báo hiệu AI đang xử lý hoặc đang sinh code, giúp người dùng kiên nhẫn chờ đợi.
