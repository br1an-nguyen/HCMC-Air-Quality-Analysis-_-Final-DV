import streamlit as st
from dashboard.ui_theme import render_page_header, inject_global_css

def main():
    inject_global_css()
    render_page_header(
        "Tổng quan Dự án Phân tích Chất lượng Không khí TP.HCM",
        "Giai đoạn nghiên cứu 2021 – 2022"
    )
    
    st.markdown("""
    ### Giới thiệu chung
    Dashboard này được xây dựng nhằm cung cấp cái nhìn toàn diện và trực quan về thực trạng ô nhiễm không khí tại Thành phố Hồ Chí Minh trong giai đoạn 2021 - 2022. 
    Dữ liệu được thu thập từ các trạm quan trắc tự động, bao gồm các chỉ số quan trọng như <b>PM2.5, NO2, SO2, CO, O3 và TSP</b>.

    ### Mục tiêu của Dashboard
    Hệ thống phân tích tập trung vào 5 mục tiêu chính:

    1.  <b>Xu Hướng Thời Gian</b>: Theo dõi sự biến đổi của các chất ô nhiễm theo giờ, ngày, tháng và mùa. Xác định các thời điểm ô nhiễm nhất trong năm.
    2.  <b>Phân Bố Khu Vực</b>: So sánh chất lượng không khí giữa các trạm quan trắc khác nhau để tìm ra các "điểm nóng" ô nhiễm.
    3.  <b>Thời Tiết Ảnh Hưởng</b>: Phân tích mối liên hệ giữa các yếu tố khí tượng (Nhiệt độ, Độ ẩm) và mức độ tập trung của bụi mịn.
    4.  <b>Tương Quan Quan Hệ</b>: Khám phá mối quan hệ tương hỗ giữa các chất gây ô nhiễm để hiểu rõ hơn về nguồn phát thải.
    5.  <b>Rủi Ro Sức Khỏe</b>: Đánh giá mức độ rủi ro dựa trên các tiêu chuẩn sức khỏe cộng đồng (như ngưỡng WHO).

    ### Hướng dẫn sử dụng
    *   Sử dụng <b>thanh điều hướng bên trái</b> để chuyển đổi giữa các mục tiêu phân tích.
    *   Tại mỗi trang, bạn có thể sử dụng các bộ lọc ở Sidebar để tùy chỉnh khoảng thời gian và trạm quan trắc cần xem.
    *   Các biểu đồ đều có tính tương tác, bạn có thể phóng to hoặc di chuột để xem giá trị chi tiết.
    
    <hr style='border:none; border-top:1px solid #E5EEF3; margin:24px 0 18px 0;'>
    <p style='color:#4F6B7A; font-style:italic;'>Phát triển bởi nhóm nghiên cứu Phân tích Dữ liệu Chất lượng Không khí.</p>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
