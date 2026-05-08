"""
P05_Correlation_Insights — HCMC Air Quality
Mục tiêu 4: Tương quan nội bộ giữa CO, NO2, SO2, PM2.5
Chạy: streamlit run p05_v4.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from itertools import combinations

st.set_page_config(
    page_title="P05 · Correlation Insights · HCMC Air Quality",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', 'Segoe UI', Arial, sans-serif;
    background: {C['bg']}; color: {C['text']};
}}

/* ── Header ── */
.dash-header {{
    background: linear-gradient(135deg, {C['text']} 0%, #1E3A52 60%, #2A5A7A 100%);
    border-radius: 14px; padding: 24px 32px; margin-bottom: 20px;
    position: relative; overflow: hidden;
    box-shadow: 0 4px 20px rgba(22,50,79,0.15);
}}
.dash-header::before {{
    content:''; position:absolute; top:-50px; right:-50px;
    width:200px; height:200px; border-radius:50%;
    background: radial-gradient(circle,rgba(255,183,3,.18) 0%,rgba(255,183,3,0) 70%);
}}
.dash-header h1 {{
    color:#fff; font-size:21px; font-weight:700;
    margin:0 0 6px; letter-spacing:-.4px;
}}
.dash-header .hm {{
    color:rgba(255,255,255,.55); font-size:12.5px;
    margin:0; display:flex; gap:16px; flex-wrap:wrap;
}}

/* ── KPI cards ── */
.kpi-card {{
    background:{C['card']}; border:1px solid {C['border']};
    border-radius:12px; padding:16px 18px 14px;
    position:relative; overflow:hidden;
    box-shadow:0 2px 8px rgba(22,50,79,.05);
}}
.kpi-card .accent {{
    position:absolute; top:0; left:0;
    width:100%; height:3px; border-radius:12px 12px 0 0;
}}
.kpi-card .klabel {{
    font-size:10px; font-weight:600; letter-spacing:.9px;
    color:{C['sub']}; text-transform:uppercase; margin-bottom:8px;
    display:flex; align-items:center; gap:6px;
}}
.kpi-card .kdot {{
    width:7px; height:7px; border-radius:50%; flex-shrink:0;
}}
.kpi-card .kval {{
    font-size:30px; font-weight:700; line-height:1;
    margin-bottom:4px; letter-spacing:-1px;
    font-family:'DM Mono',monospace;
}}
.kpi-card .kunit {{
    font-size:12px; font-weight:400; color:{C['sub']}; margin-left:2px;
}}
.kpi-card .ksub {{ font-size:11px; color:{C['sub']}; }}

/* ── Section headers ── */
.stitle {{
    font-size:14px; font-weight:700; color:{C['text']};
    margin:0 0 2px; letter-spacing:-.2px;
}}
.ssub {{ font-size:11.5px; color:{C['sub']}; margin:0 0 10px; }}

/* ── r table ── */
.rtable {{
    width:100%; border-collapse:collapse;
    border:1px solid {C['border']}; border-radius:8px;
    overflow:hidden; font-size:12px;
}}
.rtable thead tr {{ background:{C['bg']}; }}
.rtable th {{
    padding:6px 10px; text-align:left; font-size:9.5px;
    font-weight:700; color:{C['sub']}; letter-spacing:.6px; text-transform:uppercase;
}}
.rtable td {{ padding:6px 10px; border-top:1px solid {C['grid']}; }}

/* ── Divider ── */
hr.div {{ border:none; border-top:1px solid {C['border']}; margin:18px 0; }}

#MainMenu,footer,header {{ visibility:hidden; }}
.block-container {{ padding-top:1.3rem; padding-bottom:2rem; }}
</style>
""", unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    for col, flag in {"CO":"CO_flag","NO2":"NO2_flag","SO2":"SO2_flag","PM2.5":"PM2.5_flag"}.items():
        df.loc[df[flag] == 2, col] = np.nan
    return df


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='background:{C["text"]};border-radius:10px;
                padding:12px 16px;margin-bottom:16px;'>
      <div style='color:white;font-size:14px;font-weight:700;'>HCMC Air Quality</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**Dữ liệu**")
    uploaded = st.file_uploader("Tải CSV", type="csv",
                                 help="Air_Quality_HCMC_Cleaned.csv")
    st.markdown("---")
    st.markdown("**Bộ lọc**")
    station_ph = st.empty()
    date_ph    = st.empty()
    hour_ph    = st.empty()
    st.markdown("---")
    st.markdown("**Scatter tuỳ chỉnh**")
    scatter_x = st.selectbox("Trục X", COLS, index=0)
    scatter_y = st.selectbox("Trục Y", COLS, index=2)
    color_by  = st.radio("Màu theo", ["Station_No", "Hour"], horizontal=True)
    st.markdown("---")
    st.markdown(f"<div style='font-size:10.5px;color:{C['sub']};line-height:1.7;'>"
                "6 trạm · 02/2021–06/2022<br>Flag=2: loại trước khi tính r<br>"
                "Outlier: giữ lại</div>", unsafe_allow_html=True)


# ── Load & Filter ─────────────────────────────────────────────────────────────
if uploaded:
    df_raw = load_data(uploaded)
else:
    try:
        df_raw = load_data("Air_Quality_HCMC_Cleaned.csv")
    except FileNotFoundError:
        st.warning("⚠️ Chưa có file. Vui lòng upload CSV ở sidebar.")
        st.stop()

all_stations = sorted(df_raw["Station_No"].unique())
sel_stations = station_ph.multiselect("Trạm đo", all_stations, default=all_stations,
                                      format_func=lambda x: f"Trạm {x}")
dmin, dmax = df_raw["Date"].min().date(), df_raw["Date"].max().date()
sel_dates  = date_ph.date_input("Khoảng thời gian", value=(dmin, dmax),
                                 min_value=dmin, max_value=dmax)
sel_hours  = hour_ph.slider("Giờ trong ngày", 0, 23, (0, 23))

df = df_raw[
    df_raw["Station_No"].isin(sel_stations) &
    (df_raw["Date"] >= pd.Timestamp(sel_dates[0])) &
    (df_raw["Date"] <= pd.Timestamp(sel_dates[1])) &
    df_raw["Hour"].between(sel_hours[0], sel_hours[1])
].copy()

# Guard: if all stations are deselected or filters remove all rows, stop gracefully
if df.empty:
    st.warning("⚠️ Không có dữ liệu sau bộ lọc. Vui lòng chọn ít nhất một trạm hoặc mở rộng phạm vi ngày/giờ.")
    st.stop()


# ── Precompute ────────────────────────────────────────────────────────────────
corr_ov = df[COLS].corr().round(3)
means   = {c: df[c].mean() for c in COLS}
stations_sel = sorted(df["Station_No"].unique())
st_corr = {st: df[df["Station_No"]==st][COLS].corr().round(3) for st in stations_sel}

cmap_st = {str(s): px.colors.qualitative.Set2[i % 8]
           for i, s in enumerate(sorted(df["Station_No"].unique()))}


# ── Helpers ───────────────────────────────────────────────────────────────────
def kpi(label, val, unit, sub, color, fmt=".1f"):
    v = f"{val:{fmt}}" if isinstance(val, (int, float)) else str(val)
    return (f'<div class="kpi-card">'
            f'<div class="accent" style="background:{color};"></div>'
            f'<div class="klabel"><span class="kdot" style="background:{color};"></span>{label}</div>'
            f'<div class="kval" style="color:{color};">{v}<span class="kunit">{unit}</span></div>'
            f'<div class="ksub">{sub}</div></div>')

def rbadge(r):
    a   = abs(r)
    bg  = "#D65A31" if a >= .6 else ("#D98E04" if a >= .3 else "#6B7A99")
    lbl = "Mạnh"    if a >= .6 else ("Trung bình" if a >= .3 else "Yếu")
    sgn = "+" if r >= 0 else "−"
    return (f"<span style='background:{bg};color:#fff;font-size:9.5px;font-weight:700;"
            f"padding:2px 8px;border-radius:20px;font-family:monospace;'>{sgn}{a:.2f}</span>"
            f"&nbsp;<span style='font-size:10.5px;color:{C['sub']};'>{lbl}</span>")

def bl(h=290, mb=8):
    return dict(height=h, margin=dict(l=6,r=6,t=6,b=mb),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Sans", color=C["text"]))


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="dash-header">
  <h1>Tương quan nội bộ giữa các chất ô nhiễm</h1>
  <div class="hm">
    <span>📍 {len(sel_stations)} trạm</span>
    <span>📅 {sel_dates[0].strftime('%d/%m/%Y')} – {sel_dates[1].strftime('%d/%m/%Y')}</span>
    <span>🕐 {sel_hours[0]:02d}h–{sel_hours[1]:02d}h</span>
    <span>🔬 CO · NO₂ · SO₂ · PM2.5</span>
  </div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ═══════════════════════════════════════════════════════════════════════════════
k1,k2,k3,k4 = st.columns(4, gap="small")
for col_ui, metric, fmt in zip([k1,k2,k3,k4], COLS, [".0f",".1f",".1f",".1f"]):
    with col_ui:
        st.markdown(kpi(f"Mean {metric}", means[metric], " μg/m³",
                        "Trung bình toàn kỳ", C[metric], fmt), unsafe_allow_html=True)

st.markdown("<hr class='div'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Heatmap (trái, 38%) | Bảng r + Insight (phải, 62%)
# Tách heatmap khỏi bảng r để hai cột cân đối
# ═══════════════════════════════════════════════════════════════════════════════
r1_left, r1_right = st.columns([1.1, 1], gap="large")

with r1_left:
    st.markdown('<p class="stitle">Correlation Heatmap</p>'
                '<p class="ssub">Pearson r · giá trị gốc (flag ≠ 2) · toàn bộ trạm</p>',
                unsafe_allow_html=True)
    z = corr_ov.values
    fig_hm = go.Figure(go.Heatmap(
        z=z, x=COLS, y=COLS,
        text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont={"size":15,"family":"DM Mono","color":C["text"]},
        colorscale=[[0,"#B23A2F"],[.3,"#F2D4D0"],[.5,"#F9FBFC"],[.7,"#C8DFF0"],[1,"#2B7BBB"]],
        zmid=0, zmin=-1, zmax=1, showscale=True,
        colorbar=dict(thickness=10, len=.85,
                      title=dict(text="r", font=dict(size=10,color=C["sub"])),
                      tickfont=dict(size=9,color=C["sub"]), tickvals=[-1,-.5,0,.5,1]),
        xgap=4, ygap=4,
    ))
    fig_hm.update_layout(
        **bl(340),
        xaxis=dict(showgrid=False, tickfont=dict(size=12,family="DM Sans")),
        yaxis=dict(showgrid=False, tickfont=dict(size=12,family="DM Sans"), autorange="reversed"),
    )
    st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar":False})

with r1_right:
    st.markdown('<p class="stitle">Hệ số Pearson r — 6 cặp biến</p>'
                '<p class="ssub">Mức độ tương quan tuyến tính · toàn bộ trạm · giá trị gốc (flag ≠ 2)</p>',
                unsafe_allow_html=True)

    # Bảng r — full-width trong cột phải
    rows_html = "".join(
        f"<tr><td style='font-weight:500;'>{a} – {b}</td>"
        f"<td>{rbadge(corr_ov.loc[a,b])}</td></tr>"
        for a, b in ALL_PAIRS
    )
    st.markdown(f"""
    <table class="rtable">
      <thead><tr><th>Cặp biến</th><th>Hệ số r</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


st.markdown("<hr class='div'>", unsafe_allow_html=True)

st.markdown('<p class="stitle">Pair-scatter: CO là trục trung tâm</p>'
            '<p class="ssub">CO so với NO₂ · SO₂ · PM2.5 — 400 mẫu · trendline OLS · màu theo trạm</p>',
            unsafe_allow_html=True)

pairs3   = [("CO","NO2"),("CO","SO2"),("CO","PM2.5")]
labels3  = ["CO vs NO₂", "CO vs SO₂", "CO vs PM2.5"]

for col_ui, (xa,ya), lbl in zip(st.columns(3, gap="medium"), pairs3, labels3):
    sub = df[[xa,ya,"Station_No"]].dropna()
    sub = sub.sample(min(400,len(sub)), random_state=pairs3.index((xa,ya))*7)
    rp  = sub[[xa,ya]].corr().iloc[0,1]

    fig_p = px.scatter(sub, x=xa, y=ya,
                       color=sub["Station_No"].astype(str), color_discrete_map=cmap_st,
                       opacity=.45, trendline="ols", trendline_scope="overall",
                       trendline_color_override=C["text"], labels={"color":"Trạm"})
    fig_p.update_traces(selector=dict(mode="markers"), marker=dict(size=3.5))
    fig_p.update_layout(
        height=210, margin=dict(l=6,r=6,t=34,b=6),
        title=dict(text=f"<b>{lbl}</b>   r = {rp:.3f}",
                   font=dict(size=11.5,color=C["text"]), x=0.04, y=0.97),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=C["text"]),
        xaxis=dict(title=dict(text=xa,font=dict(size=9.5)),
                   gridcolor=C["grid"], zeroline=False, tickfont=dict(size=8.5)),
        yaxis=dict(title=dict(text=ya,font=dict(size=9.5)),
                   gridcolor=C["grid"], zeroline=False, tickfont=dict(size=8.5)),
        legend=dict(
            title=dict(text="Trạm", font=dict(size=8.5)),
            font=dict(size=8.5),
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,.88)",
            bordercolor=C["border"],
            borderwidth=1,
        ),
        showlegend=True,
    )
    with col_ui:
        st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})

st.markdown("<hr class='div'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ROW 3 — Scatter tuỳ chỉnh (expandable, full-width)
# ═══════════════════════════════════════════════════════════════════════════════
with st.expander(f"🔍  Scatter tuỳ chỉnh — {scatter_x} vs {scatter_y}  (chọn biến trong sidebar)",
                 expanded=False):
    if scatter_x == scatter_y:
        st.warning("⚠️ Vui lòng chọn hai biến khác nhau.")
    else:
        sdf = df[[scatter_x, scatter_y, "Station_No", "Hour"]].dropna()
        sdf = sdf.sample(min(1000, len(sdf)), random_state=42)
        rv  = sdf[[scatter_x, scatter_y]].corr().iloc[0,1]

        sc_left, sc_right = st.columns([2.2, 1], gap="large")

        with sc_left:
            # Layout chung cho cả 2 mode
            _axis_x = dict(title=dict(text=f"{scatter_x} ({UNITS[scatter_x]})", font=dict(size=12)),
                           gridcolor=C["grid"], zeroline=False,
                           showline=True, linecolor=C["border"], tickfont=dict(size=10))
            _axis_y = dict(title=dict(text=f"{scatter_y} ({UNITS[scatter_y]})", font=dict(size=12)),
                           gridcolor=C["grid"], zeroline=False,
                           showline=True, linecolor=C["border"], tickfont=dict(size=10))

            if color_by == "Station_No":
                fig_sc = px.scatter(sdf, x=scatter_x, y=scatter_y,
                                    color=sdf["Station_No"].astype(str),
                                    color_discrete_map=cmap_st, opacity=.5,
                                    trendline="ols", trendline_scope="overall",
                                    trendline_color_override=C["text"], labels={"color":"Trạm"})
                fig_sc.update_traces(selector=dict(mode="markers"), marker=dict(size=4))
                fig_sc.update_layout(
                    **bl(340),
                    xaxis=_axis_x, yaxis=_axis_y,
                    hovermode="closest",
                    # legend riêng, không có colorbar
                    legend=dict(
                        title=dict(text="Trạm", font=dict(size=11)),
                        bgcolor="rgba(255,255,255,.85)",
                        bordercolor=C["border"], borderwidth=1,
                        font=dict(size=11),
                        x=1.01, y=1,            # đẩy legend ra ngoài chart
                        xanchor="left", yanchor="top",
                    ),
                )
            else:
                fig_sc = px.scatter(sdf, x=scatter_x, y=scatter_y, color="Hour",
                                    color_continuous_scale=["#2B7BBB","#FFB703","#B23A2F"],
                                    opacity=.5, trendline="ols", trendline_scope="overall",
                                    trendline_color_override=C["text"])
                fig_sc.update_traces(selector=dict(mode="markers"), marker=dict(size=4))
                fig_sc.update_layout(
                    **bl(340),
                    xaxis=_axis_x, yaxis=_axis_y,
                    hovermode="closest",
                    showlegend=False,           # tắt legend text, chỉ giữ colorbar
                    coloraxis_colorbar=dict(
                        title=dict(text="Giờ", font=dict(size=11)),
                        thickness=14, len=.75,
                        tickfont=dict(size=10),
                        tickvals=[0, 6, 12, 18, 23],
                        ticktext=["0h", "6h", "12h", "18h", "23h"],
                        x=1.01,                 # đẩy colorbar sát cạnh phải
                    ),
                )

            fig_sc.add_annotation(x=.97, y=.05, xref="paper", yref="paper",
                                  text=f"<b>r = {rv:.3f}</b>", showarrow=False,
                                  font=dict(size=13, color=C["text"], family="DM Mono"),
                                  bgcolor="rgba(255,255,255,.9)",
                                  bordercolor=C["border"], borderwidth=1, borderpad=7)
            st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})

        with sc_right:
            # Bảng r per-station cho cặp đang chọn
            st.markdown(f'<p class="stitle" style="font-size:12.5px;">'
                        f'r của {scatter_x}–{scatter_y} theo trạm</p>',
                        unsafe_allow_html=True)
            rrows = "".join(
                f"<tr><td>Trạm {s}</td>"
                f"<td>{rbadge(st_corr[s].loc[scatter_x, scatter_y])}</td></tr>"
                for s in stations_sel
            )
            st.markdown(f"""
            <table class="rtable" style="margin-top:8px;">
              <thead><tr><th>Trạm</th><th>Hệ số r</th></tr></thead>
              <tbody>{rrows}</tbody>
            </table>""", unsafe_allow_html=True)