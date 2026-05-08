import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load dữ liệu
df = pd.read_csv('data/cleaned/Air_Quality_HCMC_Cleaned.csv')

# Lọc dữ liệu lỗi
df['PM2.5'] = df.apply(lambda row: np.nan if row['PM2.5_flag'] != 0 else row['PM2.5'], axis=1)
df['O3'] = df.apply(lambda row: np.nan if row['O3_flag'] != 0 else row['O3'], axis=1)

# Tính trung bình nồng độ PM2.5 và O3 mỗi ngày
daily_avg = df.groupby('Date')[['PM2.5', 'O3']].mean()

# Vẽ biểu đồ phân tích
plt.figure(figsize=(10,6))
plt.plot(daily_avg['PM2.5'], label='PM2.5')
plt.plot(daily_avg['O3'], label='O3')
plt.xlabel('Ngày')
plt.ylabel('Nồng độ (µg/m³)')
plt.title('Phân tích Nghịch lý PM2.5 & O3')
plt.legend()
plt.show()