# Dashboard Design Format - HCMC Air Quality (Re-designed from Notebook v2)

Tài liệu này được thiết kế lại dựa trên notebook mới `clean_and_explore_data.ipynb` và là chuẩn duy nhất cho toàn nhóm khi làm dashboard.
Mục tiêu: thống nhất thiết kế, thống nhất logic dữ liệu, tránh overlap khi nhiều người làm song song.

## 1. Dữ liệu chuẩn được phép dùng

Nguồn dữ liệu cho dashboard phải là file sạch đã export ở cuối pipeline:

- `../data/cleaned/Air_Quality_HCMC_Cleaned.csv`

Schema chuẩn đang dùng để vẽ dashboard:

- Time: `Date`, `Hour`
- Dimension: `Station_No`
- Metrics: `TSP`, `PM2.5`, `O3`, `CO`, `NO2`, `SO2`, `Temperature`, `Humidity`

Quy tắc bắt buộc:

- Không dùng lại cột `date` gốc trong dashboard.
- Không tự tạo lại logic làm sạch khác notebook nếu chưa thống nhất nhóm.
- Mọi biểu đồ phải bám schema trên.

## 2. Data assumptions cần ghi chú trên dashboard

Các giả định quan trọng từ notebook phải được phản ánh trong phần note/phụ lục:

1. Missing data của biến số được nội suy theo thời gian trong từng `Station_No`.
2. Outlier được giữ lại vì có thể là sự kiện môi trường thật.
3. Trường hợp `PM2.5 > TSP` được xử lý bằng nội suy tỷ lệ dựa trên các trạm bình thường.
4. `Station_No` là kiểu phân loại (categorical), không phải giá trị liên tục.

Mẫu disclaimer ngắn (đặt ở trang Method):

- `Dữ liệu đã được xử lý missing theo time interpolation theo từng trạm; giữ outlier; hiệu chỉnh bất nhất PM2.5 > TSP theo tỷ lệ PM2.5/TSP tham chiếu.`

## 3. Mục tiêu dashboard (business questions)

Dashboard phải trả lời rõ 5 câu hỏi sau:

1. Xu hướng ô nhiễm theo ngày/giờ biến động thế nào?
2. Trạm nào có mức ô nhiễm cao hơn các trạm còn lại?
3. Nhiệt độ và độ ẩm liên quan thế nào đến PM2.5/O3?
4. Mối tương quan giữa các chất ô nhiễm là gì?
5. Những khung giờ/range thời gian nào cần cảnh báo ưu tiên?

## 4. Visual identity (màu, chữ, bố cục)

## 4.1 Theme cơ bản

- Canvas background: `#F4F7FB`
- Card background: `#FFFFFF`
- Border: `#D8E1EB`
- Text chính: `#102A43`
- Text phụ: `#486581`
- Gridline: `#E6EDF4`

## 4.2 Color mapping cố định theo biến

- PM2.5: `#C0392B`
- TSP: `#7F1D1D`
- O3: `#1B9E77`
- CO: `#5E548E`
- NO2: `#F39C12`
- SO2: `#2E86AB`
- Temperature: `#E76F51`
- Humidity: `#3A86FF`

Quy tắc:

- Một biến chỉ có đúng một màu trong mọi page.
- Không dùng random palette theo chart.
- Khi highlight, chỉ dùng 1 màu nhấn `#FFB703`.

## 4.3 Typography

- Font: `Segoe UI` (fallback `Arial`)
- Dashboard title: 24-28 px
- Section title: 16-18 px
- Label/axis/legend: 11-12 px
- KPI number: 30-36 px

## 5. Chuẩn trang dashboard (page blueprint)

Khuyến nghị 5 trang chính, đặt tên cố định:

1. `P01_Overview`
2. `P02_Time_Pattern`
3. `P03_Station_Comparison`
4. `P04_Weather_Impact`
5. `P05_Correlation_Insights`

Khung bố cục mỗi trang:

1. Header: Title + Date range + Station filter.
2. Top row: 3-5 KPI cards.
3. Main row: 2 visual chính.
4. Bottom row: 1 visual phụ + 1 text insight box.

## 6. Chuẩn chart theo từng mục tiêu

## 6.1 Time Pattern

- Line chart: `Date` trên trục X, metric trên trục Y.
- Heatmap: `Hour` x `DayOfWeek` (nếu có tạo thêm cột), giá trị là trung bình PM2.5/O3.
- Boxplot theo `Hour` để thấy peak giờ cao điểm.

Không được:

- Vẽ >2 line trong cùng một chart nếu không dùng small multiples.

## 6.2 Station Comparison

- Bar chart theo `Station_No`, metric = mean/median.
- Dot plot xếp hạng trạm cho PM2.5 và TSP.
- Bắt buộc sort giảm dần theo giá trị chính.

## 6.3 Weather Impact

- Scatter: `Temperature` vs `O3` (có trendline).
- Scatter: `Humidity` vs `PM2.5` (có trendline).
- Color theo `Station_No`, không color theo metric để tránh nhiễu.

## 6.4 Correlation Insights

- Correlation heatmap cho: `TSP`, `PM2.5`, `O3`, `CO`, `NO2`, `SO2`, `Temperature`, `Humidity`.
- Diverging scale: âm -> trung tính -> dương (midpoint = 0).
- Hiển thị hệ số trên từng ô.

## 7. KPI chuẩn toàn dashboard

Bắt buộc thống nhất các KPI sau ở trang tổng quan:

1. Mean PM2.5 toàn kỳ
2. Mean TSP toàn kỳ
3. Trạm có PM2.5 trung bình cao nhất
4. Khung giờ PM2.5 trung bình cao nhất
5. Số bản ghi đang hiển thị sau filter

Format hiển thị:

- Giá trị + đơn vị (`ug/m3`, `%`, `degC`)
- Có delta so với kỳ trước khi đủ dữ liệu

## 8. Chuẩn tooltip và title

Mỗi visual phải có title theo mẫu:

- `[Metric] theo [Dimension] - [Scope]`

Ví dụ:

- `PM2.5 theo giờ - Toàn bộ trạm`

Tooltip tối thiểu gồm:

1. `Date`
2. `Hour` (nếu có)
3. `Station_No`
4. Metric chính + đơn vị
5. Metric phụ liên quan (nếu có)

## 9. Bộ lọc và hành vi tương tác

Global slicers bắt buộc:

- `Date` (range)
- `Station_No` (multi-select)
- `Hour` (optional cho trang time)

Interaction rules:

- Cross-filter bật mặc định giữa các visual cùng trang.
- Có nút `Reset Filters` trên mỗi trang.
- Không dùng quá 4 slicer hiển thị cùng lúc trên 1 page.

## 10. Anti-overlap workflow cho nhóm

## 10.1 Ownership matrix

- Member A: Data validation + measures logic
- Member B: Theme, KPI cards, layout system
- Member C: `P02_Time_Pattern`
- Member D: `P03_Station_Comparison`
- Member E: `P04_Weather_Impact` + `P05_Correlation_Insights`

## 10.2 Quy tắc làm việc

1. Mỗi người chỉ edit page mình sở hữu.
2. Thay đổi chung (màu, KPI definition, naming) phải cập nhật file này trước.
3. Pull/merge chỉ thực hiện sau khi QA checklist pass.
4. Không duplicate visual cùng business question ở hai page khác nhau nếu không có mục đích storytelling rõ ràng.

## 10.3 Naming convention

- Page: `Pxx_Topic`
- Visual: `V_[Page]_[Metric]_[ChartType]`
- Measure: `M_[Metric]_[Agg]`

Ví dụ:

- `V_P02_PM25_Line`
- `M_PM25_Mean`

## 11. QA checklist trước khi chốt

- Đúng schema dữ liệu sạch (`Date`, `Hour`, `Station_No`, các metrics).
- Màu biến nhất quán giữa mọi page.
- Không có chart bị rối do quá nhiều marks/lines.
- Title, axis label, đơn vị, tooltip đầy đủ.
- Insight có số liệu cụ thể (không viết chung chung).
- Filter hoạt động đúng và reset được.
- Không có visual trùng nghĩa giữa các trang.
- Phần note phương pháp có nêu xử lý missing và TSP inconsistency.

