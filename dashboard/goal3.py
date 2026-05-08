"""
Goal 3 — Tác động của yếu tố thời tiết đến nồng độ ô nhiễm
Dashboard Streamlit + Plotly cho phân tích HCMC Air Quality.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ──────────────────────────── CONFIG ────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "data" / "cleaned" / "Air_Quality_HCMC_Cleaned.csv"

COLORS = {
    "PM2.5": "#B23A2F", "TSP": "#6F1D1B", "O3": "#1F8A70",
    "CO": "#4E5D8A", "NO2": "#D98E04", "SO2": "#2B7BBB",
    "Temperature": "#D65A31", "Humidity": "#2F80ED",
}
POLLUTANTS = ["PM2.5", "TSP", "O3", "CO", "NO2", "SO2"]
WEATHER = ["Temperature", "Humidity"]
STATIONS = [1, 2, 3, 4, 5, 6]
MONTH_LABELS = {i: f"T{i}" for i in range(1, 13)}


def _season(m: int) -> str:
    return "Mùa khô" if m in (12, 1, 2, 3, 4) else "Mùa mưa"


def _norm(s: pd.Series) -> pd.Series:
    """Min-max normalize về 0-1."""
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi != lo else pd.Series(0.5, index=s.index)


# ──────────────────────────── DATA ──────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    df["month"] = df["Date"].dt.month
    df["season"] = df["month"].map(_season)
    return df


def apply_filters(df, stations, date_range, season, hour_range):
    f = df[df["Station_No"].isin(stations)].copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        f = f[(f["Date"] >= pd.Timestamp(date_range[0])) & (f["Date"] <= pd.Timestamp(date_range[1]))]
    if season != "Tất cả":
        f = f[f["season"] == season]
    f = f[(f["Hour"] >= hour_range[0]) & (f["Hour"] <= hour_range[1])]
    return f

def filter_original_multi(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Giữ lại các hàng có flag=0 cho TẤT CẢ các cột chỉ định."""
    mask = pd.Series(True, index=df.index)
    for c in cols:
        flag = f"{c}_flag"
        if flag in df.columns:
            mask &= df[flag] == 0
    return df[mask]

def filter_reliable(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Giữ lại các hàng có flag=0 hoặc 1 (gốc + imputed) cho các cột."""
    mask = pd.Series(True, index=df.index)
    for c in cols:
        flag = f"{c}_flag"
        if flag in df.columns:
            mask &= df[flag].isin([0, 1])
    return df[mask].dropna(subset=cols)

# ──────────────────────────── SIDEBAR ───────────────────────────
def render_sidebar(df):
    st.sidebar.markdown("## 🔧 Bộ lọc dữ liệu")

    stations = st.sidebar.multiselect(
        "🏭 Trạm quan trắc", STATIONS, default=STATIONS,
        format_func=lambda x: f"Trạm {x}",
    )
    mn, mx = df["Date"].min().date(), df["Date"].max().date()
    date_range = st.sidebar.date_input("📅 Khoảng thời gian", value=(mn, mx), min_value=mn, max_value=mx)

    season = st.sidebar.radio("🌦️ Mùa", ["Tất cả", "Mùa khô", "Mùa mưa"], horizontal=True)

    hour_range = st.sidebar.slider("🕐 Khung giờ", 0, 23, (0, 23))

    pollutant_focus = st.sidebar.multiselect(
        "🧪 Chất ô nhiễm hiển thị (Heatmap)", POLLUTANTS, default=POLLUTANTS,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Dữ liệu: HealthyAir HCMC 02/2021 – 06/2022")

    return stations, date_range, season, hour_range, pollutant_focus


# ──────────────────── SECTION 1 — KPI ──────────────────────────
def render_section1(df):
    st.markdown("### 📊 Tổng quan Khí tượng & Ô nhiễm")

    # Lọc dữ liệu đáng tin cậy cho từng metric KPI
    df_temp = filter_reliable(df, ["Temperature"])
    df_humid = filter_reliable(df, ["Humidity"])
    df_pm = filter_reliable(df, ["PM2.5"])

    dry = df_pm[df_pm["season"] == "Mùa khô"]
    wet = df_pm[df_pm["season"] == "Mùa mưa"]
    pm_dry = dry["PM2.5"].mean() if not dry.empty else 0
    pm_wet = wet["PM2.5"].mean() if not wet.empty else 0
    delta_pm = ((pm_dry - pm_wet) / pm_wet * 100) if pm_wet else 0

    # Tìm tương quan mạnh nhất (dùng dữ liệu reliable cho từng cặp)
    best_r, best_label = 0, ""
    for w in WEATHER:
        for p in POLLUTANTS:
            tmp = filter_original_multi(df, [w, p])[[w, p]]
            if len(tmp) > 10:
                r = tmp[w].corr(tmp[p])
                if abs(r) > abs(best_r):
                    best_r, best_label = r, f"{w[:4]}×{p}"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Nhiệt độ TB", f"{df_temp['Temperature'].mean():.1f} °C")
    c2.metric("💧 Độ ẩm TB", f"{df_humid['Humidity'].mean():.1f} %")
    c3.metric("🏜️ PM2.5 Khô vs Mưa", f"{pm_dry:.1f} / {pm_wet:.1f}", f"{delta_pm:+.1f}%")
    c4.metric("🔗 Tương quan mạnh nhất", best_label, f"r = {best_r:+.3f}")


# ──────────────────── SECTION 2 — HEATMAP ──────────────────────
def render_section2(df, pollutant_focus):
    st.markdown("### 🔥 Ma trận Tương quan: Thời tiết × Ô nhiễm")
    st.caption("Mức độ tương quan tuyến tính giữa Nhiệt độ & Độ ẩm với 6 chất ô nhiễm · Ô viền vàng: tương quan đáng kể (|r| ≥ 0.15)")

    cols_show = [p for p in POLLUTANTS if p in pollutant_focus]
    if not cols_show:
        st.warning("Chọn ít nhất 1 chất ô nhiễm.")
        return

    mat = np.zeros((2, len(cols_show)))
    for i, w in enumerate(WEATHER):
        for j, p in enumerate(cols_show):
            tmp = filter_original_multi(df, [w, p])[[w, p]]
            mat[i, j] = tmp[w].corr(tmp[p]) if len(tmp) > 10 else 0

    fig = go.Figure(go.Heatmap(
        z=mat, x=cols_show, y=["Nhiệt độ", "Độ ẩm"],
        colorscale="RdBu_r", zmid=0, zmin=-0.5, zmax=0.5,
        text=[[f"{v:+.3f}" for v in row] for row in mat],
        texttemplate="%{text}", textfont=dict(size=15, family="Segoe UI"),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>r = %{z:.3f}<extra></extra>",
        colorbar=dict(title="r"),
    ))

    shapes = []
    for i in range(2):
        for j in range(len(cols_show)):
            if abs(mat[i, j]) >= 0.15:
                shapes.append(dict(
                    type="rect", x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                    line=dict(color="#FFB703", width=3),
                ))

    fig.update_layout(
        shapes=shapes, height=260,
        margin=dict(l=80, r=30, t=20, b=40),
        font=dict(family="Segoe UI"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Insight callout — dynamic
    nghich, thuan, neutral = [], [], []
    for j, p in enumerate(cols_show):
        r_temp = mat[0, j]   # Temperature row
        r_humid = mat[1, j]  # Humidity row
        sig_temp = abs(r_temp) >= 0.15
        sig_humid = abs(r_humid) >= 0.15

        if not sig_temp and not sig_humid:
            neutral.append(p)
            continue

        details = []
        if sig_temp:
            details.append(f"Nhiệt độ r={r_temp:+.3f}")
        if sig_humid:
            details.append(f"Độ ẩm r={r_humid:+.3f}")
        entry = f"**{p}** ({', '.join(details)})"

        # Phân loại theo hướng tương quan trung bình của các cặp đáng kể
        sig_vals = [v for v, s in [(r_temp, sig_temp), (r_humid, sig_humid)] if s]
        if sum(sig_vals) / len(sig_vals) < 0:
            nghich.append(entry)
        else:
            thuan.append(entry)

    if nghich or thuan:
        parts = ["📌 **Thời tiết tác động có chọn lọc:**"]
        if nghich:
            parts.append(f"↘ Tương quan nghịch (thời tiết cao → ô nhiễm giảm): {' · '.join(nghich)}")
        if thuan:
            parts.append(f"↗ Tương quan thuận (thời tiết cao → ô nhiễm tăng): {' · '.join(thuan)}")
        if neutral:
            parts.append(f"↔ Gần như không ảnh hưởng: {', '.join(neutral)}")
        st.info("  \n".join(parts))


# ──────────────── SECTION 3 — DIURNAL CYCLES ───────────────────
def _diurnal_chart(hourly, weather_col, poll_col, title, caption_text):
    """Vẽ 1 chart normalized theo giờ cho 1 cặp weather-pollutant."""
    w_raw = hourly[weather_col]
    p_raw = hourly[poll_col]
    w_n, p_n = _norm(w_raw), _norm(p_raw)
    # r = w_raw.corr(p_raw)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly.index, y=w_n, mode="lines+markers", name=weather_col,
        line=dict(color=COLORS[weather_col], width=3), marker=dict(size=5),
        customdata=np.stack([w_raw.values], axis=-1),
        hovertemplate=(
            f"<b>{weather_col}</b><br>"
            "Giờ: %{x}h<br>Normalized: %{y:.2f}<br>"
            "Giá trị thật: %{customdata[0]:.1f}<extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=hourly.index, y=p_n, mode="lines+markers", name=poll_col,
        line=dict(color=COLORS[poll_col], width=3), marker=dict(size=5),
        customdata=np.stack([p_raw.values], axis=-1),
        hovertemplate=(
            f"<b>{poll_col}</b><br>"
            "Giờ: %{x}h<br>Normalized: %{y:.2f}<br>"
            "Giá trị thật: %{customdata[0]:.1f}<extra></extra>"
        ),
    ))
    #   (r = {r:+.3f})
    fig.update_layout(
        title=dict(text=f"{title}", font=dict(size=13)),
        xaxis=dict(title="Giờ", dtick=2, range=[-0.5, 23.5]),
        yaxis=dict(title="Normalized (0–1)", range=[-0.05, 1.1]),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        height=340, margin=dict(l=50, r=20, t=75, b=50),
        font=dict(family="Segoe UI"),
    )
    return fig, caption_text


def _diurnal_chart_3lines(hourly, w1, w2, poll, title, caption_text):
    """Vẽ chart normalized 3 đường: 2 weather + 1 pollutant."""
    raws = {w1: hourly[w1], w2: hourly[w2], poll: hourly[poll]}
    norms = {k: _norm(v) for k, v in raws.items()}

    fig = go.Figure()
    for var in [w1, w2, poll]:
        fig.add_trace(go.Scatter(
            x=hourly.index, y=norms[var], mode="lines+markers", name=var,
            line=dict(color=COLORS[var], width=3), marker=dict(size=5),
            customdata=np.stack([raws[var].values], axis=-1),
            hovertemplate=(
                f"<b>{var}</b><br>"
                "Giờ: %{x}h<br>Normalized: %{y:.2f}<br>"
                "Giá trị thật: %{customdata[0]:.1f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        xaxis=dict(title="Giờ", dtick=2, range=[-0.5, 23.5]),
        yaxis=dict(title="Normalized (0–1)", range=[-0.05, 1.1]),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        height=360, margin=dict(l=50, r=20, t=85, b=50),
        font=dict(family="Segoe UI"),
    )
    return fig, caption_text


def render_section3(df):
    st.markdown("### 🕐 Chu kỳ Ngày: Giải mã Nghịch lý")
    st.caption(
        "Mỗi biến được chuẩn hóa Min-Max (0–1) để so sánh xu hướng. "
        "**Di chuột** vào điểm để xem giá trị thật."
    )

    # Lọc dữ liệu original cho PM2.5 & O3 (Row 1)
    df_pm_o3 = filter_original_multi(df, ["Temperature", "Humidity", "PM2.5", "O3"])
    # Lọc dữ liệu original cho NO2 & SO2 (Row 2)
    df_no2 = filter_original_multi(df, ["Humidity", "NO2"])
    df_so2 = filter_original_multi(df, ["Temperature", "SO2"])

    hourly_pm_o3 = df_pm_o3.groupby("Hour")[WEATHER + POLLUTANTS].mean()
    hourly_no2 = df_no2.groupby("Hour")[WEATHER + POLLUTANTS].mean()
    hourly_so2 = df_so2.groupby("Hour")[WEATHER + POLLUTANTS].mean()

    # ── Row 1: PM2.5 ──
    st.markdown("#### 🔍 Nghịch lý PM2.5")
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        pm_peak_h = hourly_pm_o3["PM2.5"].idxmax()
        fig, cap = _diurnal_chart_3lines(
            hourly_pm_o3, "Temperature", "Humidity", "PM2.5",
            "Nhiệt độ, Độ ẩm & PM2.5 theo giờ",
            f"PM2.5 peak lúc {pm_peak_h}h khi nhiệt độ còn thấp và độ ẩm cao "
            f"— dấu hiệu giờ cao điểm sáng kết hợp nghịch nhiệt bề mặt giữ bụi, "
            f"không phải tác động trực tiếp của thời tiết."
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(cap)

    # ── Row 1 right: O3 ──
    with r1c2:
        o3_peak_h = hourly_pm_o3["O3"].idxmax()
        temp_peak_h = hourly_pm_o3["Temperature"].idxmax()
        lag = o3_peak_h - temp_peak_h
        fig, cap = _diurnal_chart_3lines(
            hourly_pm_o3, "Temperature", "Humidity", "O3",
            "Nhiệt độ, Độ ẩm & O3 theo giờ",
            f"O3 gần bằng 0 suốt đêm, peak lúc {o3_peak_h}h "
            f"— trễ hơn nhiệt độ ~{lag} tiếng do phản ứng quang hóa cần thời gian tích lũy. "
            f"Chính độ trễ này khiến Pearson r thấp dù O3 phụ thuộc rõ vào chu kỳ bức xạ mặt trời."
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(cap)

    # ── Row 2: NO2 & SO2 ──
    st.markdown("#### 🔍 Bất ngờ NO2 & SO2")
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        r_no2 = hourly_no2["Humidity"].corr(hourly_no2["NO2"])
        no2_trough_h = hourly_no2["NO2"].idxmin()
        fig, cap = _diurnal_chart(
            hourly_no2, "Humidity", "NO2",
            f"Độ ẩm & NO2 theo giờ",
            f"Hai đường gần trùng khít — cùng cao ban đêm, cùng chạm đáy vào khoảng {no2_trough_h}h. "
            f"Cơ chế kép: trưa nóng phá nghịch nhiệt → NO2 khuếch tán; "
            f"chiều tối nghịch nhiệt tái lập đúng giờ cao điểm → NO2 tích tụ cùng độ ẩm. "
            f"Không có tương quan nhân quả, chỉ phản ánh sự cộng hưởng."
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(cap)

    with r2c2:
        # SO2 × Temp: monthly thay vì hourly (r_monthly=0.703 giải thích rõ hơn)
        monthly_so2 = df_so2.groupby("month")[["Temperature", "SO2"]].mean().reindex(range(1, 13))
        x_months = [MONTH_LABELS[m] for m in range(1, 13)]
        t_raw = monthly_so2["Temperature"]
        s_raw = monthly_so2["SO2"]
        t_n, s_n = _norm(t_raw), _norm(s_raw)
        r_m = t_raw.corr(s_raw)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_months, y=t_n, mode="lines+markers", name="Temperature",
            line=dict(color=COLORS["Temperature"], width=3), marker=dict(size=6),
            customdata=np.stack([t_raw.values], axis=-1),
            hovertemplate=(
                "<b>Temperature</b><br>%{x}<br>"
                "Normalized: %{y:.2f}<br>Giá trị thật: %{customdata[0]:.1f} °C<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=x_months, y=s_n, mode="lines+markers", name="SO2",
            line=dict(color=COLORS["SO2"], width=3), marker=dict(size=6),
            customdata=np.stack([s_raw.values], axis=-1),
            hovertemplate=(
                "<b>SO2</b><br>%{x}<br>"
                "Normalized: %{y:.2f}<br>Giá trị thật: %{customdata[0]:.1f} µg/m³<extra></extra>"
            ),
        ))
        fig.update_layout(
            title=dict(text=f"Nhiệt độ & SO2 trung bình theo tháng (r = {r_m:+.3f})", font=dict(size=13)),
            xaxis=dict(title="Tháng"),
            yaxis=dict(title="Normalized (0–1)", range=[-0.05, 1.1]),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
            height=340, margin=dict(l=50, r=20, t=75, b=50),
            font=dict(family="Segoe UI"),
        )

        so2_peak_m = MONTH_LABELS[monthly_so2["SO2"].idxmax()]
        so2_trough_m = MONTH_LABELS[monthly_so2["SO2"].idxmin()]
        temp_peak_m = MONTH_LABELS[monthly_so2["Temperature"].idxmax()]
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"SO2 cao nhất vào {so2_peak_m}, thấp nhất vào {so2_trough_m}. "
            f"Nhìn chung xu hướng cùng chiều với nhiệt độ — phù hợp giả thuyết hoạt động công nghiệp tăng theo mùa khô. "
            f"Tuy nhiên {so2_trough_m} là ngoại lệ khi nhiệt độ tăng nhứng SO2 lại chạm đáy — "
            f"có thể do các yếu tố khác can thiệp (mưa lớn cuối mùa…). "
            f"Do đó, Không có tương quan trực tiếp giưa nhiệt độ và SO2 mà "
        )


# ──────────────── SECTION 4 — MONTHLY TREND ────────────────────
def render_section4(df):
    st.markdown("### 📅 Xu hướng Theo Tháng: PM2.5 & O3")
    st.caption("Kiểm tra liệu ô nhiễm có biến động theo mùa không — và nhiệt độ đóng vai trò gì trong đó.")

    # Lọc dữ liệu reliable cho từng biến trong monthly chart
    df_pm25 = filter_reliable(df, ["PM2.5", "Humidity"])
    df_o3 = filter_reliable(df, ["O3", "Temperature"])
    monthly_pm25 = df_pm25.groupby("month")[["PM2.5", "Humidity"]].mean().reindex(range(1, 13))
    monthly_o3 = df_o3.groupby("month")[["O3", "Temperature"]].mean().reindex(range(1, 13))
    x_labels = [MONTH_LABELS[m] for m in range(1, 13)]

    col1, col2 = st.columns(2)

    # ── PM2.5 by month ──
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_labels, y=monthly_pm25["PM2.5"], name="PM2.5",
            marker_color=COLORS["PM2.5"], opacity=0.85,
            hovertemplate="<b>%{x}</b><br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, y=monthly_pm25["Humidity"], name="Độ ẩm",
            yaxis="y2", mode="lines+markers",
            line=dict(color=COLORS["Humidity"], width=2, dash="dot"),
            marker=dict(size=6),
            hovertemplate="<b>%{x}</b><br>Humidity: %{y:.1f} %<extra></extra>",
        ))
        # Season shading
        fig.add_vrect(x0=-0.5, x1=3.5, fillcolor="rgba(186,117,23,0.08)", line_width=0, layer="below")
        fig.add_vrect(x0=3.5, x1=10.5, fillcolor="rgba(29,158,117,0.08)", line_width=0, layer="below")
        fig.add_vrect(x0=10.5, x1=11.5, fillcolor="rgba(186,117,23,0.08)", line_width=0, layer="below")
        fig.add_annotation(x=1.5, y=1.07, yref="paper", text="Mùa khô", showarrow=False, font=dict(size=10, color="#5F5F5F"))
        fig.add_annotation(x=7, y=1.07, yref="paper", text="Mùa mưa", showarrow=False, font=dict(size=10, color="#5F5F5F"))
        fig.add_annotation(x=11, y=1.07, yref="paper", text="Mùa khô", showarrow=False, font=dict(size=10, color="#5F5F5F"))

        fig.update_layout(
            title=dict(text="PM2.5 trung bình theo tháng (µg/m³) & Độ ẩm (%)", font=dict(size=14)),
            xaxis=dict(title="Tháng"),
            yaxis=dict(title="PM2.5 (µg/m³)"),
            yaxis2=dict(title="Độ ẩm (%)", overlaying="y", side="right", showgrid=False, range=[40, 100]),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            height=400, margin=dict(l=50, r=60, t=70, b=70),
            font=dict(family="Segoe UI"),
        )
        pm_peak_m = MONTH_LABELS[monthly_pm25["PM2.5"].idxmax()]
        pm_trough_m = MONTH_LABELS[monthly_pm25["PM2.5"].idxmin()]
        humid_peak_m = MONTH_LABELS[monthly_pm25["Humidity"].idxmax()]
        humid_min_v = monthly_pm25["Humidity"].min()
        humid_max_v = monthly_pm25["Humidity"].max()
        pm_ratio = monthly_pm25["PM2.5"].max() / monthly_pm25["PM2.5"].min() if monthly_pm25["PM2.5"].min() > 0 else 0
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"PM2.5 và Độ ẩm thể hiện xu hướng **ngược chiều** rõ rệt: PM2.5 cao nhất vào {pm_peak_m} (mùa khô) khi độ ẩm thấp, "
            f"và chạm đáy vào {pm_trough_m} (mùa mưa), cũng là giai đoạn độ ẩm đạt đỉnh. "
            f"Sự đối nghịch này phản ánh tác động **'rửa trôi'** của tự nhiên: các tháng mưa nhiều làm tăng độ ẩm đồng thời gột rửa bụi bẩn trong không khí."
        )

    # ── O3 by month ──
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_labels, y=monthly_o3["O3"], name="O3",
            marker_color=COLORS["O3"], opacity=0.85,
            hovertemplate="<b>%{x}</b><br>O3: %{y:.1f} µg/m³<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, y=monthly_o3["Temperature"], name="Nhiệt độ",
            yaxis="y2", mode="lines+markers",
            line=dict(color=COLORS["Temperature"], width=2, dash="dot"),
            marker=dict(size=6),
            hovertemplate="<b>%{x}</b><br>Temp: %{y:.1f} °C<extra></extra>",
        ))
        fig.add_vrect(x0=-0.5, x1=3.5, fillcolor="rgba(186,117,23,0.08)", line_width=0, layer="below")
        fig.add_vrect(x0=3.5, x1=10.5, fillcolor="rgba(29,158,117,0.08)", line_width=0, layer="below")
        fig.add_vrect(x0=10.5, x1=11.5, fillcolor="rgba(186,117,23,0.08)", line_width=0, layer="below")
        fig.add_annotation(x=1.5, y=1.07, yref="paper", text="Mùa khô", showarrow=False, font=dict(size=10, color="#5F5F5F"))
        fig.add_annotation(x=7, y=1.07, yref="paper", text="Mùa mưa", showarrow=False, font=dict(size=10, color="#5F5F5F"))
        fig.add_annotation(x=11, y=1.07, yref="paper", text="Mùa khô", showarrow=False, font=dict(size=10, color="#5F5F5F"))

        fig.update_layout(
            title=dict(text="O3 trung bình theo tháng (µg/m³) & Nhiệt độ (°C)", font=dict(size=14)),
            xaxis=dict(title="Tháng"),
            yaxis=dict(title="O3 (µg/m³)"),
            yaxis2=dict(title="Nhiệt độ (°C)", overlaying="y", side="right", showgrid=False, range=[24, 32]),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            height=400, margin=dict(l=50, r=60, t=70, b=70),
            font=dict(family="Segoe UI"),
        )
        o3_peak_m = MONTH_LABELS[monthly_o3["O3"].idxmax()]
        o3_trough_m = MONTH_LABELS[monthly_o3["O3"].idxmin()]
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"O3 cao nhất vào {o3_peak_m} (mùa khô), thấp nhất {o3_trough_m} (mùa mưa). "
            f"O3 là khí, không bị mưa rửa trôi; O3 thấp vào mùa mưa vì mây dày "
            f"che khuất ánh sáng mặt trời, làm phản ứng quang hóa suy yếu. "
            f"Nhiệt độ gần phẳng quanh năm → không giải thích được biên độ dao động O3."
        )


# ──────────────── CONCLUSION BOX ───────────────────────────────
def render_conclusion():
    st.markdown("---")
    st.markdown("### 💡 Kết luận")
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #EEF4F8 0%, #F4F8FB 100%);
            border-left: 5px solid #1F8A70;
            border-radius: 8px;
            padding: 24px 28px;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #16324F;
            line-height: 1.8;
        ">
            <h4 style="margin-top:0; color:#1F8A70;">
                🌤️ Thời tiết là điều kiện nền — Nguồn phát thải mới là nguyên nhân chính
            </h4>
            <ol style="margin-bottom: 0;">
                <li>
                    <b>Tương quan tổng thể rất yếu</b>: Không có cặp Thời tiết × Ô nhiễm nào
                    vượt |r| = 0.35. Ở khí hậu nhiệt đới TP.HCM, nhiệt độ và độ ẩm dao động
                    hẹp quanh năm nên không đủ tạo tín hiệu tương quan mạnh với ô nhiễm.
                </li>
                <li>
                    <b>Chu kỳ ngày là yếu tố gây nhiễu</b>: PM2.5 peak sáng sớm (giờ cao điểm),
                    O3 peak chiều (trễ quang hóa 3–5h so với Nhiệt độ peak), NO2 và SO2 tăng theo hoạt động
                    giao thông và công nghiệp — tất cả trùng với chu kỳ nhiệt/ẩm nhưng nguyên nhân thực sự
                    là <em>hoạt động giao thông và công nghiệp</em>, không phải thời tiết.
                </li>
                <li>
                    <b>Mùa khô ô nhiễm hơn 34%</b> — nhưng nhiệt độ 2 mùa gần như bằng nhau.
                    Với PM2.5: yếu tố quyết định là <em>thiếu mưa rửa trôi</em>
                    và nghịch nhiệt giữ bụi lơ lửng. Với O3: mùa mưa nhiều mây che khuất
                    ánh sáng mặt trời làm <em>phản ứng quang hóa suy yếu</em> — hai chất cùng pattern
                    mùa nhưng cơ chế hoàn toàn khác nhau.
                </li>
                <li>
                    <b>Hàm ý</b>: Chính sách giảm ô nhiễm tại TP.HCM cần tập trung vào
                    <em>kiểm soát nguồn phát thải</em> (giao thông, công nghiệp) thay vì
                    chờ đợi điều kiện thời tiết thuận lợi — vì thời tiết chỉ điều tiết
                    mức độ tích tụ, không quyết định lượng phát thải.
                </li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────── MAIN ─────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Goal 3 — Thời tiết & Ô nhiễm | HCMC Air Quality",
        page_icon="🌤️",
        layout="wide",
    )
    st.markdown(
        "<h1 style='font-family:Segoe UI; color:#16324F;'>"
        "🌤️ Mục tiêu 3 — Tác động của Thời tiết đến Ô nhiễm"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.caption("Dashboard phân tích mối liên hệ giữa nhiệt độ, độ ẩm và nồng độ các chất ô nhiễm tại TP.HCM (02/2021 – 06/2022)")
    st.markdown("---")

    # Load data
    if not DATA_PATH.exists():
        st.error(f"Không tìm thấy file dữ liệu: {DATA_PATH}")
        return
    df = load_data()

    # Sidebar filters
    stations, date_range, season, hour_range, poll_focus = render_sidebar(df)
    if not stations:
        st.warning("Vui lòng chọn ít nhất 1 trạm.")
        return

    filtered = apply_filters(df, stations, date_range, season, hour_range)
    if filtered.empty:
        st.warning("Không có dữ liệu sau khi lọc.")
        return

    st.sidebar.metric("📊 Số bản ghi", f"{len(filtered):,}")

    # Render sections
    render_section1(filtered)
    st.markdown("---")
    render_section2(filtered, poll_focus)
    st.markdown("---")
    render_section3(filtered)
    st.markdown("---")
    render_section4(filtered)
    render_conclusion()


if __name__ == "__main__":
    main()
