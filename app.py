"""
HCMC Air Quality Dashboard — Home Page
Streamlit multipage app: các goal nằm trong thư mục pages/
Chạy: streamlit run app.py
"""
import streamlit as st
import requests
import json

st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌫️ HCMC Air Quality Dashboard")

tab1, tab2 = st.tabs(["🏠 Dashboard Home", "🤖 AI Assistant"])

with tab1:
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

with tab2:
    st.header("🤖 Trợ lý Phân tích AI (Data Analyst)")
    st.write("Nhập yêu cầu phân tích dữ liệu, AI sẽ viết code Python và bạn có thể duyệt/chạy ngay trên máy.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("💬 Trò chuyện")
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
            
        # Hiển thị lịch sử chat
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if prompt := st.chat_input("Hỏi AI về cách vẽ biểu đồ hoặc phân tích dữ liệu..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("AI đang phân tích..."):
                    try:
                        res = requests.post("http://localhost:8000/api/chat", json={
                            "prompt": prompt,
                            "context": "Dữ liệu gồm PM2.5, NO2, SO2, CO, O3, TSP từ 2021-2022 tại 6 trạm TP.HCM."
                        })
                        if res.status_code == 200:
                            data = res.json()
                            explanation = data.get("explanation", "Không có giải thích.")
                            st.write(explanation)
                            st.session_state.chat_messages.append({"role": "assistant", "content": explanation})
                            
                            # Lưu code AI sinh ra vào session_state để đẩy qua cột Editor
                            code_generated = data.get("code", "")
                            if code_generated:
                                st.session_state.current_code = code_generated
                                st.rerun() # Refresh UI để hiển thị code mới sang cột 2
                        else:
                            st.error(f"Lỗi API: {res.text}")
                    except Exception as e:
                        st.error("Không thể kết nối Backend FastAPI. Đảm bảo bạn đã chạy: `uvicorn backend.main:app --port 8000`")
    
    with col2:
        st.subheader("💻 Mã nguồn & Thực thi")
        st.info("Sau khi AI sinh code, bạn có thể chỉnh sửa ở đây và bấm Chạy.")
        
        # Lấy code hiện tại từ session state
        code_val = st.session_state.get("current_code", "# Code Python do AI sinh ra sẽ xuất hiện ở đây\n")
        
        # Ô text area cho phép sửa code
        code_input = st.text_area("Python Editor", value=code_val, height=400)
        
        if st.button("🚀 Phê duyệt & Chạy Code (Execute)"):
            if code_input.strip() and code_input != "# Code Python do AI sinh ra sẽ xuất hiện ở đây\n":
                with st.spinner("Đang chạy mã Python..."):
                    try:
                        exec_res = requests.post("http://localhost:8000/api/execute", json={"code": code_input})
                        if exec_res.status_code == 200:
                            result = exec_res.json()
                            if result["success"]:
                                st.success("Chạy thành công!")
                                if result["stdout"]:
                                    st.text("Kết quả (Stdout):")
                                    st.code(result["stdout"])
                            else:
                                st.error("Có lỗi trong quá trình chạy!")
                                if result["stderr"]:
                                    st.text("Lỗi (Stderr):")
                                    st.code(result["stderr"])
                        else:
                            st.error(f"Lỗi Execute API: {exec_res.text}")
                    except Exception as e:
                         st.error("Không thể kết nối Backend Execute API.")
            else:
                st.warning("Vui lòng nhập code trước khi chạy.")
