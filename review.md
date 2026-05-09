
# Báo Cáo Đánh Giá Code — Dashboard P03 (Phiên Bản Mới Nhất)

---

## TIÊU CHÍ 1 — Kiểm Tra Logic Ngưỡng WHO

### ✅ Đúng (2/6 chất)

| Chất | Ngưỡng code | WHO AQG 2021 24h | Kết luận                                                                          |
| ----- | ------------- | ---------------- | ----------------------------------------------------------------------------------- |
| PM2.5 | 15.0 µg/m³  | 15.0 µg/m³     | ✅ Chính xác                                                                      |
| SO2   | 40.0 µg/m³  | 40.0 µg/m³     | ✅ Chính xác (nhưng dữ liệu SO2 có anomaly nghiêm trọng — xem bên dưới) |

### ❌ Sai hoặc không có cơ sở (3/6 chất)

**O3 = 100 µg/m³ — Sai metric đầu vào:**
Ngưỡng 100 µg/m³ của WHO là chuẩn  **8-hour peak average** , không phải 24h mean. Code tính `df_daily = groupby([..., Date_only]).mean()` — tức là trung bình 24 giờ — rồi so sánh con số đó với 100. Đây là hai đại lượng khác nhau về định nghĩa. Kết quả: tỷ lệ vượt ngưỡng của Bình Tân (70.9% ngày) và Linh Trung (56.8% ngày) không thể diễn giải là "vượt chuẩn WHO" một cách hợp lệ.

**CO = 10,000 µg/m³ — Không khớp với bất kỳ chuẩn nào:**
WHO 24h CO = **4,000 µg/m³** (4 mg/m³). QCVN 05:2023 24h CO =  **30,000 µg/m³** . Con số 10,000 trong code không có nguồn gốc chuẩn rõ ràng. Hậu quả: toàn bộ 6 trạm đều hiển thị CO "an toàn" (max ~1,342 µg/m³ << 10,000), nhưng nếu dùng ngưỡng WHO thực (4,000) thì kết luận vẫn không đổi — CO thực tế rất thấp so với mọi chuẩn.

**TSP = 50 µg/m³ — Không có cơ sở WHO:**
WHO 2021 AQG không ban hành ngưỡng TSP 24h. QCVN 05:2023 quy định TSP 24h =  **150 µg/m³** . Code dùng 50 µg/m³ không tham chiếu được về nguồn chuẩn, dẫn đến 3 trạm (Thanh Đa, Linh Trung, KCN Tân Bình) bị đánh dấu "vượt ngưỡng" trên biểu đồ theo một mức không chính thức.

### ⚠️ Vấn đề phương pháp luận trong KPI4

KPI4 tính `n_exceed` từ `map_data` — là **median của daily means** theo trạm. Đây không phải định nghĩa chuẩn WHO (WHO áp dụng threshold cho từng ngày quan trắc 24h riêng lẻ). Cách đúng là đếm số ngày `daily_mean > threshold`, sau đó báo cáo tỷ lệ. Giá trị thực từ dữ liệu:

| Trạm            | PM2.5 — % ngày vượt WHO 15 µg/m³ |
| ---------------- | -------------------------------------- |
| Thanh Đa        | **90.7%**ngày                         |
| ĐHQG Linh Trung | 79.4% ngày                            |
| KCN Tân Bình   | 73.1% ngày                            |
| Bình Tân       | 66.2% ngày                            |
| Quận 10         | 65.4% ngày                            |
| Quận 3          | 47.3% ngày                            |

KPI4 hiện chỉ báo "5/6 trạm" mà không truyền đạt được mức độ nghiêm trọng (gần như 365 ngày vượt chuẩn tại Thanh Đa). Đây là thông tin quan trọng bị ẩn đi.

---

## TIÊU CHÍ 2 — Kiểm Tra Logic Các Chart

### Chart 1: Ranked Horizontal Bar — ✅ Logic Đúng

`sort_values(ascending=True)` với `orientation='h'` cho ra thanh thấp nhất ở trên cùng, cao nhất ở dưới cùng — đúng với quy ước đọc biểu đồ ngang. Màu đỏ highlight "Vượt ngưỡng" hoạt động đúng. Không có lỗi logic.

### Chart 2: Facet Bar (% WHO) — ⚠️ 2 vấn đề cần sửa

**Vấn đề 1 — Comment sai so với code:**
Dòng comment viết `# Tính mean cho từng chất` nhưng code thực tế dùng `df_r[p].median()`. Đây là median-of-daily-means, không phải mean. Cần thống nhất cả code lẫn label trên chart (hiện chart không ghi rõ là mean hay median).

**Vấn đề 2 — Pooling Region che khuất sự khác biệt nội vùng:**
Khu "Giao thông" gộp cả Bình Tân (PM2.5 median = 16.86) và Quận 3 (PM2.5 median = 14.33) thành một thanh duy nhất. Hai trạm này có profile khác nhau rõ rệt — Quận 3 là trạm duy nhất không vượt WHO về PM2.5, trong khi Bình Tân vượt 12%. Facet theo Region làm mất thông tin này. Đây là chart thể hiện `Profile theo Khu vực`, không phải `Profile theo Trạm`, nên cần ghi rõ trong title rằng các trạm cùng region đã được gộp.

**Vấn đề 3 — SO2 và NO2 làm nhiễu dominant_insight:**
`idxmax()` trả về SO2 tại Nền đô thị (679% WHO) vì dữ liệu SO2 toàn mạng có median 150–340 µg/m³ — gần như chắc chắn là lỗi đơn vị hoặc drift thiết bị. NO2 tại Quận 3 đạt 1,091% WHO do anomaly bimodal đã được cảnh báo trước đó. Kết quả là câu `dominant_insight` tự động in ra *"SO2 tại Nền đô thị chiếm tỷ trọng cao nhất"* — một kết luận hoàn toàn sai về mặt môi trường và xuất phát từ artifact dữ liệu, không phải thực tế.

### Chart 3: Box Plot — ✅ Logic Đúng, 1 Insight Sai

Input `df_daily` (daily means) là đúng cho box plot. Tuy nhiên `boxplot_insight` báo **KCN Tân Bình** có IQR lớn nhất (14.60 µg/m³) — đây là **đúng** theo dữ liệu. Code tính IQR trực tiếp từ `df_daily.groupby('Location').quantile()` — chính xác.

### Chart 4: Radar Chart — ✅ Logic Đúng, ⚠️ Cần Chú Thích

Logic hiển thị worst/best station theo `focus_pollutant` là đúng. Kỹ thuật **Cap & Annotate** (ép trục 200%, hiển thị text cảnh báo khi vượt) là giải pháp hợp lý cho vấn đề SO2/NO2 anomaly. Tuy nhiên:

Khi `focus_pollutant = PM2.5`: worst = Thanh Đa, best = Quận 3. Quận 3 có NO2 = 1,091% WHO và SO2 = 876% WHO (đều bị cap tại 200%). Người xem sẽ thấy Quận 3 có hình đa giác "nhỏ hơn" Thanh Đa — nhưng thực tế Quận 3 có hình radar cực kỳ bất thường do anomaly. Câu insight *"Quận 3 là trạm sạch nhất"* cần đi kèm disclaimer rõ ràng hơn là chỉ dùng `st.warning` ở đầu trang.

### Chart 5: Day/Night Dot Plot — ✅ Logic Đúng, 1 Insight Cần Cập Nhật

Logic phát hiện "Đêm > Ngày" và highlight bằng border đỏ là đúng. Dữ liệu thực xác nhận:

* **KCN Tân Bình** : Đêm (20.04) > Ngày (19.43) — PM2.5 cao hơn ban đêm
* **ĐHQG Linh Trung** : Đêm (20.70) > Ngày (19.53) — PM2.5 cao hơn ban đêm

Insight text cần đề cập cả hai trạm này. Tuy nhiên chênh lệch rất nhỏ (~0.6–1.2 µg/m³) — cần thêm lưu ý rằng sự khác biệt này có thể không có ý nghĩa thống kê và không nên diễn giải quá mức.

---

## TIÊU CHÍ 3 — Đề Xuất Insight Thuần Dữ Liệu

### Insight Facet Bar (thay thế dominant_insight hiện tại)

Loại SO2 và NO2 khỏi vòng tính dominant do anomaly. Với các chất còn lại:

> *"Nhìn trên hồ sơ % WHO (loại trừ SO2/NO2 do nghi vấn chất lượng đo lường): PM2.5 là chất chiếm tỷ trọng cao nhất tại khu Dân cư (162% WHO) và Công nghiệp (137% WHO). O3 là chất chiếm tỷ trọng cao nhất tại khu Giao thông (Bình Tân: 111% WHO). TSP vượt ngưỡng tham chiếu tại Dân cư (117%) và Nền đô thị (113%)."*

### Insight Box Plot (cập nhật)

> *"KCN Tân Bình có biên độ dao động PM2.5 ngày lớn nhất (IQR = 14.6 µg/m³), gấp 2.0 lần so với Quận 3 (IQR = 7.2 µg/m³). Thanh Đa tuy có median cao nhất (24.3 µg/m³) nhưng IQR nhỏ hơn KCN Tân Bình (13.6 vs 14.6) — cho thấy mức ô nhiễm tại Thanh Đa cao nhưng ổn định, trong khi KCN Tân Bình dao động mạnh hơn theo ngày, phù hợp với tính chất hoạt động công nghiệp không đều."*

### Insight Day/Night (cập nhật)

> *"KCN Tân Bình và ĐHQG Linh Trung là 2 trạm duy nhất trong mạng có PM2.5 trung vị ban đêm cao hơn ban ngày (chênh lệch lần lượt 0.6 và 1.2 µg/m³). Do chênh lệch nhỏ, cần thận trọng khi diễn giải. 4 trạm còn lại đều có nồng độ cao hơn ban ngày, nhất quán với nguồn phát thải giao thông tập trung vào giờ cao điểm."*

---

## TIÊU CHÍ 4 — Kết Luận Tổng Thể (Thuần Dữ Liệu)

> **Không gian ô nhiễm tại TPHCM có sự phân hóa rõ rệt theo đặc trưng khu vực, nhưng không theo chiều hướng thông thường:**
>
> **PM2.5 và TSP:** Khu Dân cư (Thanh Đa) — không phải Giao thông hay Công nghiệp — dẫn đầu về nồng độ bụi mịn toàn mạng, với median PM2.5 = 24.3 µg/m³ (162% WHO) và 90.7% số ngày vượt chuẩn 24h. KCN Tân Bình đứng thứ hai (20.6 µg/m³, 73.1% ngày). Trạm Giao thông ở Quận 3 là trạm duy nhất không vượt WHO PM2.5 (47.3% ngày, median = 14.3 µg/m³).
>
> **O3:** Phân bố không gian ngược chiều với PM2.5. Bình Tân (Giao thông) có O3 cao nhất (median 110.8 µg/m³, 70.9% ngày vượt 100 µg/m³), trong khi KCN Tân Bình có O3 thấp nhất (77.4 µg/m³, chỉ 5.9% ngày). Điều này cho thấy hai nhóm chất ô nhiễm có nguồn gốc và cơ chế sinh ra khác nhau theo không gian.
>
> **NO2 và SO2:** Dữ liệu tại Quận 3 và toàn mạng SO2 có dấu hiệu bất thường nghiêm trọng (NO2 Quận 3 median = 272.7 µg/m³, SO2 toàn mạng median 150–340 µg/m³). Không thể đưa ra kết luận không gian đáng tin cậy cho hai chất này từ dataset hiện tại.
>
> **Hàm ý chính sách (từ dữ liệu):** Nếu PM2.5 là ưu tiên can thiệp, Thanh Đa cần được xem xét trước, không phải các khu giao thông. Nếu O3 là ưu tiên, trọng tâm là Bình Tân và Linh Trung. Không có một chiến lược đồng nhất nào phù hợp với cả sáu trạm đồng thời — điều này được xác nhận bởi dữ liệu, không phải giả định.

---

## Tóm Tắt Ma Trận Đánh Giá

| Hạng mục                               | Trạng thái                                         | Ưu tiên sửa                          |
| ---------------------------------------- | ---------------------------------------------------- | --------------------------------------- |
| PM2.5 threshold (15)                     | ✅ Đúng                                            | —                                      |
| NO2 threshold (25)                       | ✅ Đúng                                            | —                                      |
| SO2 threshold (40)                       | ✅ Đúng nhưng data anomaly                        | Thêm disclaimer mạnh hơn             |
| O3 threshold — sai metric               | ❌ 24h mean ≠ 8h peak                               | 🔴 Sửa ngay                            |
| TSP threshold — không có chuẩn       | ❌ 50 µg/m³ không có nguồn                      | 🔴 Ghi rõ nguồn hoặc đổi sang QCVN |
| CO threshold — không khớp chuẩn nào | ❌                                                   | 🟠 Làm rõ nguồn                      |
| Chart 1 (Ranked Bar)                     | ✅ Logic đúng                                      | —                                      |
| Chart 2 (Facet % WHO)                    | ⚠️ Pooling + comment sai + dominant bị SO2 chiếm | 🔴 Sửa insight                         |
| Chart 3 (Box Plot)                       | ✅ Logic đúng                                      | —                                      |
| Chart 4 (Radar)                          | ✅ Đúng, cần disclaimer rõ hơn                  | 🟡 Cải thiện                          |
| Chart 5 (Day/Night)                      | ✅ Logic đúng, insight cần cập nhật             | 🟡 Cập nhật text                      |
| KPI4 exceedance                          | ⚠️ Median-of-stations thay vì % ngày vượt      | 🟠 Đề xuất bổ sung metric           |
