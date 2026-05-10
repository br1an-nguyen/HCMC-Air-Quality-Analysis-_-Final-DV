"""
HCMC Air Quality Dashboard — Entry Point
Sử dụng st.navigation để tạo giao diện đa trang hiện đại.
"""
import streamlit as st

# Cấu hình trang chung
st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Định nghĩa các trang dựa trên file trong thư mục dashboard/
pg0 = st.Page("dashboard/overview.py", title="Tổng Quan", icon=":material/home:", default=True)
pg1 = st.Page("dashboard/goal1_time_trend_dashboard.py", title="Xu Hướng Thời Gian", icon=":material/trending_up:")
pg2 = st.Page("dashboard/goal2_station_comparison_dashboard.py", title="Phân Bố Khu Vực", icon=":material/location_on:")
pg3 = st.Page("dashboard/goal3_weather_impact_analysis.py", title="Ảnh Hưởng Thời Tiết", icon=":material/wb_sunny:")
pg4 = st.Page("dashboard/goal4_pollutant_correlation_analysis.py", title="Tương Quan Các Chất", icon=":material/analytics:")
pg5 = st.Page("dashboard/goal5_health_risk_profiling.py", title="Rủi Ro Sức Khỏe", icon=":material/health_and_safety:")

# Sử dụng danh sách phẳng để không hiển thị tiêu đề nhóm
pg = st.navigation([pg0, pg1, pg2, pg3, pg4, pg5])

# ── Styling Sidebar Navigation ──
st.markdown(
    """
    <style>
    /* Mục lục điều hướng chung */
    [data-testid="stSidebarNav"] ul {
        padding-top: 10px;
    }
    
    /* Font chữ lớn cho tất cả các mục */
    [data-testid="stSidebarNav"] li a {
        font-size: 16px !important;
        font-weight: 500 !important;
        color: #16324F !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        margin-bottom: 4px !important;
    }

    /* Riêng chữ "Tổng quan" trong sidebar */
    [data-testid="stSidebarNav"] li:first-child {
        border-bottom: 1px solid #E5EEF3 !important;
        margin-bottom: 12px !important;
        padding-bottom: 12px !important;
    }
    
    [data-testid="stSidebarNav"] li:first-child a span {
        font-size: 24px !important;
        font-weight: 700 !important;
    }

    /* Phần được chọn: background xanh đậm, chữ trắng */
    [data-testid="stSidebarNav"] li a[aria-current="page"] {
        background-color: #16324F !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebarNav"] li a[aria-current="page"] span {
        color: #ffffff !important;
    }
    [data-testid="stSidebarNav"] li a[aria-current="page"] svg {
        fill: #ffffff !important;
    }

    /* Căn chỉnh icon */
    [data-testid="stSidebarNavItems"] svg {
        width: 20px !important;
        height: 20px !important;
        margin-right: 4px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Chạy trang đã chọn
pg.run()

# Lưu ý: Phần AI Assistant cũ đã được lược bỏ để khớp với giao diện tối giản trong hình.
# Nếu bạn muốn thêm lại AI Assistant như một trang riêng, có thể định nghĩa thêm st.Page cho nó.

# Tích hợp Floating Chatbot Widget (Phase 4)
import os
try:
    from dashboard.components.chat_widget import render_chat_widget
    # Lấy backend URL từ env, mặc định 8000 (FastAPI).
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    render_chat_widget(backend_url)
except Exception as e:
    st.error(f"Cannot load Chatbot Widget: {e}")
