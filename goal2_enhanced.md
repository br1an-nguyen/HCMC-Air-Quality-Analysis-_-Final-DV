
## Hệ Thống Insight — 3 Tầng Logic

### Tầng 1: Shape Classification — Phân Loại Hình Dạng Đa Giác

Đây là insight đầu tiên, đọc được ngay khi nhìn vào radar.

```python
RELIABLE_CATEGORIES = ['PM2.5', 'TSP', 'CO', 'O3']
THRESHOLDS = {'PM2.5': 15.0, 'TSP': 150.0, 'CO': 4000.0, 'O3': 100.0}

def classify_shape(percs: dict) -> tuple[str, str]:
    """
    Trả về (shape_label, mô tả ngắn) dựa trên % WHO của 4 chất.
    percs = {'PM2.5': 162.0, 'TSP': 38.9, 'CO': 23.4, 'O3': 99.9}
    """
    pm25_over = percs['PM2.5'] > 100
    o3_over   = percs['O3']   > 100
    co_over   = percs['CO']   > 100   # CO threshold = 4000 µg/m3, khó vượt
    tsp_over  = percs['TSP']  > 100

    if pm25_over and o3_over:
        # Hai trục cùng vượt ngưỡng → hình dạng phồng về 2 phía đối diện
        pm25_dominance = percs['PM2.5'] / (percs['PM2.5'] + percs['O3'])
        if pm25_dominance > 0.6:
            return ("DUAL-THREAT (PM2.5 nặng hơn)",
                    f"Cả PM2.5 ({percs['PM2.5']:.0f}% WHO) lẫn O3 ({percs['O3']:.0f}% WHO) đều vượt ngưỡng, "
                    f"trong đó bụi mịn chiếm ưu thế hơn.")
        elif pm25_dominance < 0.4:
            return ("DUAL-THREAT (O3 nặng hơn)",
                    f"Cả PM2.5 ({percs['PM2.5']:.0f}% WHO) lẫn O3 ({percs['O3']:.0f}% WHO) đều vượt ngưỡng, "
                    f"trong đó ozone chiếm ưu thế hơn.")
        else:
            return ("DUAL-THREAT (cân bằng)",
                    f"PM2.5 ({percs['PM2.5']:.0f}% WHO) và O3 ({percs['O3']:.0f}% WHO) vượt ngưỡng ở mức tương đương.")

    elif pm25_over and not o3_over:
        return ("PARTICLE-DOMINANT",
                f"PM2.5 ({percs['PM2.5']:.0f}% WHO) vượt ngưỡng rõ ràng. "
                f"O3 nằm sát ngưỡng ({percs['O3']:.0f}% WHO). "
                f"Bụi mịn là mối lo trực tiếp duy nhất.")

    elif o3_over and not pm25_over:
        return ("OZONE-DOMINANT",
                f"O3 ({percs['O3']:.0f}% WHO) vượt ngưỡng trong khi PM2.5 ({percs['PM2.5']:.0f}% WHO) "
                f"vẫn dưới mức khuyến cáo — trạm này tốt hơn về bụi nhưng xấu hơn về khí quang hóa.")

    else:
        return ("BELOW-WHO",
                f"Tất cả 4 chất đều dưới ngưỡng WHO. "
                f"PM2.5 = {percs['PM2.5']:.0f}%, O3 = {percs['O3']:.0f}%.")
```

**Kết quả shape classification cho từng trạm:**

```python
# Thanh Đa  → PARTICLE-DOMINANT
# "PM2.5 (162%) vượt ngưỡng rõ ràng. O3 nằm sát ngưỡng (100%). Bụi mịn là mối lo trực tiếp duy nhất."

# Bình Tân  → DUAL-THREAT (O3 nặng hơn)
# "Cả PM2.5 (112%) lẫn O3 (138%) đều vượt ngưỡng, trong đó ozone chiếm ưu thế hơn."

# Quận 3   → OZONE-DOMINANT
# "O3 (133%) vượt ngưỡng trong khi PM2.5 (96%) vẫn dưới mức khuyến cáo."
```

---

### Tầng 2: Axis Dominance — Trục Chi Phối (nhất quán với chart)

Tính `share` từ **capped values** để khớp với những gì mắt nhìn thấy trên chart.

```python
def get_axis_dominance_insight(station_df, station_name, region_name):
    """
    Tính phần trăm diện tích radar của từng trục DỰA TRÊN GIÁ TRỊ ĐÃ CAP.
    Nhất quán 100% với hình đa giác được vẽ.
    """
    capped, uncapped = {}, {}
    for p in RELIABLE_CATEGORIES:
        v = station_df[p].median()
        pct = (v / THRESHOLDS[p]) * 100 if pd.notna(v) else 0
        uncapped[p] = pct
        capped[p]   = min(pct, 200)   # cap ở 200% khi auto_scale=False

    total_capped = sum(capped.values())
    dominant_p   = max(capped, key=capped.get)
    dom_share    = capped[dominant_p] / total_capped * 100

    # Số thực (uncapped) để context
    actual_val = uncapped[dominant_p]
    was_capped = actual_val > 200

    lines = [
        f"📐 **Độ lệch trục ({station_name} — {region_name}):** "
        f"Hình đa giác bị kéo lệch mạnh nhất về trục **{dominant_p}**, "
        f"chiếm **{dom_share:.0f}%** tổng diện tích hiển thị "
        f"(đạt **{capped[dominant_p]:.0f}%** WHO trên biểu đồ"
        + (f", giá trị thực = **{actual_val:.0f}%** — bị ép về 200% để giữ tỉ lệ)." if was_capped
           else f".")
        + ""
    ]

    # Thêm context về trục thứ 2 nếu nó cũng vượt 100%
    second_over = {p: capped[p] for p in RELIABLE_CATEGORIES if p != dominant_p and capped[p] > 100}
    if second_over:
        second_p   = max(second_over, key=second_over.get)
        second_pct = uncapped[second_p]
        lines.append(
            f"  Trục **{second_p}** cũng vượt ngưỡng WHO ({second_pct:.0f}%), "
            f"tạo hình đa giác DUAL-THREAT — áp lực ô nhiễm từ hai nguồn độc lập."
        )

    return "\n".join(lines)
```

---

### Tầng 3: Comparative Insight — So Sánh Worst vs Best

Đây là insight quan trọng nhất, chỉ xuất hiện khi có 2 trạm trên radar.

```python
def get_comparative_insight(worst_row, best_row, df_daily, focus_pollutant):
    """
    So sánh worst vs best station trên radar 4 trục.
    Phát hiện 3 pattern: TRADEOFF, DOMINANCE, CONVERGENCE.
    """
    w_df = df_daily[df_daily['Station_No'] == worst_row['Station_No']]
    b_df = df_daily[df_daily['Station_No'] == best_row['Station_No']]

    w_percs = {p: w_df[p].median() / THRESHOLDS[p] * 100 for p in RELIABLE_CATEGORIES}
    b_percs = {p: b_df[p].median() / THRESHOLDS[p] * 100 for p in RELIABLE_CATEGORIES}

    insights = []

    # === PATTERN 1: TRADEOFF — Trạm "tốt" về chất này lại xấu hơn về chất khác ===
    tradeoff_axes = []
    for p in RELIABLE_CATEGORIES:
        if p == focus_pollutant:
            continue
        # Best station tệ hơn worst station trên trục p
        if b_percs[p] > w_percs[p] and b_percs[p] > 100:
            gap = b_percs[p] - w_percs[p]
            tradeoff_axes.append((p, gap, b_percs[p], w_percs[p]))

    if tradeoff_axes:
        tradeoff_axes.sort(key=lambda x: x[1], reverse=True)
        p, gap, b_val, w_val = tradeoff_axes[0]
        insights.append(
            f"🔄 **Nghịch lý không gian:** Trạm tốt nhất về **{focus_pollutant}** "
            f"({best_row['Location']}, {b_percs[focus_pollutant]:.0f}% WHO) lại có **{p}** "
            f"**cao hơn {gap:.0f} điểm %** so với trạm tệ nhất "
            f"({b_val:.0f}% vs {w_val:.0f}% WHO). "
            f"Hai chất này có nguồn gốc và cơ chế khác nhau — không thể tối ưu đồng thời."
        )

    # === PATTERN 2: DOMINANCE — Worst station tệ hơn trên TẤT CẢ các trục ===
    all_worse = all(w_percs[p] >= b_percs[p] for p in RELIABLE_CATEGORIES)
    if all_worse:
        worst_gap = max(w_percs[p] - b_percs[p] for p in RELIABLE_CATEGORIES)
        worst_gap_p = max(RELIABLE_CATEGORIES, key=lambda p: w_percs[p] - b_percs[p])
        insights.append(
            f"📌 **Ô nhiễm toàn diện:** {worst_row['Location']} tệ hơn {best_row['Location']} "
            f"trên cả 4 trục đáng tin cậy. Chênh lệch lớn nhất tại **{worst_gap_p}** "
            f"(+{worst_gap:.0f} điểm %). Can thiệp tại đây sẽ cải thiện đa chiều."
        )

    # === PATTERN 3: PM2.5 vs O3 absolute gap ===
    pm25_gap = w_percs['PM2.5'] - b_percs['PM2.5']
    o3_gap   = b_percs['O3']   - w_percs['O3']    # dương = best tệ hơn về O3

    insights.append(
        f"📊 **Khoảng cách định lượng:** "
        f"PM2.5 tại {worst_row['Location']} cao hơn {best_row['Location']} "
        f"**{w_df['PM2.5'].median() - b_df['PM2.5'].median():.1f} µg/m³ "
        f"(+{pm25_gap:.0f} điểm %)**. "
        + (f"Ngược lại, O3 tại {best_row['Location']} cao hơn {o3_gap:.0f} điểm % — "
           f"trục O3 phản ánh trạng thái ô nhiễm khí quang hóa cao hơn tại khu vực này."
           if o3_gap > 5 else
           f"O3 ở cả hai trạm ở mức tương đương.")
    )

    return "\n\n".join(insights)
```

**Kết quả thực tế với PM2.5 focus (Thanh Đa vs Quận 3):**

```
🔄 Nghịch lý không gian: Trạm tốt nhất về PM2.5
   (Quận 3, 96% WHO) lại có O3 cao hơn 33 điểm %
   so với trạm tệ nhất (133% vs 100% WHO).
   Hai chất này có nguồn gốc và cơ chế khác nhau —
   không thể tối ưu đồng thời.

📊 Khoảng cách định lượng: PM2.5 tại Thanh Đa cao hơn
   Quận 3 9.95 µg/m³ (+66 điểm %). Ngược lại,
   O3 tại Quận 3 cao hơn 33 điểm % — trục O3
   phản ánh trạng thái ô nhiễm khí quang hóa cao hơn
   tại khu vực giao thông này.
```

---

### Assembling — Ghép Lại Toàn Bộ Insight Block

```python
def render_radar_insight(worst_row, best_row, df_daily, focus_pollutant):
    w_df = df_daily[df_daily['Station_No'] == worst_row['Station_No']]
    b_df = df_daily[df_daily['Station_No'] == best_row['Station_No']]

    # Tính percs cho shape classification
    w_percs = {p: w_df[p].median() / THRESHOLDS[p] * 100 for p in RELIABLE_CATEGORIES}
    b_percs = {p: b_df[p].median() / THRESHOLDS[p] * 100 for p in RELIABLE_CATEGORIES}

    w_shape_label, w_shape_desc = classify_shape(w_percs)
    b_shape_label, b_shape_desc = classify_shape(b_percs)

    st.info(
        f"#### 🕸️ Phân Tích Hình Thái Đa Giác\n\n"

        f"**🔴 {worst_row['Location']} ({worst_row['Region']}) — [{w_shape_label}]**\n"
        f"{w_shape_desc}\n\n"
        + get_axis_dominance_insight(w_df, worst_row['Location'], worst_row['Region'])
        + "\n\n"

        f"**🔵 {best_row['Location']} ({best_row['Region']}) — [{b_shape_label}]**\n"
        f"{b_shape_desc}\n\n"
        + get_axis_dominance_insight(b_df, best_row['Location'], best_row['Region'])
        + "\n\n---\n\n"

        + get_comparative_insight(worst_row, best_row, df_daily, focus_pollutant)
    )
```

---

## Ví Dụ Output Đầy Đủ Theo Từng Focus Pollutant

### Khi `focus_pollutant = PM2.5` (Thanh Đa vs Quận 3)

> **🔴 Thanh Đa (Dân cư) — [PARTICLE-DOMINANT]**
> PM2.5 (162% WHO) vượt ngưỡng rõ ràng. O3 nằm sát ngưỡng (100%). Bụi mịn là mối lo trực tiếp duy nhất.
> 📐 Hình đa giác bị kéo lệch mạnh nhất về trục  **PM2.5** , chiếm **50%** tổng diện tích hiển thị.
>
> **🔵 Quận 3 (Giao thông) — [OZONE-DOMINANT]**
> O3 (133% WHO) vượt ngưỡng trong khi PM2.5 (96% WHO) vẫn dưới mức khuyến cáo — trạm này tốt hơn về bụi nhưng xấu hơn về khí quang hóa.
> 📐 Hình đa giác bị kéo lệch mạnh nhất về trục  **O3** , chiếm **49%** tổng diện tích hiển thị.
>
> ---
>
> 🔄 **Nghịch lý không gian:** Trạm tốt nhất về PM2.5 (Quận 3, 96% WHO) lại có O3 cao hơn **33 điểm %** so với trạm tệ nhất (133% vs 100% WHO). Hai chất này có nguồn gốc và cơ chế khác nhau — không thể tối ưu đồng thời.
>
> 📊 **Khoảng cách định lượng:** PM2.5 tại Thanh Đa cao hơn Quận 3  **9.95 µg/m³ (+66 điểm %)** . Ngược lại, O3 tại Quận 3 cao hơn 33 điểm % — phản ánh đặc trưng ô nhiễm quang hóa của khu vực giao thông mật độ cao.

---

### Khi `focus_pollutant = O3` (Bình Tân vs Thanh Đa)

> **🔴 Bình Tân (Giao thông) — [DUAL-THREAT (O3 nặng hơn)]**
> Cả PM2.5 (112% WHO) lẫn O3 (138% WHO) đều vượt ngưỡng, trong đó ozone chiếm ưu thế hơn.
> 📐 Hình đa giác bị kéo lệch mạnh nhất về trục  **O3** , chiếm **45%** tổng diện tích hiển thị.
>
> **🔵 Thanh Đa (Dân cư) — [PARTICLE-DOMINANT]**
> PM2.5 (162% WHO) vượt ngưỡng rõ ràng. O3 nằm sát ngưỡng (100%). Bụi mịn là mối lo trực tiếp duy nhất.
> 📐 Hình đa giác bị kéo lệch mạnh nhất về trục  **PM2.5** , chiếm **50%** tổng diện tích hiển thị.
>
> ---
>
> 🔄 **Nghịch lý không gian:** Trạm tốt nhất về O3 (Thanh Đa, 100% WHO) lại có PM2.5 cao hơn **50 điểm %** so với Bình Tân (162% vs 112% WHO).
>
> 📊 **Khoảng cách định lượng:** O3 tại Bình Tân cao hơn Thanh Đa  **38.1 µg/m³ (+38 điểm %)** . Bình Tân mang đặc trưng kép — vừa có bụi mịn vượt ngưỡng vừa có ozone quang hóa cao.

---

## Tóm Tắt Logic Decision Tree

```
Radar 4 trục (PM2.5, TSP, CO, O3)
│
├── Tầng 1: Phân loại từng trạm
│     ├── PM2.5 > 100% AND O3 > 100%  → DUAL-THREAT
│     ├── PM2.5 > 100% AND O3 ≤ 100%  → PARTICLE-DOMINANT  
│     ├── PM2.5 ≤ 100% AND O3 > 100%  → OZONE-DOMINANT
│     └── Cả hai ≤ 100%               → BELOW-WHO
│
├── Tầng 2: Trục chi phối (capped values, nhất quán với chart)
│     └── dominant_axis = max(capped_values)
│         share = capped[dominant] / sum(capped) × 100
│
└── Tầng 3: So sánh 2 trạm
      ├── Pattern TRADEOFF → phát hiện nghịch lý không gian
      ├── Pattern DOMINANCE → trạm A tệ hơn B trên mọi trục
      └── PM2.5/O3 gap → khoảng cách định lượng cụ thể
```
