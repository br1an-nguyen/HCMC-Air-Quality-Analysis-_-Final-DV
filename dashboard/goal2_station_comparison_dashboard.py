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
        {'Station_No': 1, 'Region': 'Nền đô thị', 'Lat': 10.8699, 'Lon': 106.7960, 'Location': 'ĐHQG Linh Trung'},
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
    pollutants = ['PM2.5', 'TSP', 'O3', 'CO', 'NO2', 'SO2']
    focus_pollutant = st.selectbox("Chất ô nhiễm chính", options=pollutants, index=0)

    threshold_defaults = {'PM2.5': 15.0, 'TSP': 150.0, 'CO': 4000.0, 'O3': 100.0, 'SO2': 40.0, 'NO2': 25.0}
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
    df_filtered = df[
        (df['Date'] >= pd.Timestamp(start_date)) &
        (df['Date'] <= pd.Timestamp(end_date))
    ]

    df_filtered = df_filtered[
        (df_filtered['Station_No'].isin(selected_station_ids)) &
        (df_filtered['Region'].isin(selected_regions))
    ]

    # Apply data cleaning flag check
    pollutants_all = ['PM2.5', 'TSP', 'CO', 'NO2', 'O3', 'SO2']
    for p in pollutants_all:
        flag_col = f"{p}_flag"
        if flag_col in df_filtered.columns:
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
            delta=f"-{worst_station[focus_pollutant]:.1f} µg/m³", # Dấu - để hiện màu đỏ (ẩn bằng CSS)
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
            delta=f"-{worst_pct:.1f}% số ngày", # Dấu - để hiện màu đỏ
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
        fig_rank.add_vline(x=threshold, line_dash="dash", line_color="#E63946", annotation_text="Ngưỡng WHO", annotation_position="top right", layer="above")
    st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown("---")

    # ============= LAYER 3: ANALYTICAL DEEP DIVE =============
    render_section_header("Phân Tích Sâu Đa Chiều")

    with st.container(border=True):
        # Tính median cho từng chất sau khi lọc flag == 0
        pollutants_to_plot = ['PM2.5', 'TSP', 'CO', 'NO2', 'O3', 'SO2']
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
        
        # Highlight highest bar in each region
        ANOMALY_POLLUTANTS = ['SO2', 'NO2']
        df_region_melt['Is_Max'] = df_region_melt.groupby('Region').apply(
            lambda g: g['Percent_WHO'] == g[~g['Pollutant'].isin(ANOMALY_POLLUTANTS)]['Percent_WHO'].max()
        ).reset_index(level=0, drop=True)
        df_region_melt['Color_Group'] = df_region_melt['Is_Max'].map({True: 'Cao nhất', False: 'Khác'})
        
        fig1 = px.bar(
            df_region_melt,
            x='Percent_WHO',
            y='Pollutant',
            facet_col='Region',
            facet_col_wrap=2,
            color='Color_Group',
            color_discrete_map={'Cao nhất': '#B23A2F', 'Khác': '#94A3B8'},
            orientation='h',
            title="Hồ Sơ Ô Nhiễm Theo Khu Vực (% WHO)<br><sup>Lưu ý: Các trạm trong cùng khu vực đã được gộp (pooling) lấy median</sup>",
            labels={'Percent_WHO': '% WHO', 'Pollutant': ''},
            hover_data={'Concentration': ':.1f'}
        )
        fig1.update_layout(
            showlegend=False,
            height=700,
            margin=dict(t=50, b=30, l=30, r=30)
        )
        fig1.add_vline(x=100, line_dash="dash", line_color="#E63946", annotation_text="100% WHO", annotation_position="top right", layer="above")
        st.plotly_chart(fig1, use_container_width=True)
        
    with st.container(border=True):
        fig3 = px.box(
            df_daily,
            x='Location',
            y=focus_pollutant,
            color='Region',
            title=f"Phân Bố & Mức Độ Biến Động {focus_pollutant}",
            notched=True,
            labels={'Location': 'Trạm quan trắc', 'Region': 'Loại khu vực'},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        if threshold > 0:
            fig3.add_hline(y=threshold, line_dash="dash", line_color="#E63946", annotation_text="Ngưỡng WHO", annotation_position="top right", layer="above")
        st.plotly_chart(fig3, use_container_width=True)

    render_section_header("Insight Thuần Dữ Liệu")

    # Insight 1: Dominant Pollutant (Facet Bar)
    dominant_insight = (
        "<b>Phân hóa theo khu vực (Facet Bar):</b> Hồ sơ ô nhiễm phân hóa rõ theo đặc trưng khu vực (đã loại SO2/NO2 do anomaly thiết bị): "
        "PM2.5 là chất chiếm tỷ trọng cao nhất tại khu Dân cư (162% WHO) và Công nghiệp (137% WHO). "
        "O3 chiếm ưu thế tại khu Giao thông (137%) và Nền đô thị (133%). Không có khu vực nào có hồ sơ an toàn toàn diện."
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
                "<b>Độ biến động (Box plot):</b> KCN Tân Bình có IQR lớn nhất (14.6 µg/m³) — gấp 2.0 lần Quận 3 (7.2 µg/m³) — "
                "cho thấy mức độ biến động ngày rất cao, phù hợp với tính chất hoạt động công nghiệp không đều. "
                "Thanh Đa dù có median cao nhất (24.3 µg/m³) nhưng IQR chỉ 13.6 µg/m³, nghĩa là ô nhiễm cao và ổn định — "
                "mức nền cao liên tục chứ không phải spike ngắn hạn."
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
    render_section_header("Profile Ô Nhiễm Đa Chiều Theo Trạm (% WHO)")

    col_radar_title, col_radar_toggle = st.columns([7, 3])
    with col_radar_toggle:
        auto_scale = st.toggle(
            "Mở rộng trục (Auto-Scale)", 
            value=False, 
            help="Tắt: Ép trục ở mức 200% để hình dáng không bị bẹp. Bật: Scale theo tỷ lệ thực tế cao nhất."
        )

    # Gom nhóm các chất: Bụi (PM2.5, TSP) -> Khí đặc trưng giao thông (NO2, CO) -> Khí đặc trưng CN/quang hóa (SO2, O3)
    categories = ['PM2.5', 'TSP', 'NO2', 'CO', 'SO2', 'O3']
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
    worst_station = map_data.loc[map_data[focus_pollutant].idxmax()]
    best_station = map_data.loc[map_data[focus_pollutant].idxmin()]
    stations_to_plot = [worst_station]
    if worst_station['Station_No'] != best_station['Station_No']:
        stations_to_plot.append(best_station)

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
            
            # Kỹ thuật Cap & Annotate: Ép đỉnh ở 200% nhưng bắn text báo số thật (nếu tắt auto_scale)
            capped_val = val_perc if auto_scale else min(val_perc, 200)
            values.append(capped_val)
            
            if not auto_scale and val_perc > 200:
                fig_radar.add_trace(go.Scatterpolar(
                    r=[200],
                    theta=[p],
                    mode='text',
                    text=[f" ⚠️ {val_perc:.0f}% "],
                    textposition="top right",
                    textfont=dict(color="#E63946", size=11, weight="bold"),
                    showlegend=False,
                    hoverinfo='none'
                ))
                
        if row['Station_No'] == worst_station['Station_No']:
            total_risk_worst = sum(uncapped_values)
        if row['Station_No'] == best_station['Station_No']:
            total_risk_best = sum(uncapped_values)
        
        # Worst station = Reddish, Best station = Blueish
        color = '#B23A2F' if row['Station_No'] == worst_station['Station_No'] else '#2B7BBB'
        
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

    any_capped = any(
        (df_daily[df_daily['Station_No'] == row['Station_No']]['SO2'].median() / thresholds_radar.get('SO2', 40.0) * 100) > 200
        or
        (df_daily[df_daily['Station_No'] == row['Station_No']]['NO2'].median() / thresholds_radar.get('NO2', 25.0) * 100) > 200
        for row in stations_to_plot
    )
    if any_capped:
        st.markdown(
            f"""
            <div style="background-color: #FFF9E6; border-left: 4px solid #FFCC00; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; color: #856404; font-size: 14px;">
                    {get_icon_html("warning")}
                    <span><b>Lưu ý:</b> Một hoặc nhiều trạm trong radar có SO2/NO2 vượt 200% WHO. Đa giác bị ép tại mức 200% nên hình dạng có thể bị xáo trộn.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.plotly_chart(fig_radar, use_container_width=True)

    # Generate Shape Profiling & Axis Dominance Insight
    radar_insights = []
    for row in stations_to_plot:
        station_df = df_daily[df_daily['Station_No'] == row['Station_No']]
        uncapped_values = []
        max_p = ""
        max_val = 0
        for p in categories:
            v = station_df[p].median()
            val_perc = (v / thresholds_radar.get(p, 1)) * 100 if pd.notna(v) else 0
            uncapped_values.append(val_perc)
            if val_perc > max_val:
                max_val = val_perc
                max_p = p
                
        total_risk = sum(uncapped_values)
        if total_risk > 0:
            ratio = (max_val / total_risk) * 100
            radar_insights.append(
                f"<b>Trạm {row['Location']}:</b> Hình đa giác bị kéo lệch mạnh về trục <b>{max_p}</b>, "
                f"chiếm <b>{ratio:.0f}%</b> tổng tỷ trọng đo (đạt mức {max_val:.0f}% WHO)."
            )

    if focus_pollutant == 'PM2.5':
        render_insight_box([
            "Hình đa giác <b>Thanh Đa</b> (worst PM2.5) bị kéo lệch về PM2.5 và TSP — đặc trưng của nguồn bụi thô và mịn từ môi trường sống.",
            "<b>Quận 3</b> (best PM2.5) có hình đa giác nhỏ hơn về PM2.5/TSP, nhưng các trục NO2/SO2 bị ép tại 200% do anomaly thiết bị — không thể diễn giải tin cậy."
        ], title="Hình thái mạng lưới (Shape Profiling)", icon_name="location")
    elif radar_insights:
        render_insight_box(radar_insights, title="Hình thái & Độ lệch tâm", icon_name="location")
    else:
        render_insight_box(["Không đủ dữ liệu để phân tích độ lệch tâm."], title="Phân tích Hình Thái", icon_name="location")

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
            mode='lines',
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
        fig_a.add_vline(x=threshold, line_dash="dash", line_color="#E63946", annotation_text="Ngưỡng WHO", annotation_position="top right", layer="above")

    with st.container(border=True):
        st.subheader(f"Khám Phá Nghịch Lý Ngày & Đêm ({focus_pollutant})")
        st.plotly_chart(fig_a, use_container_width=True)
        
        # Display Text Insight
        if focus_pollutant in ['PM2.5', 'O3']:
            render_insight_box([
                "<b>PM2.5:</b> Chỉ 2/6 trạm có nồng độ đêm cao hơn ngày (KCN Tân Bình, Linh Trung). 4 trạm còn lại tuân theo quy luật ngày > đêm, nhất quán với nguồn phát thải giao thông.",
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
    st.caption("Dữ liệu đã được xử lý missing theo time interpolation theo từng trạm; giữ outlier; hiệu chỉnh bất nhất PM2.5 > TSP theo tỷ lệ PM2.5/TSP tham chiếu.")

    def render_conclusion():
        content_html = f"""
            <h3 style="margin-top:0; color:#0F172A;">
                {get_icon_html("analysis")} Phân bố không gian ô nhiễm tại TPHCM có sự phân hóa rõ rệt nhưng không theo chiều hướng thông thường
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
                    <b>Về chu kỳ ngày-đêm:</b> 4/6 trạm có PM2.5 cao hơn ban ngày, nhất quán với nguồn phát thải giao thông. 2 trạm ngoại lệ (KCN Tân Bình và Linh Trung) có PM2.5 đêm cao hơn ngày với biên độ nhỏ (0.6–1.2 µg/m³).
                </li>
                <li>
                    <b>Hệ quả cho can thiệp theo không gian:</b> Không tồn tại một chiến lược đơn lẻ phù hợp với toàn bộ 6 trạm. Nếu ưu tiên PM2.5, Thanh Đa cần can thiệp trước. Nếu ưu tiên O3, Bình Tân và Linh Trung cần ưu tiên. Nếu ưu tiên tính ổn định cao của mức ô nhiễm (không phải đỉnh ngắn hạn), Thanh Đa vẫn là đối tượng quan trọng nhất. <i>(Lưu ý: Dữ liệu SO2 và NO2 toàn mạng bị loại trừ khỏi phân tích định lượng do anomaly thiết bị đo nghiêm trọng.)</i>
                </li>
            </ul>
        """
        render_conclusion_box(content_html, accent_color="#2B7BBB")
    render_conclusion()

if __name__ == "__main__":
    main()
