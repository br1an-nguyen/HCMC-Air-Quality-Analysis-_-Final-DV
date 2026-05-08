from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "cleaned" / "Air_Quality_HCMC_Cleaned.csv"

# WHO 2021 annual guideline for PM2.5
PM25_SAFE_THRESHOLD = 15.0  # µg/m³

# ── Color mapping ──
COLOR_PM25    = "#B23A2F"
COLOR_TSP     = "#6F1D1B"
COLOR_SAFE    = "#2A9D8F"
COLOR_HAZARDOUS = "#E63946"
COLOR_HIGHLIGHT = "#FFB703"

HEALTH_RISK_COLORS  = {"Safe": COLOR_SAFE, "Hazardous": COLOR_HAZARDOUS}
HEALTH_RISK_DISPLAY = {"Safe": "An toàn", "Hazardous": "Nguy hại"}

WEEKDAY_ORDER_VI = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
WEEKDAY_MAP = {
    0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4",
    3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật",
}

# ── Theme tokens — khớp dashboard_design_format.md ──
CANVAS_BG     = "#F4F8FB"
CARD_BG       = "#FFFFFF"
TEXT_PRIMARY  = "#16324F"
TEXT_SECONDARY= "#4F6B7A"
GRIDLINE      = "#E5EEF3"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def _build_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo cột `datetime` từ `Date` + `Hour`."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    hour_str = (
        df["Hour"].astype(str).str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(2)
    )
    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str).str.strip() + " " + hour_str + ":00:00",
        errors="coerce",
    )
    return df


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    """Đọc CSV, chuẩn hóa thời gian, feature engineering."""
    df = pd.read_csv(path)
    df = _build_datetime(df)
    df = df.dropna(subset=["datetime"])
    df = df.sort_values(["Station_No", "datetime"]).reset_index(drop=True)

    # ── Feature Engineering ──
    # PM25_TSP_Ratio: guard chia 0 / NaN
    df["PM25_TSP_Ratio"] = np.where(
        (df["TSP"].notna()) & (df["TSP"] > 0) & (df["PM2.5"].notna()),
        df["PM2.5"] / df["TSP"],
        np.nan,
    )

    # Health_Risk: phân loại theo ngưỡng tham chiếu WHO
    df["Health_Risk"] = pd.Series("Safe", index=df.index).where(
        df["PM2.5"] <= PM25_SAFE_THRESHOLD, other="Hazardous"
    )
    df.loc[df["PM2.5"].isna(), "Health_Risk"] = np.nan

    # Cột phụ trợ
    df["DayOfWeek"] = df["datetime"].dt.dayofweek.map(WEEKDAY_MAP)
    df["Hour_dt"]   = df["datetime"].dt.hour   # dùng cho heatmap

    return df


# ─────────────────────────────────────────────────────────────────────────────
# SHARED LAYOUT HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _base_layout(**overrides) -> dict:
    """Layout mặc định cho mọi Plotly figure."""
    defaults = dict(
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(family="Segoe UI, Arial", color=TEXT_PRIMARY, size=12),
        xaxis=dict(gridcolor=GRIDLINE, showgrid=True),
        yaxis=dict(gridcolor=GRIDLINE, showgrid=True),
        margin=dict(l=55, r=30, t=65, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor=CARD_BG, font_size=12),
    )
    defaults.update(overrides)
    return defaults


def _base_layout_no_axes(**overrides) -> dict:
    """Layout mặc định không có xaxis/yaxis (cho Pie/Donut)."""
    d = {k: v for k, v in _base_layout().items() if k not in ("xaxis", "yaxis")}
    d.update(overrides)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# CHART FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def V_P06_Health_Risk_Donut(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart: tỷ lệ % số giờ An toàn vs Nguy hại (toàn bộ dữ liệu đã lọc
    station + date, KHÔNG lọc theo health_risk để phản ánh bức tranh tổng thể).
    """
    counts = df["Health_Risk"].value_counts()
    labels  = counts.index.tolist()
    display = [HEALTH_RISK_DISPLAY.get(l, l) for l in labels]
    values  = counts.values.tolist()
    colors  = [HEALTH_RISK_COLORS.get(l, "#888") for l in labels]

    total     = sum(values)
    haz_count = counts.get("Hazardous", 0)
    haz_pct   = (haz_count / total * 100) if total > 0 else 0

    fig = go.Figure(go.Pie(
        labels=display,
        values=values,
        hole=0.58,
        marker=dict(colors=colors, line=dict(color=CARD_BG, width=2)),
        textinfo="percent+label",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Số giờ: %{value:,}<br>Tỷ lệ: %{percent}<extra></extra>",
        sort=False,
    ))
    fig.update_layout(
        **_base_layout_no_axes(
            title=dict(text="Tỷ lệ giờ An toàn / Nguy hại", font=dict(size=15)),
            showlegend=True,
            height=380,
        )
    )
    return fig


def V_P06_Station_Risk_Bar(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart nằm ngang: % giờ nguy hại theo từng trạm, sort giảm dần.
    Trả lời câu hỏi "Khu vực nào nguy hiểm hơn?" — phần cốt lõi của Goal 5 mới.
    """
    valid = df[df["Health_Risk"].notna()].copy()
    stn = (
        valid.groupby("Station_No")["Health_Risk"]
        .value_counts()
        .unstack()
        .fillna(0)
    )
    stn["total"]   = stn.sum(axis=1)
    stn["haz_pct"] = stn.get("Hazardous", 0) / stn["total"] * 100
    stn["safe_pct"]= stn.get("Safe", 0)      / stn["total"] * 100
    stn = stn.sort_values("haz_pct", ascending=True).reset_index()
    stn["label"] = "Trạm " + stn["Station_No"].astype(str)

    avg_haz = stn["haz_pct"].mean()

    fig = go.Figure()

    # Bar nguy hại
    fig.add_trace(go.Bar(
        x=stn["haz_pct"],
        y=stn["label"],
        orientation="h",
        name="Nguy hại",
        marker=dict(
            color=stn["haz_pct"],
            colorscale=[[0, "#FCBBA1"], [0.5, "#FB6A4A"], [1.0, COLOR_HAZARDOUS]],
            showscale=False,
        ),
        text=[f"{v:.1f}%" for v in stn["haz_pct"]],
        textposition="outside",
        textfont=dict(color=TEXT_PRIMARY, size=12),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Phần trăm giờ nguy hại: %{x:.1f}%<br>"
            "Số giờ nguy hại: %{customdata[0]:,}<br>"
            "Tổng giờ: %{customdata[1]:,}<extra></extra>"
        ),
        customdata=list(zip(
            stn.get("Hazardous", pd.Series([0]*len(stn))).astype(int),
            stn["total"].astype(int),
        )),
    ))

    # Đường trung bình toàn hệ thống
    fig.add_vline(
        x=avg_haz,
        line_dash="dash", line_color=TEXT_SECONDARY, line_width=1.5,
        annotation=dict(
            text=f"TB: {avg_haz:.1f}%",
            font=dict(color=TEXT_SECONDARY, size=11),
            bgcolor=CARD_BG,
        ),
        annotation_position="top right",
    )

    fig.update_layout(
        **_base_layout(
            title=dict(text="Phần trăm giờ nguy hại (PM2.5 > 15 µg/m³) theo trạm quan trắc", font=dict(size=15)),
            xaxis=dict(
                title="Phần trăm giờ quan trắc",
                range=[0, 105],
                gridcolor=GRIDLINE,
                showgrid=True,
                ticksuffix="%",
            ),
            yaxis=dict(title="", gridcolor=GRIDLINE, showgrid=False),
            height=330,
            showlegend=False,
        )
    )
    return fig


def V_P06_PM25_TSP_Ratio_Boxplot(df: pd.DataFrame) -> go.Figure:
    """
    Boxplot phân phối PM2.5/TSP theo trạm.
    Nhận df_pre_risk (đã lọc station+date, CHƯA lọc health_risk)
    để phân phối không bị lệch theo chiều nào.
    """
    plot_df = df.dropna(subset=["PM2.5", "TSP"]).copy()
    plot_df["Station_Label"] = "Trạm " + plot_df["Station_No"].astype(str)

    fig = px.box(
        plot_df,
        x="Station_Label",
        y="PM25_TSP_Ratio",
        color_discrete_sequence=[COLOR_TSP],   # FIX: dùng màu TSP đúng #6F1D1B
        points="outliers",
        labels={
            "Station_Label":   "Trạm quan trắc",
            "PM25_TSP_Ratio":  "Tỷ lệ PM2.5 / TSP",
        },
    )
    fig.update_traces(
        marker=dict(color=COLOR_PM25, opacity=0.45, size=3),
        line=dict(color=COLOR_TSP),
        fillcolor="rgba(111, 29, 27, 0.12)",
    )

    # ĐÃ XÓA: Đường ngưỡng tham chiếu 0.5 (fig.add_hline)

    fig.update_layout(
        **_base_layout(
            title=dict(text="Phân bố tỷ lệ PM2.5 / TSP theo trạm quan trắc", font=dict(size=15)),
            xaxis_title="Trạm quan trắc",
            yaxis_title="Tỷ lệ PM2.5 / TSP",
            height=380,
            showlegend=False,
        )
    )
    return fig


def V_P06_Hourly_PM25_TSP_Ratio_Line(df: pd.DataFrame) -> go.Figure:
    """
    Line chart: PM2.5/TSP trung bình theo giờ trong ngày.
    Nhận df_pre_risk (CHƯA lọc health_risk) để không bị lệch.
    Dùng Hour_dt (từ datetime) thay vì cột Hour gốc để nhất quán.
    """
    hourly_avg = df.groupby("Hour_dt")["PM25_TSP_Ratio"].mean().reset_index()
    hourly_avg.rename(columns={"Hour_dt": "Hour"}, inplace=True)

    fig = go.Figure()

    # Vùng tô bóng nhẹ dưới đường
    fig.add_trace(go.Scatter(
        x=hourly_avg["Hour"],
        y=hourly_avg["PM25_TSP_Ratio"],
        mode="none",
        fill="tozeroy",
        fillcolor=f"rgba(178, 58, 47, 0.08)",
        showlegend=False,
        hoverinfo="skip",
    ))

    # Đường chính
    fig.add_trace(go.Scatter(
        x=hourly_avg["Hour"],
        y=hourly_avg["PM25_TSP_Ratio"],
        mode="lines+markers",
        name="Tỷ lệ trung bình",
        line=dict(color=COLOR_PM25, width=3, shape="spline"),
        marker=dict(size=7, color=COLOR_PM25),
        hovertemplate="<b>%{x}:00</b><br>Tỷ lệ TB: %{y:.4f}<extra></extra>",
    ))

    # ĐÃ THÊM LẠI: Đường ngưỡng tham chiếu 0.5 (Tạo thành Trace để đưa lên Legend)
    fig.add_trace(go.Scatter(
        x=[hourly_avg["Hour"].min(), hourly_avg["Hour"].max()],
        y=[0.5, 0.5],
        mode="lines",
        name="Ngưỡng tham chiếu (0.5)",
        line=dict(color=TEXT_SECONDARY, width=2, dash="dash"),
        hoverinfo="skip"
    ))

    # --- XỬ LÝ SCALE TRỤC Y ---
    # Lấy giá trị min/max thực tế của dữ liệu
    y_min = hourly_avg["PM25_TSP_Ratio"].min()
    y_max = hourly_avg["PM25_TSP_Ratio"].max()
    
    # Thiết lập giới hạn: Mở rộng thêm 0.05 so với dữ liệu thực tế cho thoáng,
    # và luôn đảm bảo giới hạn trên bao phủ được ngưỡng 0.5
    y_lower = max(0.0, y_min - 0.05)
    y_upper = max(0.52, y_max + 0.05)

    fig.update_layout(
        **_base_layout(
            title=dict(text="Diễn biến tỷ lệ PM2.5 / TSP trung bình theo giờ", font=dict(size=15)),
            xaxis=dict(
                title="Giờ trong ngày",
                dtick=1,
                range=[-0.5, 23.5],
                gridcolor=GRIDLINE,
                showgrid=True,
            ),
            yaxis=dict(
                title="Tỷ lệ PM2.5 / TSP",
                gridcolor=GRIDLINE,
                showgrid=True,
                range=[y_lower, y_upper], # Ép khoảng scale mới vào trục Y
                dtick=0.05,               # Rút ngắn các bước nhảy lưới để nhìn rõ biên độ
            ),
            height=380,
            showlegend=True, # Bật Legend để hiển thị "Tỷ lệ trung bình" và "Ngưỡng tham chiếu" trên cùng
        )
    )
    return fig


def V_P06_Hazardous_Heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap: Hour (0-23) × DayOfWeek — tần suất giờ PM2.5 nguy hại.
    Nhận df_pre_risk (đã lọc station+date, CHƯA lọc health_risk).
    Dùng Hour_dt (từ datetime) để nhất quán với heatmap.
    """
    haz = df[df["Health_Risk"] == "Hazardous"].copy()

    pivot = (
        haz.groupby(["DayOfWeek", "Hour_dt"])
        .size()
        .reset_index(name="Count")
        .pivot(index="DayOfWeek", columns="Hour_dt", values="Count")
        .reindex(index=WEEKDAY_ORDER_VI, columns=range(24))
        .fillna(0)
    )

    custom_scale = [
        [0.0,  "#FFF5F0"],
        [0.25, "#FCBBA1"],
        [0.5,  "#FB6A4A"],
        [0.75, "#CB181D"],
        [1.0,  "#67000D"],
    ]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(range(24)),
        y=WEEKDAY_ORDER_VI,
        colorscale=custom_scale,
        colorbar=dict(title="Số lần<br>Nguy hại", title_font=dict(size=11)),
        hovertemplate=(
            "<b>%{y}</b> — %{x}:00<br>"
            "Số lần nguy hại: %{z:,.0f}<extra></extra>"
        ),
    ))

    # Đánh dấu ô đỉnh cao nhất
    if pivot.values.max() > 0:
        max_val = pivot.values.max()
        max_row, max_col = np.unravel_index(pivot.values.argmax(), pivot.values.shape)
        fig.add_shape(
            type="rect",
            x0=max_col - 0.5, x1=max_col + 0.5,
            y0=max_row - 0.5, y1=max_row + 0.5,
            line=dict(color=COLOR_HIGHLIGHT, width=2.5),
            fillcolor="rgba(0,0,0,0)",
        )
        fig.add_annotation(
            x=max_col, y=max_row,
            text=f"Đỉnh: {int(max_val)}",
            showarrow=True, arrowhead=2, arrowcolor=COLOR_HIGHLIGHT,
            font=dict(size=11, color=COLOR_HIGHLIGHT, family="Segoe UI"),
            bgcolor="rgba(22,50,79,0.85)", borderpad=4,
            ax=40, ay=-30,
        )

    fig.update_layout(
        **_base_layout_no_axes(
            title=dict(
                text="Tần suất giờ nguy hại theo ngày trong tuần và khung giờ",
                font=dict(size=15),
            ),
            xaxis=dict(
                title="Giờ trong ngày",
                dtick=1,
                gridcolor=GRIDLINE,
                showgrid=False,
            ),
            yaxis=dict(
                title="Ngày trong tuần",
                gridcolor=GRIDLINE,
                showgrid=False,
                autorange="reversed",
            ),
            height=420,
        )
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PAGE RENDER
# ─────────────────────────────────────────────────────────────────────────────

def reset_filters(default_stations, default_start, default_end):
    """Hàm callback gán trực tiếp giá trị mặc định vào session state."""
    st.session_state["P06_station"] = default_stations
    st.session_state["P06_date"] = (default_start, default_end)

def render_P06_Health_Risk_Profiling(file_path: str | None = None) -> None:
    """Render toàn bộ trang P06 — Health Risk & Pollutant Profiling."""

    # ── Custom CSS ──
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {CANVAS_BG}; }}
        section[data-testid="stSidebar"] {{
            background-color: {CARD_BG};
            border-right: 1px solid {GRIDLINE};
        }}
        div[data-testid="stMetric"] {{
            background: {CARD_BG};
            border: 1px solid {GRIDLINE};
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}
        div[data-testid="stMetric"] label {{
            color: {TEXT_SECONDARY};
            font-size: 13px;
        }}
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            font-size: 28px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        .section-divider {{
            border: none;
            border-top: 1px solid {GRIDLINE};
            margin: 24px 0 18px 0;
        }}
    </style>
    """, unsafe_allow_html=True)

    # ── Tiêu đề trang ──
    st.markdown(
        f"<h1 style='color:{TEXT_PRIMARY};font-family:Segoe UI,Arial;margin-bottom:2px;'>"
        "Mục tiêu 5: Phân tích Rủi ro Sức khỏe và Đặc tính Nguồn phát Bụi</h1>",
        unsafe_allow_html=True,
    )

    # ── Load data ──
    data_path = file_path or str(DEFAULT_DATA_PATH)
    if not Path(data_path).exists():
        st.error(f"Không tìm thấy tập tin `{data_path}`. Vui lòng kiểm tra lại đường dẫn.")
        return

    with st.spinner("Đang tải dữ liệu…"):
        df_all = load_data(data_path)

    if df_all.empty:
        st.warning("Không có dữ liệu hợp lệ.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR — Bộ lọc
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### Bộ lọc dữ liệu")

        all_stations = sorted(df_all["Station_No"].unique().tolist())
        sel_stations: list = st.multiselect(
            "Chọn trạm quan trắc",
            options=all_stations,
            default=all_stations,
            format_func=lambda x: f"Trạm {x}",
            key="P06_station",
        )

        min_d = df_all["datetime"].dt.date.min()
        max_d = df_all["datetime"].dt.date.max()
        sel_range = st.date_input(
            "Khoảng thời gian",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
            key="P06_date",
        )

        # Truyền trực tiếp các giá trị gốc vào hàm callback
        st.button(
            "Đặt lại bộ lọc", 
            on_click=reset_filters, 
            args=(all_stations, min_d, max_d)
        )


    # ── Validate filter ──
    if isinstance(sel_range, (list, tuple)):
        if len(sel_range) == 2:
            d_start, d_end = sel_range
        elif len(sel_range) == 1:
            # Dừng hệ thống và hiển thị thông báo yêu cầu chọn ngày kết thúc
            st.info("Vui lòng chọn ngày kết thúc trong bộ lọc khoảng thời gian để xem dữ liệu.")
            return
        else:
            d_start, d_end = min_d, max_d
    else:
        d_start, d_end = sel_range, sel_range

    if not sel_stations:
        st.warning("Vui lòng chọn ít nhất một trạm.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # TẠO TẬP DỮ LIỆU df_pre_risk
    # ─────────────────────────────────────────────────────────────────────────
    # Tối ưu hóa: Chuyển đổi d_start và d_end sang pd.Timestamp để so sánh trực tiếp 
    # với cột "datetime", lấy trọn vẹn dữ liệu đến 23:59:59 của ngày kết thúc.
    start_ts = pd.to_datetime(d_start)
    end_ts = pd.to_datetime(d_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    mask_station_date = (
        (df_all["Station_No"].isin(sel_stations))
        & (df_all["datetime"] >= start_ts)
        & (df_all["datetime"] <= end_ts)
        & (df_all["Health_Risk"].notna())
    )
    df_pre_risk: pd.DataFrame = df_all[mask_station_date].copy()

    
    if df_pre_risk.empty:
        st.warning("Không có dữ liệu trong khoảng đã chọn.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # KPI CARDS — TOP ROW
    # ─────────────────────────────────────────────────────────────────────────
    # Lấy tổng số giờ (số dòng dữ liệu hợp lệ)
    total_hours    = len(df_pre_risk)

    # Tính toán tổng nồng độ cho PM2.5 và TSP
    total_pm25     = df_pre_risk["PM2.5"].sum()
    total_tsp      = df_pre_risk["TSP"].sum()

    ratio_valid    = df_pre_risk["PM25_TSP_Ratio"].dropna()
    avg_ratio      = ratio_valid.mean() if not ratio_valid.empty else 0

    # Chia thành 4 cột cho các chỉ số
    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Tổng nồng độ PM2.5",
        f"{total_pm25:,.0f}",
        help="Tổng nồng độ bụi mịn PM2.5 tích lũy trong khoảng thời gian đã lọc (µg/m³)"
    )

    k2.metric(
        "Tổng nồng độ TSP",
        f"{total_tsp:,.0f}",
        help="Tổng nồng độ tổng bụi lơ lửng TSP tích lũy trong khoảng thời gian đã lọc (µg/m³)"
    )

    k3.metric(
        "Tổng số giờ quan trắc",
        f"{total_hours:,}",
        help="Tổng số giờ có dữ liệu hợp lệ trong khoảng thời gian và khu vực đã chọn"
    )

    k4.metric(
        "Tỷ lệ PM2.5/TSP TB",
        f"{avg_ratio:.3f}",
        help="Tỷ lệ PM2.5/TSP trung bình — phản ánh mức độ bụi mịn trong tổng bụi lơ lửng"
    )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ROW 1 — Donut + Station Bar
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Tổng quan rủi ro và phân bố theo khu vực")

    col_donut, col_bar = st.columns(2)
    with col_donut:
        st.plotly_chart(
            V_P06_Health_Risk_Donut(df_pre_risk),
            use_container_width=True,
        )
    with col_bar:
        st.plotly_chart(
            V_P06_Station_Risk_Bar(df_pre_risk),
            use_container_width=True,
        )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ROW 2 — Boxplot + Line chart (đều dùng df_pre_risk — FIX BUG)
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Đặc tính nguồn phát bụi và Tỷ lệ PM2.5 / TSP")

    col_box, col_line = st.columns(2)
    with col_box:
        # FIX: dùng df_pre_risk thay vì df_display
        st.plotly_chart(
            V_P06_PM25_TSP_Ratio_Boxplot(df_pre_risk),
            use_container_width=True,
        )
    with col_line:
        # FIX: dùng df_pre_risk thay vì df_display
        st.plotly_chart(
            V_P06_Hourly_PM25_TSP_Ratio_Line(df_pre_risk),
            use_container_width=True,
        )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ROW 3 — Heatmap (dùng df_pre_risk)
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Tần suất vượt ngưỡng theo khung giờ và ngày trong tuần")
    st.plotly_chart(
        V_P06_Hazardous_Heatmap(df_pre_risk),
        use_container_width=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Dashboard Goal 5",
        page_icon="",
        layout="wide",
    )
    render_P06_Health_Risk_Profiling()


if __name__ == "__main__":
    main()