import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from itertools import combinations
import os

# ── Design tokens ─────────────────────────────────────────────────────────────
C = {
    "CO": "#4E5D8A", "NO2": "#D98E04", "SO2": "#2B7BBB", "PM2.5": "#B23A2F",
    "hi": "#FFB703", "bg": "#FFFFFF", "card": "#FFFFFF",
    "border": "#D9E4EC", "text": "#16324F", "sub": "#4F6B7A",
    "grid": "#E5EEF3", "pos": "#1F8A70", "neg": "#B23A2F",
}

COLS      = ["CO", "NO2", "SO2", "PM2.5"]
UNITS     = {"CO": "μg/m³", "NO2": "μg/m³", "SO2": "μg/m³", "PM2.5": "μg/m³"}
ALL_PAIRS = list(combinations(COLS, 2))

@st.cache_data
def load_data(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    for col, flag in {"CO":"CO_flag","NO2":"NO2_flag","SO2":"SO2_flag","PM2.5":"PM2.5_flag"}.items():
        df.loc[df[flag] == 2, col] = np.nan
    return df

def rbadge(r):
    a   = abs(r)
    bg  = "#D65A31" if a >= .6 else ("#D98E04" if a >= .3 else "#6B7A99")
    lbl = "Mạnh"    if a >= .6 else ("Trung bình" if a >= .3 else "Yếu")
    sgn = "+" if r >= 0 else "−"
    return (f"<span style='background:{bg};color:#fff;font-size:9.5px;font-weight:700;"
            f"padding:2px 8px;border-radius:20px;font-family:monospace;'>{sgn}{a:.2f}</span>"
            f"&nbsp;<span style='font-size:10.5px;color:{C['sub']};'>{lbl}</span>")

def _strength_label(r):
    if pd.isna(r): return "Không đủ dữ liệu", "ins-weak"
    ar = abs(r)
    if r < -0.1: return "Nghịch biến nhẹ", "ins-neg"
    if ar >= 0.6: return "Tương quan mạnh", "ins-strong"
    if ar >= 0.3: return "Tương quan trung bình", "ins-mid"
    return "Tương quan yếu", "ins-weak"

def _fmt_r(r):
    return "N/A" if pd.isna(r) else f"{r:+.3f}"

def _pair_insight(a, b, r):
    lbl, css = _strength_label(r)
    key = tuple(sorted([a, b]))
    if key == ("CO", "SO2"):
        if pd.isna(r): txt = "Dữ liệu chưa đủ để kết luận."
        elif r >= 0.6: txt = "CO và SO2 tăng/giảm cùng pha rõ rệt, củng cố dấu hiệu nguồn đốt và giao thông diesel."
        elif r >= 0.2: txt = "CO-SO2 vẫn đồng biến nhưng chưa mạnh."
        else: txt = "CO-SO2 đồng biến yếu trong phạm vi lọc này."
    elif key == ("CO", "NO2"):
        if pd.isna(r): txt = "Chưa đủ dữ liệu."
        elif abs(r) < 0.15: txt = "CO-NO2 rất yếu: NO2 chịu thêm quá trình quang hóa ban ngày nên không đi cùng CO."
        elif r > 0: txt = "CO-NO2 dương, gợi ý vai trò phát thải sơ cấp nổi bật hơn."
        else: txt = "CO-NO2 âm nhẹ cho thấy lệch pha theo thời gian."
    elif key == ("CO", "PM2.5"):
        if pd.isna(r): txt = "Chưa đủ dữ liệu."
        elif abs(r) >= 0.3: txt = "CO-PM2.5 trung bình trở lên, cho thấy giao thông đóng góp đáng kể vào bụi mịn."
        else: txt = "CO-PM2.5 yếu, phản ánh PM2.5 là bài toán đa nguồn."
    elif key == ("NO2", "PM2.5"):
        if pd.isna(r): txt = "Chưa đủ dữ liệu."
        elif r < -0.1: txt = "NO2-PM2.5 âm nhẹ cho thấy lệch pha thời gian: NO2 tăng khi quang hóa, PM2.5 tích lũy khác."
        else: txt = "NO2-PM2.5 không âm rõ; khả năng có bụi thứ cấp hoặc đồng biến theo điều kiện không khí."
    else:
        if pd.isna(r): txt = "Không đủ dữ liệu."
        elif abs(r) >= 0.3: txt = "Hai chất có xu hướng đi cùng nhau ở mức đáng kể."
        else: txt = "Mối liên hệ giữa hai chất còn yếu."
    return lbl, css, txt

def _scatter_dynamic_insights(sdf, x_col, y_col, color_mode, r_val):
    insights = []
    n = len(sdf)
    strength, _ = _strength_label(r_val)
    insights.append(f"Bộ lọc hiện tại: {n} điểm; tương quan: {strength} (r = {_fmt_r(r_val)}).")
    if not pd.isna(r_val):
        if r_val >= 0.3: insights.append(f"Khi {x_col} tăng, {y_col} có xu hướng tăng cùng chiều.")
        elif r_val <= -0.1: insights.append(f"{x_col} và {y_col} có xu hướng ngược chiều nhẹ.")
        else: insights.append(f"Mối liên hệ giữa {x_col} và {y_col} đang yếu.")
    if n >= 20 and sdf[x_col].std() > 0:
        slope = np.polyfit(sdf[x_col], sdf[y_col], 1)[0]
        if slope > 0: insights.append(f"Độ dốc OLS dương ({slope:.4f}) xác nhận chiều tăng.")
        elif slope < 0: insights.append(f"Độ dốc OLS âm ({slope:.4f}) cho thấy chiều giảm.")
    return insights[:4]

def main():
    try:
        st.set_page_config(
            page_title="P05 · Correlation Insights · HCMC Air Quality",
            page_icon="🌫️",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except st.errors.StreamlitAPIException:
        pass

    # ── CSS ───────────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; background: {C['bg']}; color: {C['text']}; }}
    .dash-header {{ background: linear-gradient(135deg, {C['text']} 0%, #1E3A52 60%, #2A5A7A 100%); border-radius: 14px; padding: 24px 32px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(22,50,79,0.15); color:white; }}
    .kpi-card {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:12px; padding:16px; box-shadow:0 2px 8px rgba(22,50,79,.05); }}
    .rtable {{ width:100%; border-collapse:collapse; border:1px solid {C['border']}; border-radius:8px; overflow:hidden; font-size:12px; }}
    .rtable th {{ padding:6px 10px; text-align:left; background:{C['bg']}; color:{C['sub']}; }}
    .rtable td {{ padding:6px 10px; border-top:1px solid {C['grid']}; }}
    .ins-wrap {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top:10px; }}
    .ins-card {{ border: 1px solid {C['border']}; border-left: 4px solid {C['NO2']}; border-radius: 8px; padding: 12px; background: #FAFCFE; }}
    .ins-strong {{ border-left-color: {C['pos']}; }}
    .ins-mid {{ border-left-color: {C['NO2']}; }}
    .ins-weak {{ border-left-color: #7C8AA7; }}
    .ins-neg {{ border-left-color: {C['neg']}; }}
    hr.div {{ border:none; border-top:1px solid {C['border']}; margin:18px 0; }}
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"<div style='background:{C['text']};border-radius:10px;padding:12px;color:white;font-weight:700;'>HCMC Air Quality</div>", unsafe_allow_html=True)
        st.markdown("**Dữ liệu**")
        uploaded = st.file_uploader("Tải CSV", type="csv")
        st.markdown("---")
        st.markdown("**Bộ lọc**")
        station_ph = st.empty()
        date_ph = st.empty()
        hour_ph = st.empty()
        st.markdown("---")
        scatter_x = st.selectbox("Trục X", COLS, index=0)
        scatter_y = st.selectbox("Trục Y", COLS, index=2)
        color_by = st.radio("Màu theo", ["Station_No", "Hour"], horizontal=True)

    # ── Load Data ─────────────────────────────────────────────────────────────────
    if uploaded:
        df_raw = load_data(uploaded)
    else:
        paths = ["Air_Quality_HCMC_Cleaned.csv", "data/cleaned/Air_Quality_HCMC_Cleaned.csv", "../data/cleaned/Air_Quality_HCMC_Cleaned.csv"]
        path = next((p for p in paths if os.path.exists(p)), None)
        if path: df_raw = load_data(path)
        else:
            st.warning("⚠️ Không tìm thấy file dữ liệu.")
            st.stop()

    all_stations = sorted(df_raw["Station_No"].unique())
    sel_stations = station_ph.multiselect("Trạm đo", all_stations, default=all_stations, format_func=lambda x: f"Trạm {x}")
    dmin, dmax = df_raw["Date"].min().date(), df_raw["Date"].max().date()
    sel_dates = date_ph.date_input("Khoảng thời gian", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    sel_hours = hour_ph.slider("Giờ trong ngày", 0, 23, (0, 23))

    df = df_raw[df_raw["Station_No"].isin(sel_stations) & (df_raw["Date"] >= pd.Timestamp(sel_dates[0])) & (df_raw["Date"] <= pd.Timestamp(sel_dates[1])) & df_raw["Hour"].between(sel_hours[0], sel_hours[1])].copy()
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu sau bộ lọc.")
        st.stop()

    # ── UI ────────────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="dash-header">
      <h2 style='margin:0;'>Tương quan nội bộ giữa các chất ô nhiễm</h2>
      <div style='font-size:12px;opacity:0.8;'>📍 {len(sel_stations)} trạm | 🕐 {sel_hours[0]:02d}h–{sel_hours[1]:02d}h</div>
    </div>""", unsafe_allow_html=True)

    corr_ov = df[COLS].corr().round(3)
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("**Correlation Heatmap**")
        fig_hm = px.imshow(corr_ov, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        st.plotly_chart(fig_hm, use_container_width=True)

    with col2:
        st.markdown("**Hệ số Pearson r**")
        rows_html = "".join(f"<tr><td>{a} – {b}</td><td>{rbadge(corr_ov.loc[a,b])}</td></tr>" for a, b in ALL_PAIRS)
        st.markdown(f"<table class='rtable'><thead><tr><th>Cặp biến</th><th>Hệ số r</th></tr></thead><tbody>{rows_html}</tbody></table>", unsafe_allow_html=True)

    st.markdown("<hr class='div'>", unsafe_allow_html=True)
    st.markdown("**Insights**")
    cards = []
    for a, b in [("CO", "SO2"), ("CO", "NO2"), ("CO", "PM2.5"), ("NO2", "PM2.5")]:
        rv = corr_ov.loc[a, b]
        lbl, css, txt = _pair_insight(a, b, rv)
        cards.append(f"<div class='ins-card {css}'><b>{a}-{b} (r={rv:+.2f})</b><br>{txt}</div>")
    st.markdown(f"<div class='ins-wrap'>{''.join(cards)}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()