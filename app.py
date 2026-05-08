"""
HCMC Air Quality Dashboard — Home Page
Streamlit multipage app: các goal nằm trong thư mục pages/
Chạy: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌫️ HCMC Air Quality Dashboard")
st.markdown(
    """
    Dashboard phân tích chất lượng không khí **TP. Hồ Chí Minh**  
    dựa trên dữ liệu từ **6 trạm quan trắc**, giai đoạn **2021–2022**.

    ---
    | Goal | Nội dung |
    |------|----------|
    | **Goal 1** | Xu hướng PM2.5 theo thời gian, heatmap giờ × tháng, drill-down 24h |
    | **Goal 3** | Tác động của nhiệt độ & độ ẩm đến nồng độ ô nhiễm |
    | **Goal 4** | Tương quan nội bộ giữa CO, NO2, SO2, PM2.5 |
    | **Goal 5** | Phân tích rủi ro sức khỏe theo ngưỡng WHO |

    👈 Chọn mục phân tích ở thanh bên trái để bắt đầu.
    """
)
