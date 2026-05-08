# **BÁO CÁO PHÂN TÍCH DATASET CHẤT LƯỢNG KHÔNG KHÍ TP.HCM**

## I.  Cấu trúc biến và ý nghĩa

| **Tiêu chí**   | **Chi tiết**                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| **Tên**         | **The HelthyAir Dataset: Outdoor Air Quality in Ho Chi Minh City**                        |
| **Link tải**    | [https://data.mendeley.com/datasets/pk6tzrjks8/1](https://data.mendeley.com/datasets/pk6tzrjks8/1) |
| **Số dòng**    | **52,549 bản ghi (sau làm sạch còn 32,510 bản ghi)**                                 |
| **Số biến**    | **9 biến (PM2.5, TSP, SO, O, NO, CO, Nhiệt độ, Độ ẩm, Trạm đo)**                 |
| **Tần suất**   | **Theo giờ (hourly)**                                                                    |
| **Thời gian**   | **2/2021-6/2022**                                                                         |
| **Địa điểm** | **TP.HCM – 6 trạm quan trắc**                                                          |
| **Định dạng** | **CSV**                                                                                   |

## II. Cấu trúc biến và ý nghĩa

* **date** : Ngày và giờ ghi nhận dữ liệu.
* **Station_No** : Định danh trạm đo quan trắc (từ 1 đến 6).
* **TSP, PM2.5** : Nồng độ tổng bụi lơ lửng và bụi mịn PM2.5 (đơn vị: **$\mu g/m^{3}$**).
* **SO2, O3, NO2, CO** : Nồng độ các khí thải gây ô nhiễm (đơn vị: **$\mu g/m^{3}$** hoặc ppb).
* **Temperature** : Nhiệt độ môi trường (°C).
* **Humidity** : Độ ẩm không khí (%).

## III. Nguồn và độ tin cậy

**Chuỗi minh chứng độ tin cậy đầy đủ**

Dataset này được thu thập từ Mạng lưới quan trắc chất lượng không khí thời gian thực (AQMN) gồm 6 trạm đặt tại các khu vực giao thông, dân cư và công nghiệp tại TP.HCM. Mỗi trạm đo PM2.5, TSP, NO, SO, O, CO và hai thông số khí tượng là nhiệt độ và độ ẩm.  Dữ liệu được ghi theo tần suất phút, sau đó tổng hợp theo giờ để phân tích và mô hình hóa. **PubMed Central**

**Bài báo khoa học đính kèm (peer-reviewed):**

* **PubMed/PMC:**[https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/)
* **ScienceDirect:**[https://www.sciencedirect.com/science/article/pii/S2352340922009775](https://www.sciencedirect.com/science/article/pii/S2352340922009775)
* **DOI bài báo gốc Al forecasting: 10.1016/j.uclim.2022.101315**

Dữ liệu PM2.5 từ dataset này đã được sử dụng để xây dựng mô hình dự báo PM2.5 theo giờ, công bố trong bài báo "Al-based Air Quality PM2.5 Forecasting Models for Developing Countries: A Case Study of Ho Chi Minh City, Vietnam". **PubMed**

## IV. Mục tiêu phân tích

**Mục tiêu 1: Phân tích xu hướng ô nhiễm theo thời gian**

* **Số liệu dùng**: date, PM2.5, CO, NO2
* **Lý do chọn**: Mức độ ô nhiễm thay đổi rõ rệt theo chu kỳ: biến động trong ngày (giờ cao điểm giao thông) và biến động trong năm (mùa mưa/mùa khô).
* **Giá trị mang lại**: Người dùng nắm được khung giờ hoặc tháng nào chất lượng không khí suy giảm nhất, từ đó giúp người dân có kế hoạch sinh hoạt và ra đường hợp lý.

**Mục tiêu 2: Đánh giá sự phân bố ô nhiễm giữa các khu vực**

* **Số liệu dùng**: Station_No, PM2.5, TSP, CO
* **Lý do chọn**: Ô nhiễm mang tính cục bộ. Tùy thuộc vào vị trí trạm đo (gần quốc lộ, khu công nghiệp hay khu dân cư) mà mức độ ô nhiễm sẽ khác nhau.
* **Giá trị mang lại**: Khoanh vùng cảnh báo các khu vực có chất lượng không khí kém thường xuyên tại TP.HCM, hỗ trợ phân tích không gian (spatial analysis).

**Mục tiêu 3: Tác động của yếu tố thời tiết đến nồng độ ô nhiễm**

* **Số liệu dùng**: Temperature, Humidity, PM2.5, 03
* **Lý do chọn**: Khí hậu ảnh hưởng rất mạnh đến ô nhiễm. Nhiệt độ cao làm 03 tăng nhanh do phản ứng quang hóa, mưa và độ ẩm giúp khuếch tán bụi PM2.5.
* **Giá trị mang lại**: Hiểu rõ cơ chế hình thành ô nhiễm và tương quan nghịch/thuận của các biến, bổ sung một insight khoa học và thực tế cho dashboard.

**Mục tiêu 4: Tương quan nội bộ giữa các chất ô nhiễm**

* **Số liệu dùng**: CO, NO2, SO2, PM2.5
* **Lý do chọn**: Tại TP.HCM, CO và NO2 chủ yếu sinh ra từ khói xe cộ. So sánh sự đồng biến giữa chúng giúp kiểm chứng nguồn phát thải chính.
* **Giá trị mang lại**: Cung cấp góc nhìn định lượng về nguyên nhân cốt lõi gây ô nhiễm (vd: giao thông so với công nghiệp).

**Mục tiêu 5: Phân tích Rủi ro Sức khỏe và Đặc tính Nguồn phát Bụi**

* **Số liệu dùng:** `PM2.5`, `TSP` (Tạo thêm biến phái sinh: Tỷ lệ `PM2.5/TSP`), `Station_No`, `Date`.
* **Lý do chọn:** Đánh giá mức độ độc hại thực tế của môi trường bằng cách đối chiếu tần suất nồng độ PM2.5 vượt ngưỡng an toàn của WHO (15 µg/m³). Sử dụng tỷ lệ `PM2.5/TSP` làm chỉ báo để nhận diện bản chất ô nhiễm.
* **Giá trị mang lại:** Cung cấp bức tranh định lượng về tỷ lệ thời gian người dân phải tiếp xúc với không khí nguy hại. Đồng thời, việc nhận diện đúng đặc tính ô nhiễm tại từng khu vực sẽ là cơ sở khoa học để đề xuất các giải pháp kiểm soát phát thải và quy hoạch đô thị sát với thực tiễn.
