Dưới đây là phiên bản **Markdown** được chuyển đổi từ file PDF của bạn, đã được format lại rõ ràng để AI agent hoặc hệ thống khác có thể đọc dễ dàng:

---

# BÁO CÁO PHÂN TÍCH DATASET CHẤT LƯỢNG KHÔNG KHÍ TP.HCM

## I. Tiêu chí và Chi tiết

| Tiêu chí  | Chi tiết                                                                                           |
| --------- | -------------------------------------------------------------------------------------------------- |
| Tên       | The HealthyAir Dataset: Outdoor Air Quality in Ho Chi Minh City                                    |
| Link tải  | [https://data.mendeley.com/datasets/pk6tzrjks8/1](https://data.mendeley.com/datasets/pk6tzrjks8/1) |
| Số dòng   | 52,549 bản ghi (sau làm sạch còn 32,510 bản ghi)                                                   |
| Số biến   | 9 biến (PM2.5, TSP, SO₂, O₃, NO₂, CO, Nhiệt độ, Độ ẩm, Trạm đo)                                    |
| Tần suất  | Theo giờ (hourly)                                                                                  |
| Thời gian | 02/2021 – 06/2022                                                                                  |
| Địa điểm  | TP.HCM – 6 trạm quan trắc                                                                          |
| Định dạng | CSV                                                                                                |

---

## II. Cấu trúc biến và ý nghĩa

* **date**: Ngày và giờ ghi nhận dữ liệu
* **Station_No**: Định danh trạm đo (1 → 6)
* **TSP, PM2.5**: Nồng độ bụi (µg/m³)
* **SO₂, O₃, NO₂, CO**: Nồng độ khí ô nhiễm (µg/m³ hoặc ppb)
* **Temperature**: Nhiệt độ (°C)
* **Humidity**: Độ ẩm (%)

---

## III. Nguồn và độ tin cậy

Dataset được thu thập từ **Mạng lưới quan trắc chất lượng không khí (AQMN)** với 6 trạm tại TP.HCM (giao thông, dân cư, công nghiệp).

* Dữ liệu ghi theo phút → tổng hợp theo giờ
* Bao gồm: PM2.5, TSP, NO₂, SO₂, O₃, CO, nhiệt độ, độ ẩm

### Tài liệu khoa học liên quan

* PubMed: [https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/)
* ScienceDirect: [https://www.sciencedirect.com/science/article/pii/S2352340922009775](https://www.sciencedirect.com/science/article/pii/S2352340922009775)
* DOI: 10.1016/j.uclim.2022.101315

### Ứng dụng

Dataset đã được sử dụng trong nghiên cứu:

> *AI-based Air Quality PM2.5 Forecasting Models for Developing Countries: A Case Study of Ho Chi Minh City, Vietnam*

---

## IV. Mục tiêu phân tích

### 1. Phân tích xu hướng ô nhiễm theo thời gian

* **Dữ liệu**: date, PM2.5, CO, NO₂
* **Lý do**: Ô nhiễm biến động theo giờ (giờ cao điểm) và mùa
* **Giá trị**: Xác định thời điểm ô nhiễm cao → hỗ trợ sinh hoạt

---

### 2. Phân bố ô nhiễm theo khu vực

* **Dữ liệu**: Station_No, PM2.5, TSP, CO
* **Lý do**: Ô nhiễm mang tính cục bộ theo vị trí
* **Giá trị**: Xác định khu vực ô nhiễm cao → phân tích không gian

---

### 3. Ảnh hưởng của thời tiết

* **Dữ liệu**: Temperature, Humidity, PM2.5, O₃
* **Lý do**:

  * Nhiệt độ cao → tăng O₃
  * Độ ẩm/mưa → giảm PM2.5
* **Giá trị**: Hiểu cơ chế ô nhiễm và tương quan biến

---

### 4. Tương quan giữa các chất ô nhiễm

* **Dữ liệu**: CO, NO₂, SO₂, PM2.5
* **Lý do**: CO & NO₂ chủ yếu từ giao thông
* **Giá trị**: Xác định nguồn gây ô nhiễm (giao thông vs công nghiệp)

---

### 5. Dự báo PM2.5

* **Dữ liệu**: Tất cả biến (features), PM2.5 (target)
* **Lý do**: PM2.5 ảnh hưởng trực tiếp sức khỏe
* **Giá trị**:

  * Cảnh báo sớm ô nhiễm
  * Tăng tính ứng dụng của hệ thống

