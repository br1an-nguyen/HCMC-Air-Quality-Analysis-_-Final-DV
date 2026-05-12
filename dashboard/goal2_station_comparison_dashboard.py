import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dashboard.ui_theme import (
    inject_global_css, render_page_header,
    render_section_header, render_divider, render_insight_box, render_conclusion_box,
    render_standard_sidebar, get_icon_html
)

# ============= LOAD DATA =============
@st.cache_data
def load_data():
    df = pd.read_csv('data/cleaned/Air_Quality_HCMC_Cleaned.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    stations_meta = pd.DataFrame([
        {'Station_No': 1, 'Region': 'Nền đô thị', 'Lat': 10.8699, 'Lon': 106.7960, 'Location': 'ĐHQG Hồ Chí Minh'},
        {'Station_No': 2, 'Region': 'Giao thông', 'Lat': 10.7410, 'Lon': 106.6171, 'Location': 'Bình Tân'},
        {'Station_No': 3, 'Region': 'Công nghiệp', 'Lat': 10.8162, 'Lon': 106.6204, 'Location': 'KCN Tân Bình'},
        {'Station_No': 4, 'Region': 'Dân cư', 'Lat': 10.8158, 'Lon': 106.7174, 'Location': 'Thanh Đa'},
        {'Station_No': 5, 'Region': 'Giao thông', 'Lat': 10.7764, 'Lon': 106.6878, 'Location': 'Quận 3'},
        {'Station_No': 6, 'Region': 'Giao thông + Dân cư', 'Lat': 10.7805, 'Lon': 106.6595, 'Location': 'Quận 10'}
    ])
    
    df_merged = df.merge(stations_meta, on='Station_No')
    return df_merged, stations_meta


THRESHOLDS = {"PM2.5": 15.0, "TSP": 150.0, "CO": 4000.0, "O3": 100.0, "SO2": 40.0, "NO2": 25.0}


def _sidebar_extra_g2():
    pollutants = ['PM2.5', 'TSP', 'CO', 'O3']
    focus_pollutant = st.selectbox("Chất ô nhiễm chính", options=pollutants, index=0)

    threshold_defaults = {'PM2.5': 15.0, 'TSP': 150.0, 'CO': 4000.0, 'O3': 100.0}
    threshold = st.number_input("Ngưỡng WHO/QCVN (µg/m³)", value=threshold_defaults.get(focus_pollutant, 50.0))

    region_opts = ['Nền đô thị', 'Giao thông', 'Công nghiệp', 'Dân cư', 'Giao thông + Dân cư']
    selected_regions = st.multiselect(
        "Loại khu vực",
        options=region_opts,
        default=region_opts,
    )

    return {
        'focus_pollutant': focus_pollutant,
        'threshold': threshold,
        'selected_regions': selected_regions,
    }


# ============= RADAR INSIGHT HELPERS =============
RELIABLE_CATEGORIES = ['PM2.5', 'TSP', 'CO', 'O3']

def classify_shape(percs: dict) -> str:
    """Trả về mô tả ngắn dựa trên % WHO của 4 chất."""
    pm25_over = percs.get('PM2.5', 0) > 100
    o3_over   = percs.get('O3', 0)   > 100
    
    if pm25_over and o3_over:
        pm25_dominance = percs['PM2.5'] / (percs['PM2.5'] + percs['O3'])
        if pm25_dominance > 0.6:
            return f"Cả PM2.5 ({percs['PM2.5']:.0f}% WHO) lẫn O3 ({percs['O3']:.0f}% WHO) đều vượt ngưỡng, trong đó PM2.5 (bụi mịn) chiếm ưu thế hơn."
        elif pm25_dominance < 0.4:
            return f"Cả PM2.5 ({percs['PM2.5']:.0f}% WHO) lẫn O3 ({percs['O3']:.0f}% WHO) đều vượt ngưỡng, trong đó O3 (ozone) chiếm ưu thế hơn."
        else:
            return f"PM2.5 ({percs['PM2.5']:.0f}% WHO) và O3 ({percs['O3']:.0f}% WHO) vượt ngưỡng ở mức tương đương."
    elif pm25_over and not o3_over:
        return f"PM2.5 ({percs['PM2.5']:.0f}% WHO) vượt ngưỡng rõ ràng. O3 nằm sát dưới ngưỡng ({percs['O3']:.0f}% WHO). PM2.5 (Bụi mịn) là mối lo chính."
    elif o3_over and not pm25_over:
        return f"O3 ({percs['O3']:.0f}% WHO) vượt ngưỡng trong khi PM2.5 ({percs['PM2.5']:.0f}% WHO) vẫn dưới mức khuyến cáo — trạm này tốt hơn về bụi nhưng xấu hơn về khí quang hóa."
    else:
        return f"Tất cả 4 chất đều dưới ngưỡng WHO. PM2.5 = {percs['PM2.5']:.0f}%, O3 = {percs['O3']:.0f}%."

def get_axis_dominance_insight(station_df, station_name, region_name):
    """Tính phần trăm diện tích radar của từng trục dựa trên Capped Values."""
    capped, uncapped = {}, {}
    for p in RELIABLE_CATEGORIES:
        v = station_df[p].median()
        pct = (v / THRESHOLDS.get(p, 1)) * 100 if pd.notna(v) else 0
        uncapped[p] = pct
        capped[p]   = min(pct, 200)

    total_capped = sum(capped.values())
    if total_capped == 0: return ""
    
    dominant_p   = max(capped, key=capped.get)
    dom_share    = capped[dominant_p] / total_capped * 100
    actual_val   = uncapped[dominant_p]
    was_capped   = actual_val > 200

    main_line = (
        f"<b>Độ lệch trục ({station_name}):</b> "
        f"Hình đa giác bị kéo lệch mạnh nhất về trục <b>{dominant_p}</b>, "
        f"chiếm gần <b>{dom_share:.0f}%</b> tổng diện tích hiển thị (đạt <b>{capped[dominant_p]:.0f}%</b> WHO"
        + (f", giá trị thực = <b>{actual_val:.0f}%</b>)." if was_capped else f").")
    )
    
    # Kiểm tra trục thứ 2
    second_over = {p: capped[p] for p in RELIABLE_CATEGORIES if p != dominant_p and capped[p] > 100}
    if second_over:
        second_p   = max(second_over, key=second_over.get)
        main_line += f" Trục <b>{second_p}</b> cũng vượt ngưỡng WHO ({uncapped[second_p]:.0f}%)."
    
    return main_line

def get_comparative_insight(worst_row, best_row, df_daily, focus_pollutant) -> list[str]:
    """So sánh worst vs best station trên radar 4 trục. Trả về list các dòng insight."""
    w_df = df_daily[df_daily['Station_No'] == worst_row['Station_No']]
    b_df = df_daily[df_daily['Station_No'] == best_row['Station_No']]

    w_percs = {p: w_df[p].median() / THRESHOLDS.get(p, 1) * 100 for p in RELIABLE_CATEGORIES}
    b_percs = {p: b_df[p].median() / THRESHOLDS.get(p, 1) * 100 for p in RELIABLE_CATEGORIES}

    insights = []
    
    # Pattern 1: Tradeoff
    tradeoff_axes = []
    for p in RELIABLE_CATEGORIES:
        if p == focus_pollutant: continue
        if b_percs[p] > w_percs[p] and b_percs[p] > 100:
            gap = b_percs[p] - w_percs[p]
            tradeoff_axes.append((p, gap, b_percs[p], w_percs[p]))
    
    if tradeoff_axes:
        tradeoff_axes.sort(key=lambda x: x[1], reverse=True)
        p, gap, b_val, w_val = tradeoff_axes[0]
        insights.append(
            f"<b>Nghịch lý không gian:</b> Trạm tốt nhất về <b>{focus_pollutant}</b> "
            f"({best_row['Location']}, {b_percs.get(focus_pollutant, 0):.0f}% WHO) lại có <b>{p}</b> "
            f"<b>cao hơn {gap:.0f} điểm %</b> so với trạm tệ nhất "
            f"({b_val:.0f}% vs {w_val:.0f}% WHO). "
        )

    # Pattern 2: Dominance
    all_worse = all(w_percs[p] >= b_percs[p] for p in RELIABLE_CATEGORIES)
    if all_worse:
        worst_gap = max(w_percs[p] - b_percs[p] for p in RELIABLE_CATEGORIES)
        worst_gap_p = max(RELIABLE_CATEGORIES, key=lambda p: w_percs[p] - b_percs[p])
        insights.append(
            f"<b>Ô nhiễm toàn diện:</b> {worst_row['Location']} tệ hơn {best_row['Location']} "
            f"trên cả 4 trục đáng tin cậy. Chênh lệch lớn nhất tại <b>{worst_gap_p}</b> "
            f"(+{worst_gap:.0f} điểm %). Can thiệp tại đây sẽ cải thiện đa chiều."
        )

    # Pattern 3: Quantitative Gap
    pm25_gap = w_percs['PM2.5'] - b_percs['PM2.5']
    o3_gap   = b_percs['O3']   - w_percs['O3']
    
    gap_val = w_df['PM2.5'].median() - b_df['PM2.5'].median()
    insights.append(
        f"<b>Khoảng cách định lượng:</b> "
        f"PM2.5 tại {worst_row['Location']} cao hơn {best_row['Location']} "
        f"<b>{gap_val:.1f} µg/m³ (+{pm25_gap:.0f}% )</b>. "
        + (f"Ngược lại, O3 tại {best_row['Location']} cao hơn {o3_gap:.0f}% — trục O3 phản ánh trạng thái ô nhiễm khí quang hóa cao hơn tại khu vực này."
           if o3_gap > 5 else "O3 ở cả hai trạm ở mức tương đương.")
    )
    
    return insights

def render_radar_insight(worst_row, best_row, df_daily, focus_pollutant):
    """Hàm main để render toàn bộ insight radar block sử dụng render_insight_box."""
    w_df = df_daily[df_daily['Station_No'] == worst_row['Station_No']]
    b_df = df_daily[df_daily['Station_No'] == best_row['Station_No']]

    w_percs = {p: w_df[p].median() / THRESHOLDS.get(p, 1) * 100 for p in RELIABLE_CATEGORIES}
    b_percs = {p: b_df[p].median() / THRESHOLDS.get(p, 1) * 100 for p in RELIABLE_CATEGORIES}

    w_desc = classify_shape(w_percs)
    b_desc = classify_shape(b_percs)

    # Xây dựng danh sách các dòng insight (bullet points)
    lines = [
        f"<b>{worst_row['Location']} ({worst_row['Region']}):</b> {w_desc}",
        get_axis_dominance_insight(w_df, worst_row['Location'], worst_row['Region']),
        f"<b>{best_row['Location']} ({best_row['Region']}):</b> {b_desc}",
        get_axis_dominance_insight(b_df, best_row['Location'], best_row['Region'])
    ]
    
    # Thêm các dòng so sánh
    comp_insights = get_comparative_insight(worst_row, best_row, df_daily, focus_pollutant)
    lines.extend(comp_insights)

    # Render sử dụng component chuẩn của hệ thống
    render_insight_box(lines, title="Phân Tích Hình Thái Đa Giác", icon_name="analysis")

def main():
    # Note: st.set_page_config is handled by app.py

    inject_global_css()

    render_page_header(
        "Phân bố không gian ô nhiễm TPHCM",
        "Phân tích sự khác biệt nồng độ ô nhiễm giữa các khu vực đặc trưng"
    )

    try:
        with st.spinner("Đang tải dữ liệu..."):
            df, stations_meta = load_data()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")
        st.stop()

    sb = render_standard_sidebar(
        df,
        datetime_col="Date",
        station_col="Station_No",
        station_format_func=lambda x: f"Trạm {x} - {stations_meta.loc[stations_meta['Station_No'] == x, 'Location'].iloc[0]}",
        sidebar_key_prefix="g2",
        extra_widgets_fn=_sidebar_extra_g2,
    )
    selected_station_ids = sb["stations"]
    start_date = sb["start_date"]
    end_date = sb["end_date"]
    focus_pollutant = sb["focus_pollutant"]
    threshold = sb["threshold"]
    selected_regions = sb["selected_regions"]

    # ============= GLOBAL THRESHOLDS =============

    # ============= FILTER DATA =============
    # Thêm .copy() để tránh cảnh báo SettingWithCopyWarning của pandas
    df_filtered = df[
        (df['Date'] >= pd.Timestamp(start_date)) &
        (df['Date'] <= pd.Timestamp(end_date))
    ].copy()

    df_filtered = df_filtered[
        (df_filtered['Station_No'].isin(selected_station_ids)) &
        (df_filtered['Region'].isin(selected_regions))
    ].copy()

    # Apply data cleaning flag check: Chỉ cho phép các nguồn dữ liệu có flag = 0 mới là hợp lệ
    pollutants_all = ['PM2.5', 'TSP', 'CO', 'NO2', 'O3', 'SO2']
    for p in pollutants_all:
        flag_col = f"{p}_flag"
        if flag_col in df_filtered.columns:
            # Những dòng có flag khác 0 sẽ bị gán thành NaN để loại khỏi mọi bước tính toán tiếp theo
            df_filtered.loc[df_filtered[flag_col] != 0, p] = np.nan

    # ============= DAILY AGGREGATION =============
    df_filtered['Date_only'] = df_filtered['Date'].dt.date

    # Sắp xếp để tính rolling window cho O3
    df_filtered = df_filtered.sort_values(by=['Station_No', 'Date'])

    df_daily = df_filtered.groupby(['Station_No', 'Location', 'Lat', 'Lon', 'Region', 'Date_only'])[pollutants_all].mean().reset_index()

    # Tính O3 8-hour peak average (Chuẩn WHO)
    if 'O3' in df_filtered.columns:
        df_filtered['O3_8h_rolling'] = df_filtered.groupby(['Station_No', 'Date_only'])['O3'].transform(lambda x: x.rolling(8, min_periods=1).mean())
        o3_daily_max = df_filtered.groupby(['Station_No', 'Date_only'])['O3_8h_rolling'].max().reset_index()
        # Replace O3 daily mean with O3 8h max
        df_daily = df_daily.drop(columns=['O3'])
        df_daily = df_daily.merge(o3_daily_max.rename(columns={'O3_8h_rolling': 'O3'}), on=['Station_No', 'Date_only'], how='left')



    # ============= LAYER 2: SPATIAL OVERVIEW =============
    if df_filtered.empty:
        st.warning("Không có dữ liệu thỏa mãn bộ lọc hiện tại.")
        st.stop()

    # Aggregates for Map
    map_data = df_daily.groupby(['Station_No', 'Location', 'Lat', 'Lon', 'Region'])[focus_pollutant].median().reset_index()
    map_data = map_data.dropna(subset=[focus_pollutant])

    # KPI CARDS SECTION (4 cards)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        worst_station = map_data.loc[map_data[focus_pollutant].idxmax()]
        st.metric(
            label=f"Trạm cao nhất ({focus_pollutant})",
            value=f"Trạm {int(worst_station['Station_No'])}",
            delta=f"{worst_station[focus_pollutant]:.1f} µg/m³", 
            delta_color="inverse"
        )

    with kpi2:
        network_mean = df_daily[focus_pollutant].median()
        st.metric(
            label="Trung vị (khoảng lọc)",
            value=f"{network_mean:.1f} µg/m³",
            delta="Toàn TPHCM",
            delta_color="off"
        )

    with kpi3:
        best_station = map_data.loc[map_data[focus_pollutant].idxmin()]
        diff = worst_station[focus_pollutant] - best_station[focus_pollutant]
        st.metric(
            label="Chênh lệch Max-Min",
            value=f"{diff:.1f} µg/m³",
            delta=f"Min: {best_station[focus_pollutant]:.1f}",
            delta_color="off"
        )

    with kpi4:
        exceed_days_per_station = df_daily[df_daily[focus_pollutant] > threshold].groupby('Station_No').size()
        total_days_per_station = df_daily.groupby('Station_No').size()
        exceed_pct = (exceed_days_per_station / total_days_per_station).fillna(0) * 100
        
        if not exceed_pct.empty and exceed_pct.max() > 0:
            worst_station_id = exceed_pct.idxmax()
            worst_pct = exceed_pct.max()
            val_str = f"Trạm {int(worst_station_id)}"
        else:
            worst_pct = 0
            val_str = "Không trạm nào"
            
        st.metric(
            label="Vượt chuẩn WHO nhiều nhất",
            value=val_str,
            delta=f"{worst_pct:.1f}% số ngày", 
            delta_color="inverse"
        )

    render_divider()

    col_map, col_info = st.columns([7, 3])

    with col_map:
        render_section_header(f"Bản Đồ Phân Bố {focus_pollutant}")
        fig_map = px.scatter_mapbox(
            map_data,
            lat="Lat",
            lon="Lon",
            size=focus_pollutant,
            color=focus_pollutant,
            hover_name="Location",
            hover_data={
                "Station_No": False,
                "Region": True,
                focus_pollutant: ":.1f",
                "Lat": False,
                "Lon": False,
            },
            labels={"Region": "Loại khu vực", focus_pollutant: f"Nồng độ {focus_pollutant}"},
            color_continuous_scale="Reds",
            size_max=35,
            zoom=10.5,
            mapbox_style="carto-positron"
        )
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(title=f"{focus_pollutant}<br>(µg/m³)")
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with col_info:
        render_section_header("Điểm Nóng Không Gian")
        st.markdown(f"**Trạm {worst_station['Location']} ({worst_station['Region']})** đang là điểm nóng nhất về **{focus_pollutant}** ({worst_station[focus_pollutant]:.1f} µg/m³).")
        
        render_insight_box([
            f"Chênh lệch nồng độ giữa trạm cao nhất và thấp nhất là <b>{diff:.1f} µg/m³</b>.",
            f"Có <b>{(map_data[focus_pollutant] > threshold).sum()}/{len(map_data)}</b> trạm đang có nồng độ trung vị vượt ngưỡng khuyến cáo ({threshold} µg/m³)."
        ], title="Thực trạng dữ liệu", icon_name="analysis")

    st.markdown("---")

    # ============= NEW: RANKED HORIZONTAL BAR =============
    render_section_header(f"Xếp Hạng Trạm Theo {focus_pollutant}")
    map_sorted = map_data.sort_values(focus_pollutant, ascending=True)

    if threshold > 0:
        map_sorted['Alert'] = map_sorted[focus_pollutant].apply(lambda x: 'Vượt ngưỡng' if x > threshold else 'An toàn')
        color_map = {'Vượt ngưỡng': '#B23A2F', 'An toàn': '#94A3B8'}
        color_col = 'Alert'
    else:
        color_map = None
        color_col = 'Region'

    fig_rank = px.bar(
        map_sorted,
        x=focus_pollutant,
        y='Location',
        color=color_col,
        color_discrete_map=color_map,
        orientation='h',
        labels={'Location': '', focus_pollutant: f"{focus_pollutant} (µg/m³)", 'Alert': 'Trạng thái'},
        text_auto='.1f'
    )
    if threshold > 0:
        fig_rank.add_vline(
            x=threshold, 
            line_dash="dash", 
            line_color="#E63946", 
            annotation_text="Ngưỡng WHO", 
            annotation_position="top right", 
            layer="above",
            annotation=dict(
                bgcolor="rgba(255, 255, 255, 0.85)",
                bordercolor="#D9E4EC",
                borderpad=3,
                yshift=15
            )
        )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown("---")

    # ============= LAYER 3: ANALYTICAL DEEP DIVE =============
    render_section_header("Phân Tích Sâu Đa Chiều")

    # BẢNG MÀU CHUẨN TỪ DESIGN FORMAT CỦA DỰ ÁN
    COLOR_MAP = {
        'PM2.5': '#B23A2F', 'TSP': '#6F1D1B', 'O3': '#1F8A70',
        'CO': '#4E5D8A', 'NO2': '#D98E04', 'SO2': '#2B7BBB'
    }

    with st.container(border=True):
        # --- PHẦN 1: XỬ LÝ DỮ LIỆU (TỪ CODE GỐC CỦA BẠN) ---
        pollutants_to_plot = ['PM2.5', 'TSP', 'CO', 'O3']
        valid_pollutants = [p for p in pollutants_to_plot if p in df_filtered.columns]
        
        mean_data = []
        for region in df_filtered['Region'].unique():
            region_data = {'Region': region}
            df_r = df_daily[df_daily['Region'] == region]
            for p in valid_pollutants:
                val = df_r[p].median()
                region_data[p] = val
            mean_data.append(region_data)
            
        df_region = pd.DataFrame(mean_data)
        cols_to_melt = valid_pollutants
        df_region_melt = df_region.melt(id_vars='Region', value_vars=cols_to_melt, var_name='Pollutant', value_name='Concentration')
        
        # Chuẩn hóa về % so với ngưỡng WHO
        df_region_melt['Percent_WHO'] = df_region_melt.apply(
            lambda row: (row['Concentration'] / THRESHOLDS.get(row['Pollutant'], 1)) * 100, axis=1
        )

       
        # 1. Sắp xếp (Sort) dữ liệu trước khi vẽ để các thanh bar hiển thị có thứ tự (Gestalt Principle)
        df_region_melt = df_region_melt.sort_values(by=['Region', 'Percent_WHO'], ascending=[True, True])
        
        # 2. Vẽ biểu đồ (Áp dụng đúng Color Mapping)
        fig1 = px.bar(
            df_region_melt,
            x='Percent_WHO',
            y='Pollutant',
            facet_col='Region',
            facet_col_wrap=2,
            color='Pollutant',            # Đổi sang color theo chất ô nhiễm
            color_discrete_map=COLOR_MAP, # Áp dụng bảng màu chuẩn
            orientation='h',
            title="Hồ Sơ Ô Nhiễm Theo Khu Vực (% WHO)<br>",
            labels={'Percent_WHO': '% WHO', 'Pollutant': 'Chất Ô Nhiễm', 'Region': 'Khu vực'},
            hover_data={'Concentration': ':.1f'}
        )
        
        fig1.update_layout(
            showlegend=False,
            height=700,
            margin=dict(t=50, b=30, l=30, r=30),
            plot_bgcolor='#FFFFFF'        # Thêm background chuẩn của theme
        )
        
        # 3. Chỉnh màu đường tham chiếu về màu cảnh báo của dự án (#D98E04)
        fig1.add_vline(
        x=100, 
        line_dash="dash", 
        line_color="#D98E04", 
        annotation_text="100% WHO", 
        annotation_position="top right", 
        layer="above",
        annotation=dict(
            bgcolor="rgba(255, 255, 255, 0.85)",
            bordercolor="#D9E4EC",
            borderpad=3,
            yshift=-15
        )
    )
        
        # 4. Cập nhật đường lưới cho tất cả các facet ngang/dọc
        fig1.update_xaxes(gridcolor='#E5EEF3')
        fig1.update_yaxes(gridcolor='#E5EEF3')
        
        st.plotly_chart(fig1, use_container_width=True)
            
    with st.container(border=True):
        # Lấy màu của chất ô nhiễm đang được phân tích (focus_pollutant)
        focus_color = COLOR_MAP.get(focus_pollutant, '#4F6B7A') 
        
        fig3 = px.box(
            df_daily,
            x='Location',
            y=focus_pollutant,
            # Đã xóa param color='Region' vì theo nguyên tắc 1 biến (chất) chỉ có 1 màu
            title=f"Phân Bố & Mức Độ Biến Động {focus_pollutant}",
            notched=True,
            labels={'Location': 'Trạm quan trắc'}
        )
        
        # Ép toàn bộ các box về đúng màu của chất ô nhiễm đang xét
        fig3.update_traces(marker_color=focus_color)
        
        # Cập nhật giao diện nền chuẩn
        fig3.update_layout(
            plot_bgcolor='#FFFFFF',
            xaxis=dict(gridcolor='#E5EEF3'),
            yaxis=dict(gridcolor='#E5EEF3')
        )
        
        if threshold > 0:
            fig3.add_hline(
                y=threshold, 
                line_dash="dash", 
                line_color="#D98E04", 
                annotation_text="Ngưỡng WHO", 
                annotation_position="top right", 
                layer="above",
                # Cấu hình chi tiết cho phần annotation (text)
                annotation=dict(
                    bgcolor="rgba(255, 255, 255, 0.85)", # Nền trắng hơi trong suốt
                    bordercolor="#D9E4EC",               # Viền nhẹ để tách biệt
                    borderpad=3,                         # Khoảng cách từ chữ đến viền
                    yshift=15                            # Đẩy text dịch lên trên 15 pixel
                )
            )
            
        st.plotly_chart(fig3, use_container_width=True)

        render_section_header("Insight Thuần Dữ Liệu")

        # Insight 1: Dominant Pollutant (Facet Bar)
        dominant_insight = (
            "<b>Phân hóa theo khu vực (Facet Bar):</b> Hồ sơ ô nhiễm phân hóa rõ theo đặc trưng khu vực: "
            "PM2.5 là chất chiếm tỷ trọng cao nhất tại khu Dân cư (162% WHO) và Công nghiệp (137% WHO). "
            "O3 chiếm ưu thế tại khu Giao thông (137%) và Nền đô thị (133%). "
            "Không có khu vực nào có trạng thái an toàn ở mức toàn diện."
        )

        # Insight 2: Volatility (Box Plot)
        q1 = df_daily.groupby('Location')[focus_pollutant].quantile(0.25)
        q3 = df_daily.groupby('Location')[focus_pollutant].quantile(0.75)
        iqr = q3 - q1
        if not iqr.empty:
            max_iqr_station = iqr.idxmax()
            max_iqr_val = iqr.max()
            min_iqr_val = iqr.min()
            
            if focus_pollutant == 'PM2.5':
                boxplot_insight = (
                    "<b>Độ biến động (Box plot):</b> KCN Tân Bình có IQR lớn nhất (14.6 µg/m³) — gấp hơn 2 lần Quận 3 (7.2 µg/m³) — "
                    "cho thấy mức độ biến động ngày rất cao, phù hợp với tính chất hoạt động công nghiệp không đều. "
                    "Thanh Đa dù có median cao nhất (24.3 µg/m³) nhưng IQR chỉ 13.6 µg/m³, nghĩa là ô nhiễm cao và ổn định — "
                    "mức nền cao liên tục chứ không phải đột biến ngắn hạn."
                )
            else:
                ratio = (max_iqr_val / min_iqr_val) if min_iqr_val > 0 else 0
                boxplot_insight = (
                    f"<b>Độ biến động (Box plot):</b> Trạm <b>{max_iqr_station}</b> có biên độ dao động nồng độ (IQR) lớn nhất ({max_iqr_val:.1f} µg/m³), "
                    f"gấp {ratio:.1f} lần so với trạm có biến động nhỏ nhất."
                )
        else:
            boxplot_insight = ""

        render_insight_box([dominant_insight, boxplot_insight])

        st.markdown("---")
        render_section_header("Ô Nhiễm Đa Chiều Theo Trạm Thấp nhất - Cao nhất (% WHO)")

        col_radar_title, col_radar_toggle = st.columns([7, 3])
        with col_radar_toggle:
            auto_scale = st.toggle(
                "Mở rộng trục (Auto-Scale)", 
                value=False, 
                help="Tắt: Ép trục ở mức 200% để hình dáng không bị bẹp. Bật: Scale theo tỷ lệ thực tế cao nhất."
            )

        categories = ['PM2.5', 'TSP', 'CO', 'O3']
        thresholds_radar = THRESHOLDS

        fig_radar = go.Figure()

        # Thêm đường Red Line 100% (Ngưỡng WHO)
        fig_radar.add_trace(go.Scatterpolar(
            r=[100] * len(categories) + [100],
            theta=categories + [categories[0]],
            mode='lines',
            line=dict(color='red', dash='dash', width=2),
            name='Ngưỡng WHO (100%)',
            hoverinfo='none'
        ))

        # Chỉ hiển thị 2 trạm: Tồi tệ nhất và Tốt nhất (dựa trên focus_pollutant)
        worst_station_row = map_data.loc[map_data[focus_pollutant].idxmax()]
        best_station_row = map_data.loc[map_data[focus_pollutant].idxmin()]
        stations_to_plot = [worst_station_row]
        if worst_station_row['Station_No'] != best_station_row['Station_No']:
            stations_to_plot.append(best_station_row)

        total_risk_worst = 0
        total_risk_best = 0

        for row in stations_to_plot:
            station_df = df_daily[df_daily['Station_No'] == row['Station_No']]
            values = []
            uncapped_values = []
            for p in categories:
                v = station_df[p].median()
                val_perc = (v / thresholds_radar.get(p, 1)) * 100 if pd.notna(v) else 0
                uncapped_values.append(val_perc)
                
                capped_val = val_perc if auto_scale else min(val_perc, 200)
                values.append(capped_val)
                
                if not auto_scale and val_perc > 200:
                    fig_radar.add_trace(go.Scatterpolar(
                        r=[200],
                        theta=[p],
                        mode='text',
                        text=[f" ⚠️ {val_perc:.0f}% "],
                        textposition="top right",
                        textfont=dict(color="#E63946", size=15, weight="bold"),
                        showlegend=False,
                        hoverinfo='none'
                    ))
                    
            if row['Station_No'] == worst_station_row['Station_No']:
                total_risk_worst = sum(uncapped_values)
            if row['Station_No'] == best_station_row['Station_No']:
                total_risk_best = sum(uncapped_values)
            
            # Worst station = Reddish, Best station = Blueish
            color = '#B23A2F' if row['Station_No'] == worst_station_row['Station_No'] else '#2B7BBB'
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name=f"Trạm {row['Location']} ({row['Region']})",
                line=dict(color=color),
                opacity=0.6
            ))

        radialaxis_dict = dict(visible=True)
        if not auto_scale:
            radialaxis_dict['range'] = [0, 200]

        fig_radar.update_layout(
            polar=dict(radialaxis=radialaxis_dict),
            margin=dict(t=30, b=30, l=30, r=30)
        )


        st.plotly_chart(fig_radar, use_container_width=True)

        # Gọi hệ thống insight 3 tầng mới
        render_radar_insight(worst_station_row, best_station_row, df_daily, focus_pollutant)

        # Pre-processing
        df_filtered['Hour'] = pd.to_numeric(df_filtered['Hour'], errors='coerce')
        df_filtered['Day_Night'] = df_filtered['Hour'].apply(lambda x: 'Ngày (6h-18h)' if 6 <= x < 18 else 'Đêm (18h-6h)')
        df_dn_daily = df_filtered.groupby(['Location', 'Date_only', 'Day_Night'])[focus_pollutant].mean().reset_index()
        df_dn = df_dn_daily.groupby(['Location', 'Day_Night'])[focus_pollutant].median().reset_index()
        df_dn_pivot = df_dn.pivot(index='Location', columns='Day_Night', values=focus_pollutant).reset_index()

        fig_a = go.Figure()
        night_higher_stations = []

        for i, row in df_dn_pivot.iterrows():
            day_val = row.get('Ngày (6h-18h)', 0)
            night_val = row.get('Đêm (18h-6h)', 0)
            loc = row['Location']
            
            # Highlight Box cho Surprise Insight
            if night_val > day_val:
                night_higher_stations.append(f"**{loc}**")
                fig_a.add_shape(
                    type="rect",
                    x0=day_val - (day_val * 0.05) if day_val > 0 else 0,
                    y0=i - 0.4,
                    x1=night_val + (night_val * 0.05),
                    y1=i + 0.4,
                    line=dict(color="#E63946", width=2, dash="dot"),
                    fillcolor="rgba(230, 57, 70, 0.1)",
                    layer="below"
                )
                fig_a.add_annotation(
                    x=night_val + (night_val * 0.05),
                    y=i,
                    text="⚠️ Đêm > Ngày",
                    showarrow=False,
                    font=dict(color="#E63946", size=11, weight="bold"),
                    xanchor="left"
                )

            fig_a.add_trace(go.Scatter(
                x=[night_val, day_val],
                y=[loc, loc],
                mode='markers+lines',
                line=dict(color='gray', width=2),
                showlegend=False
            ))
            fig_a.add_trace(go.Scatter(
                x=[day_val],
                y=[loc],
                mode='markers',
                marker=dict(color='#FFB703', size=14, symbol='circle'),
                name='Ngày (6h-18h)' if i == 0 else "",
                showlegend=True if i == 0 else False
            ))
            fig_a.add_trace(go.Scatter(
                x=[night_val],
                y=[loc],
                mode='markers',
                marker=dict(color='#2B7BBB', size=14, symbol='diamond'),
                name='Đêm (18h-6h)' if i == 0 else "",
                showlegend=True if i == 0 else False
            ))

        fig_a.update_layout(
            title="Chênh lệch Nồng độ Trung vị: Ban Ngày vs Ban Đêm", 
            xaxis_title=f"{focus_pollutant} (µg/m³)",
            yaxis_title="",
            height=400,
            margin=dict(t=50, b=30, l=10, r=10)
        )
        if threshold > 0:
            fig_a.add_vline(
                x=threshold, 
                line_dash="dash", 
                line_color="#E63946", 
                annotation_text="Ngưỡng WHO", 
                annotation_position="top right", 
                layer="above",
                annotation=dict(
                    bgcolor="rgba(255, 255, 255, 0.85)",
                    bordercolor="#D9E4EC",
                    borderpad=3,
                    yshift=15
                )
            )

        with st.container(border=True):
            st.subheader(f"Khám Phá Nghịch Lý Ngày & Đêm ({focus_pollutant})")
            st.plotly_chart(fig_a, use_container_width=True)
            
            # Display Text Insight
            if focus_pollutant in ['PM2.5', 'O3']:
                render_insight_box([
                    "<b>PM2.5:</b> Chỉ 2/6 trạm có nồng độ đêm cao hơn ngày (KCN Tân Bình, ĐHQG Hồ Chí Minh). 4 trạm còn lại tuân theo quy luật ngày > đêm, nhất quán với nguồn phát thải giao thông.",
                    "<b>O3:</b> 4/6 trạm có O3 đêm cao hơn ngày, phản ánh sự tích lũy O3 kéo dài sau khi quá trình quang hóa ban ngày dừng."
                ], title="Chu kỳ Ngày / Đêm (Đặc trưng PM2.5 & O3)", icon_name="trend")
            elif night_higher_stations:
                render_insight_box([
                    f"Dữ liệu cho thấy trạm {', '.join(night_higher_stations)} có nồng độ <b>{focus_pollutant}</b> trung vị ban đêm (18h-6h) CAO HƠN ban ngày (6h-18h)."
                ], title="Insight thú vị", icon_name="trend")
            else:
                render_insight_box([
                    f"100% các trạm trong khoảng lọc đều tuân theo quy luật nồng độ <b>{focus_pollutant}</b> ban ngày cao hơn ban đêm."
                ], title="Dữ liệu xu hướng", icon_name="trend")

        st.markdown("---")
        st.markdown(f"### {get_icon_html('insight')} Kết luận", unsafe_allow_html=True)

        def render_conclusion_internal():
            content_html = f"""
                <h3 style="margin-top:0; color:#1F8A70;">
                    Phân bố không gian ô nhiễm tại TPHCM có sự phân hóa rõ rệt nhưng không theo chiều hướng thông thường
                </h3>
                <ul style="margin-bottom: 0;">
                    <li>
                        <b>Về PM2.5:</b> Khu <b>Dân cư (Thanh Đa)</b> dẫn đầu toàn mạng với median PM2.5 = <b>24.3 µg/m³ (162% WHO)</b> và <b>82.9% số ngày</b> vượt chuẩn 24h — cao hơn đáng kể so với hai trạm Giao thông (Bình Tân: 16.9 µg/m³, Quận 3: 14.3 µg/m³). Quận 3 là trạm <b>duy nhất</b> có PM2.5 trung vị dưới ngưỡng WHO (96%) và tỷ lệ vượt chuẩn thấp nhất (32.9% số ngày). Khoảng cách tuyệt đối giữa trạm cao nhất và thấp nhất là <b>9.95 µg/m³</b>.
                    </li>
                    <li>
                        <b>Về O3:</b> Phân bố không gian <b>ngược chiều hoàn toàn</b> với PM2.5. Bình Tân (Giao thông) dẫn đầu với O3 8h-peak median = <b>138.0 µg/m³ (138% WHO)</b>. Tất cả 6 trạm đều vượt ngưỡng WHO về O3, trong khi Thanh Đa — trạm tệ nhất về PM2.5 — lại là trạm <b>gần ngưỡng nhất</b> về O3 (99.9 µg/m³, 100% WHO).
                    </li>
                    <li>
                        <b>Về biến động nội tại:</b> KCN Tân Bình có IQR PM2.5 lớn nhất (14.6 µg/m³), trong khi Thanh Đa mặc dù có median cao nhất nhưng biến động thấp hơn (IQR = 13.6 µg/m³) — mức ô nhiễm cao nhưng liên tục, không phải theo đợt.
                    </li>
                    <li>
                        <b>Về chu kỳ ngày-đêm:</b> 4/6 trạm có PM2.5 cao hơn ban ngày. 2 trạm ngoại lệ (KCN Tân Bình và ĐHQG Hồ Chí Minh) có PM2.5 đêm cao hơn ngày với biên độ nhỏ (0.6–1.2 µg/m³). Đối với O3, 4/6 trạm đều có O3 cao hơn vào ban ngày.
                    </li>
                    <li>
                        <b>Hệ quả cho can thiệp theo không gian:</b> Không tồn tại một chiến lược đơn lẻ phù hợp với toàn bộ 6 trạm. Nếu ưu tiên PM2.5, Thanh Đa cần can thiệp trước. Nếu ưu tiên O3, Bình Tân và ĐHQG Hồ Chí Minh cần ưu tiên. Nếu ưu tiên tính ổn định cao của mức ô nhiễm (không phải đỉnh ngắn hạn), Thanh Đa vẫn là đối tượng quan trọng nhất.
                    </li>
                </ul>
            """
            render_conclusion_box(content_html, accent_color="#1F8A70")
        render_conclusion_internal()

if __name__ == "__main__":
    main()
