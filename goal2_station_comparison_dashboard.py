import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title="Phân Phối Không Gian - HCMC Air Quality",
    page_icon="🗺️",
    layout="wide"
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

try:
    with st.spinner("Đang tải dữ liệu..."):
        df, stations_meta = load_data()
except Exception as e:
    st.error(f"Lỗi khi tải dữ liệu: {e}")
    st.stop()

st.title("🗺️ Phân Bố Không Gian Ô Nhiễm Không Khí TPHCM")
st.markdown("*Phân tích sự khác biệt nồng độ ô nhiễm giữa các khu vực đặc trưng*")
st.markdown("---")

# ============= MAIN FILTERS =============
with st.expander("🎛️ BỘ LỌC VÀ TÙY CHỈNH DỮ LIỆU (Filters & Controls)", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_min = df['Date'].min().date()
        date_max = df['Date'].max().date()
        selected_dates = st.date_input(
            "📅 Khoảng thời gian",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max
        )
        pollutants = ['PM2.5', 'TSP', 'O3', 'CO', 'NO2', 'SO2']
        focus_pollutant = st.selectbox("🎯 Chất ô nhiễm chính", options=pollutants, index=0)
        
    with col2:
        station_opts = [f"Trạm {r['Station_No']} - {r['Location']}" for _, r in stations_meta.iterrows()]
        selected_stations_raw = st.multiselect(
            "🗺️ Trạm quan trắc",
            options=station_opts,
            default=station_opts
        )
        selected_station_ids = [int(s.split(" ")[1]) for s in selected_stations_raw]
        
        # Consistent threshold based on pollutant
        threshold_vals = {"PM2.5": 15.0, "TSP": 50.0, "CO": 10000.0, "O3": 100.0, "SO2": 40.0, "NO2": 40.0}
        threshold = st.number_input(f"Ngưỡng WHO (µg/m³)", value=threshold_vals.get(focus_pollutant, 50.0))
        
    with col3:
        region_opts = stations_meta['Region'].unique().tolist()
        selected_regions = st.multiselect(
            "🏙️ Loại khu vực",
            options=region_opts,
            default=region_opts
        )

# ============= FILTER DATA =============
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
else:
    df_filtered = df.copy()

df_filtered = df_filtered[
    (df_filtered['Station_No'].isin(selected_station_ids)) &
    (df_filtered['Region'].isin(selected_regions))
]

# Apply data cleaning flag check
flag_col = f"{focus_pollutant}_flag"
if flag_col in df_filtered.columns:
    df_filtered = df_filtered[df_filtered[flag_col] == 0]

st.markdown("<br>", unsafe_allow_html=True)
st.warning("⚠️ **Cảnh báo chất lượng dữ liệu:** Dữ liệu NO2 và SO2 tại Trạm 5 (Quận 3) có dấu hiệu phân phối bất thường (drift thiết bị đo, median SO2 vượt xa ngưỡng tự nhiên). Cần thận trọng khi diễn giải biểu đồ liên quan đến trạm này.")

# ============= LAYER 2: SPATIAL OVERVIEW =============
if df_filtered.empty:
    st.warning("Không có dữ liệu thỏa mãn bộ lọc hiện tại.")
    st.stop()

# Aggregates for Map
map_data = df_filtered.groupby(['Station_No', 'Location', 'Lat', 'Lon', 'Region'])[focus_pollutant].mean().reset_index()
map_data = map_data.dropna(subset=[focus_pollutant])

# KPI CARDS SECTION (5 cards as per proposal.md)
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    worst_station = map_data.loc[map_data[focus_pollutant].idxmax()]
    st.metric(
        label=f"🏭 Trạm cao nhất ({focus_pollutant})",
        value=f"Trạm {worst_station['Station_No']}",
        delta=f"{worst_station[focus_pollutant]:.1f} µg/m³",
        delta_color="inverse"
    )

with kpi2:
    # Mean of focus pollutant across network
    flag_col = f"{focus_pollutant}_flag"
    if flag_col in df.columns:
        df_network = df[df[flag_col] == 0]
    else:
        df_network = df
    network_mean = df_network[focus_pollutant].mean()
    
    st.metric(
        label=f"🌐 Trung bình toàn mạng",
        value=f"{network_mean:.1f} µg/m³",
        delta=f"Toàn TPHCM",
        delta_color="off"
    )

with kpi3:
    best_station = map_data.loc[map_data[focus_pollutant].idxmin()]
    diff = worst_station[focus_pollutant] - best_station[focus_pollutant]
    st.metric(
        label="📊 Chênh lệch Max-Min",
        value=f"{diff:.1f} µg/m³",
        delta=f"Min: {best_station[focus_pollutant]:.1f}",
        delta_color="off"
    )

with kpi4:
    n_exceed = (map_data[focus_pollutant] > threshold).sum()
    st.metric(
        label="⚠️ Vượt chuẩn WHO",
        value=f"{n_exceed}/{len(map_data)} trạm",
        delta=f"{(n_exceed/max(1, len(map_data)))*100:.0f}%",
        delta_color="inverse"
    )

with kpi5:
    st.metric(
        label="📋 Dữ liệu hiển thị",
        value=f"{len(df_filtered):,}",
        delta="bản ghi"
    )

st.markdown("---")

col_map, col_info = st.columns([7, 3])

with col_map:
    st.subheader(f"Bản Đồ Phân Bố {focus_pollutant}")
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
    st.subheader("💡 Điểm Nóng Không Gian")
    st.markdown(f"**Trạm {worst_station['Location']} ({worst_station['Region']})** đang là điểm nóng nhất về **{focus_pollutant}** ({worst_station[focus_pollutant]:.1f} µg/m³).")
    
    # Dynamic insight based on pollutant type
    if focus_pollutant in ['PM2.5', 'TSP', 'SO2']:
        st.info(
            f"📌 **Gợi ý phân tích (Nhóm hạt lơ lửng & Khí bền):**\n\n"
            f"- **Tính phân tán:** {focus_pollutant} có khả năng phát tán xa theo chiều gió.\n"
            f"- Nếu mức chênh lệch (Max-Min = {diff:.1f}) giữa các trạm tương đối nhỏ, chứng tỏ ô nhiễm là vấn đề vùng (regional). Ngược lại, mức chênh lệch lớn này chỉ ra có nguồn xả thải cực mạnh ngay tại **{worst_station['Region']}**."
        )
    else:
        st.info(
            f"📌 **Gợi ý phân tích (Nhóm khí phản ứng nhanh):**\n\n"
            f"- **Đặc tính cục bộ:** Các khí như {focus_pollutant} thường suy giảm rất nhanh theo khoảng cách tính từ nguồn phát.\n"
            f"- Mức độ ô nhiễm cao tại **{worst_station['Location']}** phản ánh chính xác nguồn phát thải sơ cấp (mật độ xe/nhà máy) ngay tại tọa độ đó, hoặc là hệ quả của phản ứng quang hóa mạnh (như trường hợp O3)."
        )

st.markdown("---")

# ============= LAYER 3: ANALYTICAL DEEP DIVE =============
st.header("🔬 Phân Tích Sâu Đa Chiều")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # Tính mean cho từng chất sau khi lọc flag == 0
    pollutants_to_plot = ['PM2.5', 'TSP', 'CO', 'NO2', 'O3', 'SO2']
    valid_pollutants = [p for p in pollutants_to_plot if p in df_filtered.columns]
    
    mean_data = []
    for region in df_filtered['Region'].unique():
        region_data = {'Region': region}
        df_r = df_filtered[df_filtered['Region'] == region]
        for p in valid_pollutants:
            flag_col = f"{p}_flag"
            if flag_col in df_r.columns:
                val = df_r[df_r[flag_col] == 0][p].mean()
            else:
                val = df_r[p].mean()
            region_data[p] = val
        mean_data.append(region_data)
        
    df_region = pd.DataFrame(mean_data)
    cols_to_melt = valid_pollutants
    df_region_melt = df_region.melt(id_vars='Region', value_vars=cols_to_melt, var_name='Pollutant', value_name='Concentration')
    
    # Chuẩn hóa về % so với ngưỡng WHO để khắc phục lệch scale (CO quá lớn)
    thresholds = {"PM2.5": 15.0, "TSP": 50.0, "CO": 10000.0, "O3": 100.0, "SO2": 40.0, "NO2": 40.0}
    df_region_melt['Percent_WHO'] = df_region_melt.apply(
        lambda row: (row['Concentration'] / thresholds.get(row['Pollutant'], 1)) * 100, axis=1
    )
    
    fig1 = px.bar(
        df_region_melt,
        x='Region',
        y='Percent_WHO',
        color='Pollutant',
        barmode='group',
        color_discrete_map={
            'PM2.5': '#B23A2F', 
            'TSP': '#6F1D1B', 
            'O3': '#1F8A70', 
            'CO': '#4E5D8A', 
            'NO2': '#D98E04', 
            'SO2': '#2B7BBB'
        },
        title="Mức Độ Ô Nhiễm So Với Ngưỡng WHO (%)",
        labels={'Region': 'Khu vực', 'Percent_WHO': '% so với ngưỡng WHO', 'Pollutant': 'Chất ô nhiễm'},
        hover_data={'Concentration': ':.1f'}
    )
    fig1.add_hline(y=100, line_dash="dash", line_color="#FFB703", annotation_text="Ngưỡng WHO (100%)")
    st.plotly_chart(fig1, use_container_width=True)
    
with col_chart2:
    fig3 = px.box(
        df_filtered,
        x='Location',
        y=focus_pollutant,
        color='Region',
        title=f"Phân Bố & Mức Độ Biến Động {focus_pollutant}",
        notched=True,
        labels={'Location': 'Trạm quan trắc', 'Region': 'Loại khu vực'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    if threshold > 0:
        fig3.add_hline(y=threshold, line_dash="dash", line_color="#FFB703", annotation_text="Ngưỡng WHO")
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("#### 💡 Insight Phân Bố & Biến Động")

# Dynamic Insight for Dominant Pollutant (Bar Chart)
dominant_pollutant = ""
dominant_region = ""
if not df_region_melt.empty and not df_region_melt['Percent_WHO'].isna().all():
    max_idx = df_region_melt['Percent_WHO'].idxmax()
    dominant_pollutant = df_region_melt.loc[max_idx, 'Pollutant']
    dominant_region = df_region_melt.loc[max_idx, 'Region']

dominant_insight = (
    f"📌 **Đánh giá rủi ro (Chất chi phối):** Dựa vào tỷ lệ % WHO trên dữ liệu đã lọc, "
    f"chất chi phối rủi ro sức khỏe chính là **{dominant_pollutant}** tại khu vực **{dominant_region}**. "
    f"Điều này phản ánh sự khác biệt về nguồn phát thải (ví dụ: PM2.5/NO2 từ đốt cháy tại Giao thông/Công nghiệp, hay O3 từ quang hóa tại Nền đô thị)."
)

# Dynamic Insight for Box Plot
if focus_pollutant in ['PM2.5', 'CO', 'NO2']:
    boxplot_insight = (
        f"📌 **Mô hình xả thải ({focus_pollutant}):** Box plot phản ánh chu kỳ hoạt động đặc thù. "
        "Hộp (IQR) rộng biểu thị khu vực chịu tác động mạnh của chu kỳ xả thải theo pha (ví dụ: kẹt xe giờ cao điểm). "
        "Các điểm ngoại lai (outliers) là tín hiệu cảnh báo các đợt ùn tắc cục bộ hoặc sự kiện xả thải cấp tính bất thường."
    )
elif focus_pollutant == 'O3':
    boxplot_insight = (
        f"📌 **Mô hình xả thải (O3):** Sự phân tán (độ rộng IQR) của O3 phụ thuộc chặt chẽ vào chu kỳ bức xạ mặt trời trong ngày thay vì xả thải trực tiếp. "
        "Các điểm ngoại lai (outliers) phía trên thường là dấu vết của những ngày nắng nóng gay gắt kéo dài, kích thích phản ứng quang hóa."
    )
else:
    boxplot_insight = (
        f"📌 **Mô hình xả thải ({focus_pollutant}):** Độ rộng của hộp (IQR) cho biết mức độ dao động nồng độ. "
        "Hộp hẹp nghĩa là mức nền ô nhiễm tĩnh, tích tụ đều đặn. Hộp rộng và nhiều Outliers là dấu hiệu của sự gián đoạn trong mô hình xả thải hoặc thời tiết."
    )

st.info(dominant_insight + "\n\n" + boxplot_insight)

st.subheader(f"🔥 Diễn Biến {focus_pollutant} Theo Thời Gian")
df_filtered['Month_Year'] = df_filtered['Date'].dt.to_period('M').astype(str)
df_timespace = df_filtered.groupby(['Month_Year', 'Location'])[focus_pollutant].mean().reset_index()

if len(df_timespace['Month_Year'].unique()) > 1:
    fig_heat = px.density_heatmap(
        df_timespace,
        x='Month_Year',
        y='Location',
        z=focus_pollutant,
        color_continuous_scale="Reds",
        labels={'Month_Year': 'Tháng/Năm', 'Location': 'Trạm quan trắc', focus_pollutant: 'Nồng độ'}
    )
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    df_filtered['Day'] = df_filtered['Date'].dt.date.astype(str)
    df_timespace_day = df_filtered.groupby(['Day', 'Location'])[focus_pollutant].mean().reset_index()
    if len(df_timespace_day['Day'].unique()) > 1:
        fig_heat = px.density_heatmap(
            df_timespace_day,
            x='Day',
            y='Location',
            z=focus_pollutant,
            color_continuous_scale="Reds",
            labels={'Day': 'Ngày', 'Location': 'Trạm quan trắc', focus_pollutant: 'Nồng độ'}
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("🕒 Vui lòng chọn khoảng thời gian lớn hơn 1 ngày để xem Heatmap Diễn biến.")

st.info(
    f"📌 **Bóc tách Vĩ mô và Vi mô qua Heatmap ({focus_pollutant}):**\n\n"
    f"- **Đồng bộ (Trục dọc sậm màu):** Nếu nhiều trạm cùng sậm màu vào một thời điểm, tác nhân chi phối là **Vĩ mô** (ví dụ: bước vào mùa khô, nghịch nhiệt diện rộng khóa chặt ô nhiễm).\n"
    f"- **Cục bộ (Trục ngang sậm màu):** Nếu chỉ 1 trạm sậm màu kéo dài trong khi các trạm khác sạch, tác nhân là **Vi mô** (ví dụ: công trình xây dựng mới, thay đổi luồng giao thông quanh trạm đó)."
)

st.markdown("---")
st.caption("Dữ liệu đã được xử lý missing theo time interpolation theo từng trạm; giữ outlier; hiệu chỉnh bất nhất PM2.5 > TSP theo tỷ lệ PM2.5/TSP tham chiếu.")

def render_conclusion():
    st.markdown("### 💡 Kết luận: Bài toán Quy hoạch & Quản lý Không gian")
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #F0F4F8 0%, #E2E8F0 100%);
            border-left: 5px solid #2B7BBB;
            border-radius: 8px;
            padding: 24px 28px;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #1E293B;
            line-height: 1.8;
            margin-bottom: 2rem;
            margin-top: 1rem;
        ">
            <h4 style="margin-top:0; color:#0F172A;">
                🏙️ Không gian ô nhiễm có tính phân mảnh cao — Đòi hỏi giải pháp cục bộ
            </h4>
            <ul style="margin-bottom: 0;">
                <li>
                    <b>PM2.5 và Nguồn phát thải</b>: Dữ liệu thực tế cho thấy khu <i>Dân cư (Thanh Đa)</i> lại là điểm nóng về PM2.5 cao nhất toàn mạng, vượt qua cả các khu Giao thông hay Công nghiệp. Điều này cho thấy rủi ro phơi nhiễm bụi mịn cực kỳ nghiêm trọng ngay tại nơi sinh sống.
                </li>
                <li>
                    <b>Nghịch lý O3 và NO2</b>: Trạm <i>Giao thông (Bình Tân)</i> ghi nhận nồng độ O3 cao nhất, trong khi <i>Nền đô thị (Linh Trung)</i> có NO2 cao nhất. Tương quan NO2 - O3 tại TP.HCM là thuận chiều (positive correlation), phản ánh sự tích lũy và chuyển hóa quang hóa đồng thời dưới tác động của bức xạ mặt trời vào ban ngày.
                </li>
                <li>
                    <b>Hệ quả cho chính sách</b>: Các biện pháp kiểm soát cần thiết kế <i>chuyên biệt cho từng cụm không gian</i> (Zoning). Không thể áp chuẩn chung khi mà khu Dân cư đối mặt với PM2.5, còn khu Giao thông lại vật lộn với bức xạ O3.
                </li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

render_conclusion()
