Đọc xong toàn bộ code. Để tôi đối chiếu hệ thống từng lỗi trong review cũ và đánh giá code mới.

---

## ✅ Những gì đã được sửa đúng

| # | Lỗi cũ | Trạng thái | Vị trí |
|---|---|---|---|
| 1 | PM2.5 kết luận ngược | ✅ Sửa đúng | `render_conclusion()` line 382 |
| 2 | O3 gán sai địa chỉ | ✅ Sửa đúng | `render_conclusion()` line 385 |
| 3 | Cơ chế NO-O3 sai chiều | ✅ Sửa đúng | Line 385–386 |
| 4 | KPI 2 hardcode TSP | ✅ Sửa đúng | Line 122–136 |
| 5 | Bar chart không filter flag | ✅ Sửa đúng | Line 228–239 (loop từng pollutant) |
| 6 | Static insight | ✅ Sửa đúng | Line 290–301 |
| 7 | Box plot 1 màu | ✅ Sửa đúng | Line 281 dùng `Pastel` |
| 8 | Anomaly Trạm 5 | ✅ Có cảnh báo | Line 99 `st.warning()` |

Tất cả 8 lỗi từ review đã được xử lý. Tuy nhiên có **4 vấn đề mới** và **2 đề xuất chart** cần xem xét.

---

## 🟠 Vấn đề mới phát hiện

### 1. `px.density_heatmap` dùng sai mục đích — Line 328, 341

```python
# Hiện tại: df_timespace đã là dữ liệu tổng hợp (mean theo tháng)
fig_heat = px.density_heatmap(
    df_timespace,
    x='Month_Year', y='Location', z=focus_pollutant,
    ...
)
```

`px.density_heatmap` được thiết kế để **đếm tần suất/histogram 2D**, không phải hiển thị giá trị đã tổng hợp. Nó sẽ tự aggregate lại `z` theo `histfunc` mặc định — có thể gây hiển thị sai.

**Sửa:** Dùng `go.Heatmap()` hoặc `px.imshow()` với pivot table:

```python
pivot = df_timespace.pivot(index='Location', columns='Month_Year', values=focus_pollutant)

fig_heat = px.imshow(
    pivot,
    color_continuous_scale="Reds",
    aspect="auto",
    labels=dict(x="Tháng/Năm", y="Trạm quan trắc", color=f"{focus_pollutant} (µg/m³)"),
    title=f"Heatmap Diễn Biến {focus_pollutant} Theo Thời Gian và Trạm"
)
```

---

### 2. KPI 2 tính từ `df` (toàn bộ) thay vì `df_filtered` — Line 125–129

```python
# KPI 2 dùng df gốc, không theo date/station filter của user
df_network = df[df[flag_col] == 0]
network_mean = df_network[focus_pollutant].mean()
```

Nếu user lọc chỉ còn 3 tháng mùa khô hoặc 3 trạm, KPI 2 vẫn hiện trung bình **toàn bộ dữ liệu**. Không có label nào giải thích điều này — gây ảo giác so sánh sai.

**Sửa:** Tính từ `df_filtered` và thêm note thời gian:

```python
network_mean = df_filtered[focus_pollutant].mean()
# label: "Trung bình (khoảng lọc)"
```

---

### 3. Đoạn cuối `dominant_insight` vẫn bán hardcode — Line 300

```python
dominant_insight = (
    f"...chất chi phối rủi ro sức khỏe chính là **{dominant_pollutant}** tại khu vực **{dominant_region}**. "
    f"Điều này phản ánh sự khác biệt về nguồn phát thải (ví dụ: PM2.5/NO2 từ đốt cháy tại Giao thông/Công nghiệp, "
    f"hay O3 từ quang hóa tại Nền đô thị)."  # <-- CỨNG
)
```

Phần ví dụ trong ngoặc không thay đổi theo `dominant_region`. Nếu `dominant_region = "Dân cư"` và `dominant_pollutant = "PM2.5"`, câu "PM2.5/NO2 từ đốt cháy tại Giao thông/Công nghiệp" không còn phù hợp.

**Sửa:** Map cơ chế theo pollutant động:

```python
mechanism_map = {
    'PM2.5': 'tích lũy từ đốt cháy và bụi đường',
    'O3': 'quang hóa thứ cấp dưới bức xạ mặt trời',
    'NO2': 'xả thải từ phương tiện và đốt nhiên liệu',
    'CO': 'đốt cháy không hoàn toàn (xe máy, xe tải)',
    'SO2': 'đốt than/dầu tại khu công nghiệp',
    'TSP': 'bụi đường và hoạt động xây dựng'
}
mechanism = mechanism_map.get(dominant_pollutant, 'nguồn phát thải đặc thù')
dominant_insight = (
    f"...chất chi phối là **{dominant_pollutant}** tại **{dominant_region}**, "
    f"chủ yếu do {mechanism}."
)
```

---

### 4. Heatmap không có title — Line 328, 341

Cả hai nhánh `if/else` của heatmap đều thiếu `title=`. Đây là chart lớn nhất trang nhưng không có nhãn rõ ràng.

**Sửa:** Thêm vào `px.imshow()` (sau khi sửa lỗi 1):

```python
title=f"Diễn Biến {focus_pollutant} Theo Thời Gian & Trạm Quan Trắc"
```

---

## 🟢 Đề xuất chart bổ sung

### Đề xuất 1 — Radar Chart (Spider Chart) so sánh toàn diện các trạm

**Lý do:** Bar chart hiện tại so sánh theo Region × Pollutant. Nhưng để thấy **profile ô nhiễm tổng thể của từng trạm** cùng lúc trên 6 chất, radar chart là lựa chọn tốt nhất. Đây cũng là chart duy nhất có thể trả lời câu hỏi: *"Trạm nào đa chiều nguy hiểm nhất?"*

```python
import plotly.graph_objects as go

categories = ['PM2.5', 'TSP', 'CO', 'NO2', 'O3', 'SO2']
thresholds = {"PM2.5": 15.0, "TSP": 50.0, "CO": 10000.0,
              "O3": 100.0, "SO2": 40.0, "NO2": 40.0}

fig_radar = go.Figure()
for _, row in map_data.iterrows():
    # Lấy % WHO cho từng chất từ df_filtered theo station
    station_df = df_filtered[df_filtered['Station_No'] == row['Station_No']]
    values = []
    for p in categories:
        flag_col = f"{p}_flag"
        if flag_col in station_df.columns:
            v = station_df[station_df[flag_col] == 0][p].mean()
        else:
            v = station_df[p].mean()
        values.append((v / thresholds[p]) * 100 if pd.notna(v) else 0)
    
    fig_radar.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name=row['Location'],
        opacity=0.6
    ))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 200])),
    title="Profile Ô Nhiễm Đa Chiều Theo Trạm (% WHO)"
)
```

---

### Đề xuất 2 — Ranked Horizontal Bar cho focus_pollutant

**Lý do:** Map bubble hiện tại khó so sánh chênh lệch tuyệt đối giữa các trạm (vì kích thước bubble không tuyến tính trực quan). Một horizontal bar chart đơn giản xếp hạng trạm theo `focus_pollutant` với đường kẻ ngưỡng WHO sẽ là panel đọc nhanh hiệu quả hơn — đặt ngay dưới map.

```python
map_sorted = map_data.sort_values(focus_pollutant, ascending=True)
fig_rank = px.bar(
    map_sorted,
    x=focus_pollutant,
    y='Location',
    color='Region',
    orientation='h',
    title=f"Xếp Hạng Trạm Theo {focus_pollutant}",
    labels={'Location': '', focus_pollutant: f"{focus_pollutant} (µg/m³)"},
    text_auto='.1f'
)
fig_rank.add_vline(x=threshold, line_dash="dash", line_color="#FFB703",
                   annotation_text="Ngưỡng WHO")
```

---

## 📋 Tổng kết

| Loại | Số lượng | Ghi chú |
|---|---|---|
| Lỗi cũ đã sửa | 8/8 | Sửa đúng hướng, đầy đủ |
| Vấn đề mới phát hiện | 4 | Lỗi heatmap (nghiêm trọng nhất), KPI2 scope, insight bán-cứng, thiếu title |
| Đề xuất chart mới | 2 | Radar chart (ưu tiên cao), Ranked bar (ưu tiên trung bình) |

Vấn đề cần sửa ngay nhất là **`px.density_heatmap`** — nó đang aggregate dữ liệu đã tổng hợp một lần nữa và nhiều khả năng hiển thị sai giá trị thực.