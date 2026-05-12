import pandas as pd
import plotly.express as px

# Đọc dữ liệu
df = pd.read_csv('data/cleaned/Air_Quality_HCMC_Cleaned.csv')

# Metadata trạm
stations_meta = pd.DataFrame([
    {'Station_No': 1, 'Location': 'VNU Ho Chi Minh', 'Region': 'Urban background', 'Lat': 10.8699, 'Lon': 106.7960},
    {'Station_No': 2, 'Location': 'Binh Tan', 'Region': 'Traffic', 'Lat': 10.7410, 'Lon': 106.6171},
    {'Station_No': 3, 'Location': 'Tan Binh IP', 'Region': 'Industry', 'Lat': 10.8162, 'Lon': 106.6204},
    {'Station_No': 4, 'Location': 'Thanh Da', 'Region': 'Residential', 'Lat': 10.8158, 'Lon': 106.7174},
    {'Station_No': 5, 'Location': 'District 3', 'Region': 'Traffic', 'Lat': 10.7764, 'Lon': 106.6878},
    {'Station_No': 6, 'Location': 'District 10', 'Region': 'Traffic + Residential', 'Lat': 10.7805, 'Lon': 106.6595}
])

# Lọc dữ liệu năm 2022
df['Date'] = pd.to_datetime(df['Date'])
df_2022 = df[df['Date'].dt.year == 2022].copy()

# Lọc bỏ dữ liệu lỗi (flag > 1) cho PM2.5
df_clean = df_2022[df_2022['PM2.5_flag'] <= 1].copy()

# Tính trung bình PM2.5 theo ngày và trạm
df_daily = df_clean.groupby(['Date', 'Station_No'])['PM2.5'].mean().reset_index()

# Merge với metadata để lấy tên trạm
df_daily = df_daily.merge(stations_meta, on='Station_No')

# Tạo biểu đồ Dumbbell so sánh khoảng giá trị PM2.5 giữa các trạm
fig = px.box(df_daily, x='Location', y='PM2.5', color='Location',
             title='Phân bổ PM2.5 tại các trạm năm 2022 (µg/m³)',
             labels={'PM2.5': 'Nồng độ PM2.5 (µg/m³)'})

# Thêm đường ngưỡng WHO 2021
fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="WHO 2021 (15 µg/m³)")
fig.show()