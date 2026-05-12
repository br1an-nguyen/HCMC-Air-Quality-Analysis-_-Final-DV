# HCMC Air Quality Analysis & Chatbot Dashboard

Dự án phân tích chất lượng không khí tại TP.HCM kết hợp Chatbot AI hỗ trợ truy vấn dữ liệu thông minh. Hệ thống bao gồm một Dashboard trực quan hóa dữ liệu và một Backend API tích hợp Gemini AI.

---

## 🛠 Yêu cầu hệ thống

- **Python**: Phiên bản 3.10 trở lên.
- **API Key**: Cần có `GOOGLE_API_KEY` để sử dụng tính năng Chatbot AI (Gemini).

## 🚀 Hướng dẫn cài đặt

### 1. Tải dự án và tạo môi trường ảo

```bash
# Di chuyển vào thư mục dự án
cd HCMC-Air-Quality-Analysis-_-Final-DV

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo (Windows)
.\venv\Scripts\activate

# Kích hoạt môi trường ảo (Linux/Mac)
source venv/bin/activate
```

### 2. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường

Tạo file `.env` tại thư mục gốc của dự án và thêm khóa API của bạn:

```env
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-1.5-flash
# Cấu hình URL nếu chạy trên môi trường khác localhost
# BACKEND_URL=http://localhost:80
# FRONTEND_URL=http://localhost:8501
```

---

## 🖥 Hướng dẫn khởi chạy

Để hệ thống hoạt động đầy đủ tính năng, bạn cần chạy đồng thời cả **Backend** và **Dashboard**.

### Bước 1: Khởi chạy Backend (API Chatbot)

Mở một terminal mới và chạy lệnh:

```bash
# Chạy với uvicorn từ thư mục gốc
uvicorn backend.main:app --host 0.0.0.0 --port 80
```

_Lưu ý: Nếu port 80 đã bị chiếm, bạn có thể đổi port và cập nhật biến `BACKEND_URL` trong file `.env`._

### Bước 2: Khởi chạy Dashboard (Streamlit)

Mở một terminal khác và chạy lệnh:

```bash
streamlit run app.py
```

Hệ thống sẽ tự động mở Dashboard trên trình duyệt tại địa chỉ `http://localhost:8501`.

---

## 📂 Cấu trúc dự án

- `app.py`: Entry point chính của Dashboard Streamlit.
- `dashboard/`: Chứa các trang phân tích chi tiết (Goal 1 - 5) và các component giao diện.
- `backend/`: Chứa mã nguồn FastAPI, logic xử lý AI và cơ sở dữ liệu.
  - `ai_logs.db`: Tệp cơ sở dữ liệu SQLite (được tự động khởi tạo khi chạy backend).
- `data/`: Chứa các tệp dữ liệu chất lượng không khí đã qua xử lý.
- `requirements.txt`: Danh sách các thư viện Python cần thiết.

---

## 📋 Cơ sở dữ liệu

Dự án sử dụng **SQLite**, một hệ quản trị cơ sở dữ liệu dạng tệp nhẹ nhàng:

- Không cần cài đặt server database riêng biệt.
- Khi bạn chạy lệnh khởi chạy Backend, hệ thống sẽ tự động tạo tệp `backend/ai_logs.db` và thiết lập các bảng cần thiết nếu chúng chưa tồn tại.

---

## 📝 Ghi chú

- Nếu bạn sử dụng **Dev Container** trong VS Code, hệ thống sẽ tự động cài đặt và khởi chạy các thành phần cần thiết.
- Đảm bảo Backend đã chạy trước khi sử dụng tính năng Chatbot trên Dashboard.
