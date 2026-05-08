from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# HẰNG SỐ
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "cleaned" / "Air_Quality_HCMC_Cleaned.csv"

# Ngưỡng an toàn PM2.5 theo khuyến cáo WHO (trung bình 24 giờ)
PM25_SAFE_THRESHOLD = 15.0  # µg/m³

# ── Ánh xạ màu sắc ──
COLOR_PM25      = "#B23A2F"
COLOR_SAFE      = "#2A9D8F"
COLOR_HAZARDOUS = "#E63946"
COLOR_HIGHLIGHT = "#FFB703"

HEALTH_RISK_COLORS  = {"Safe": COLOR_SAFE, "Hazardous": COLOR_HAZARDOUS}
HEALTH_RISK_DISPLAY = {"Safe": "An toàn", "Hazardous": "Nguy hại"}

WEEKDAY_ORDER_VI = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

# ── Token giao diện ──
CANVAS_BG      = "#F4F8FB"
CARD_BG        = "#FFFFFF"
TEXT_PRIMARY   = "#16324F"
TEXT_SECONDARY = "#4F6B7A"
GRIDLINE       = "#E5EEF3"


# ─────────────────────────────────────────────────────────────────────────────
# TẢI DỮ LIỆU
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
    """Đọc CSV, chuẩn hóa thời gian. Không tạo biến phái sinh TSP."""
    df = pd.read_csv(path)
    df = _build_datetime(df)
    df = df.dropna(subset=["datetime"])
    df = df.sort_values(["Station_No", "datetime"]).reset_index(drop=True)
    # Chuyển đổi cột Date sang kiểu date thuần túy để hỗ trợ groupby theo ngày
    df["Date"] = df["datetime"].dt.date
    return df


# ─────────────────────────────────────────────────────────────────────────────
# BỐ CỤC MẶC ĐỊNH
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
# HÀM VẼ BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────────────────

def Health_Risk_Donut(df_city_daily: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ Donut: tỷ lệ phần trăm số ngày An toàn và Nguy hại
    trên phạm vi toàn thành phố (df_city_daily).
    """
    counts = df_city_daily["Health_Risk"].value_counts()
    labels  = counts.index.tolist()
    display = [HEALTH_RISK_DISPLAY.get(l, l) for l in labels]
    values  = counts.values.tolist()
    colors  = [HEALTH_RISK_COLORS.get(l, "#888") for l in labels]

    fig = go.Figure(go.Pie(
        labels=display, values=values, hole=0.58,
        marker=dict(colors=colors, line=dict(color=CARD_BG, width=2)),
        textinfo="percent+label", textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Số ngày: %{value:,}<br>Tỷ lệ: %{percent}<extra></extra>",
        sort=False,
    ))
    fig.update_layout(**_base_layout_no_axes(
        title=dict(text="Tỷ lệ ngày An toàn và Nguy hại", font=dict(size=15)),
        showlegend=True, height=380,
    ))
    return fig


def Station_Risk_Bar(df_station_daily: pd.DataFrame) -> go.Figure:
    """
    Bar chart nằm ngang: phần trăm số ngày nguy hại theo từng trạm,
    sắp xếp giảm dần. Sử dụng df_station_daily (trung bình ngày cấp trạm).
    """
    valid = df_station_daily[df_station_daily["Health_Risk"].notna()].copy()
    stn = valid.groupby("Station_No")["Health_Risk"].value_counts().unstack().fillna(0)
    stn["total"]   = stn.sum(axis=1)
    stn["haz_pct"] = stn.get("Hazardous", 0) / stn["total"] * 100
    stn = stn.sort_values("haz_pct", ascending=True).reset_index()
    stn["label"] = "Trạm " + stn["Station_No"].astype(str)
    avg_haz = stn["haz_pct"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stn["haz_pct"], y=stn["label"], orientation="h", name="Nguy hại",
        marker=dict(
            color=stn["haz_pct"],
            colorscale=[[0, "#FCBBA1"], [0.5, "#FB6A4A"], [1.0, COLOR_HAZARDOUS]],
            showscale=False,
        ),
        text=[f"{v:.1f}%" for v in stn["haz_pct"]], textposition="outside",
        textfont=dict(color=TEXT_PRIMARY, size=12),
        hovertemplate=(
            "<b>%{y}</b><br>Phần trăm ngày nguy hại: %{x:.1f}%<br>"
            "Số ngày nguy hại: %{customdata[0]:,}<br>"
            "Tổng số ngày: %{customdata[1]:,}<extra></extra>"
        ),
        customdata=list(zip(
            stn.get("Hazardous", pd.Series([0] * len(stn))).astype(int),
            stn["total"].astype(int),
        )),
    ))
    fig.add_vline(
        x=avg_haz, line_dash="dash", line_color=TEXT_SECONDARY, line_width=1.5,
        annotation=dict(text=f"TB: {avg_haz:.1f}%", font=dict(color=TEXT_SECONDARY, size=11), bgcolor=CARD_BG),
        annotation_position="top right",
    )
    fig.update_layout(**_base_layout(
        title=dict(text="Phần trăm ngày nguy hại theo trạm quan trắc", font=dict(size=15)),
        xaxis=dict(title="Phần trăm ngày quan trắc", range=[0, 105], gridcolor=GRIDLINE, showgrid=True, ticksuffix="%"),
        yaxis=dict(title="", gridcolor=GRIDLINE, showgrid=False),
        height=330, showlegend=False,
    ))
    return fig


def Daily_PM25_Trend(df_city_daily: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ đường kết hợp vùng (line + area): cường độ rủi ro PM2.5
    trung bình ngày toàn thành phố, với ngưỡng tham chiếu WHO 15 µg/m³.
    Vùng nền xanh lá nhạt (Safe) và đỏ nhạt (Hazardous) được tô bằng add_hrect.
    """
    plot_df = df_city_daily.sort_values("Date").copy()
    y_max_val = plot_df["PM2.5"].max() if not plot_df.empty else 30
    y_upper = max(y_max_val * 1.15, PM25_SAFE_THRESHOLD * 1.5)

    fig = go.Figure()

    # Vùng nền chỉ báo mức độ rủi ro
    fig.add_hrect(y0=0, y1=PM25_SAFE_THRESHOLD, fillcolor="rgba(42,157,143,0.08)", layer="below", line_width=0)
    fig.add_hrect(y0=PM25_SAFE_THRESHOLD, y1=y_upper, fillcolor="rgba(230,57,70,0.08)", layer="below", line_width=0)

    # Vùng tô bóng nhẹ dưới đường chính
    fig.add_trace(go.Scatter(
        x=plot_df["Date"], y=plot_df["PM2.5"], mode="none",
        fill="tozeroy", fillcolor="rgba(178,58,47,0.10)", showlegend=False, hoverinfo="skip",
    ))
    # Đường nồng độ PM2.5 chính
    fig.add_trace(go.Scatter(
        x=plot_df["Date"], y=plot_df["PM2.5"], mode="lines+markers",
        name="PM2.5 trung bình ngày",
        line=dict(color=COLOR_PM25, width=2.5, shape="spline"),
        marker=dict(size=5, color=COLOR_PM25),
        hovertemplate="<b>%{x}</b><br>PM2.5 TB: %{y:.2f} µg/m³<extra></extra>",
    ))
    # Đường ngưỡng WHO (nét đứt)
    fig.add_trace(go.Scatter(
        x=[plot_df["Date"].min(), plot_df["Date"].max()],
        y=[PM25_SAFE_THRESHOLD, PM25_SAFE_THRESHOLD],
        mode="lines", name=f"Ngưỡng WHO ({PM25_SAFE_THRESHOLD} µg/m³)",
        line=dict(color=TEXT_SECONDARY, width=2, dash="dash"), hoverinfo="skip",
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="Diễn biến nồng độ PM2.5 trung bình ngày toàn thành phố", font=dict(size=15)),
        xaxis=dict(title="Ngày", gridcolor=GRIDLINE, showgrid=True),
        yaxis=dict(title="Nồng độ PM2.5 (µg/m³)", gridcolor=GRIDLINE, showgrid=True, range=[0, y_upper]),
        height=420, showlegend=True,
    ))
    return fig


def Hazardous_Heatmap(df: pd.DataFrame) -> go.Figure:
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
# RENDER TRANG
# ─────────────────────────────────────────────────────────────────────────────

def reset_filters(default_stations, default_start, default_end):
    """Hàm callback gán trực tiếp giá trị mặc định vào session state."""
    st.session_state["P06_station"] = default_stations
    st.session_state["P06_date"] = (default_start, default_end)


def render_Health_Risk_Profiling(file_path: str | None = None) -> None:
    """Render toàn bộ trang Mục tiêu 5 — Phân tích Rủi ro Sức khỏe do bụi mịn PM2.5."""

    # ── CSS tùy chỉnh ──
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
        "Mục tiêu 5: Phân tích Rủi ro Sức khỏe do bụi mịn PM2.5</h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Tiêu chí đánh giá: Một ngày được xếp loại \"Nguy hại\" nếu nồng độ PM2.5 "
        "trung bình trong ngày đó lớn hơn 15 µg/m³ (ngưỡng khuyến cáo của WHO), "
        "ngược lại được xếp loại \"An toàn\"."
    )

    # ── Tải dữ liệu ──
    data_path = file_path or str(DEFAULT_DATA_PATH)
    if not Path(data_path).exists():
        st.error(f"Không tìm thấy tập tin `{data_path}`. Vui lòng kiểm tra lại đường dẫn.")
        return

    with st.spinner("Đang tải dữ liệu..."):
        df_all = load_data(data_path)

    if df_all.empty:
        st.warning("Không có dữ liệu hợp lệ.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR — Bộ lọc dữ liệu
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Bộ lọc dữ liệu")

        all_stations = sorted(df_all["Station_No"].unique().tolist())
        sel_stations: list = st.multiselect(
            "Chọn trạm quan trắc", options=all_stations, default=all_stations,
            format_func=lambda x: f"Trạm {x}", key="P06_station",
        )

        min_d = df_all["datetime"].dt.date.min()
        max_d = df_all["datetime"].dt.date.max()
        sel_range = st.date_input(
            "Khoảng thời gian", value=(min_d, max_d),
            min_value=min_d, max_value=max_d, key="P06_date",
        )

        st.button("Đặt lại bộ lọc", on_click=reset_filters, args=(all_stations, min_d, max_d))

    # ── Kiểm tra bộ lọc ──
    if isinstance(sel_range, (list, tuple)):
        if len(sel_range) == 2:
            d_start, d_end = sel_range
        elif len(sel_range) == 1:
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
    # TẠO TẬP DỮ LIỆU PHÂN TẦNG
    # ─────────────────────────────────────────────────────────────────────────
    start_ts = pd.to_datetime(d_start)
    end_ts = pd.to_datetime(d_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    mask = (
        (df_all["Station_No"].isin(sel_stations))
        & (df_all["datetime"] >= start_ts)
        & (df_all["datetime"] <= end_ts)
        & (df_all["PM2.5"].notna())
    )
    df_pre_risk: pd.DataFrame = df_all[mask].copy()

    if df_pre_risk.empty:
        st.warning("Không có dữ liệu trong khoảng đã chọn.")
        return

    df_pre_risk["Health_Risk"] = np.where(
        df_pre_risk["PM2.5"] <= PM25_SAFE_THRESHOLD, "Safe", "Hazardous",
    )
    df_pre_risk["Hour_dt"] = df_pre_risk["datetime"].dt.hour
    day_map = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"}
    df_pre_risk["DayOfWeek"] = df_pre_risk["datetime"].dt.dayofweek.map(day_map)
    df_pre_risk["DayOfWeek"] = pd.Categorical(df_pre_risk["DayOfWeek"], categories=WEEKDAY_ORDER_VI, ordered=True)

    # Tầng 1: df_hourly — dữ liệu theo giờ gốc, chỉ giữ các cột cần thiết
    df_hourly = df_pre_risk[["datetime", "Date", "Station_No", "PM2.5", "Hour_dt", "DayOfWeek"]].copy()
    df_hourly = df_hourly.rename(columns={"Hour_dt": "Hour"})

    # Tầng 2: df_station_daily — trung bình ngày theo từng trạm
    df_station_daily = df_hourly.groupby(["Station_No", "Date"], as_index=False)["PM2.5"].mean()
    df_station_daily["Health_Risk"] = np.where(
        df_station_daily["PM2.5"] <= PM25_SAFE_THRESHOLD, "Safe", "Hazardous",
    )

    # Tầng 3: df_city_daily — trung bình ngày toàn thành phố
    df_city_daily = df_hourly.groupby("Date", as_index=False)["PM2.5"].mean()
    df_city_daily["Health_Risk"] = np.where(
        df_city_daily["PM2.5"] <= PM25_SAFE_THRESHOLD, "Safe", "Hazardous",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # THẺ CHỈ SỐ (KPI CARDS)
    # ─────────────────────────────────────────────────────────────────────────
    # Tính toán nồng độ trung bình thay vì tổng tích lũy
    avg_pm25 = df_hourly["PM2.5"].mean() 
    total_days = len(df_city_daily)
    haz_days = int((df_city_daily["Health_Risk"] == "Hazardous").sum())
    haz_pct = (haz_days / total_days * 100) if total_days > 0 else 0

    k1, k2, k3 = st.columns(3)
    
    # Cập nhật nhãn, giá trị hiển thị (lấy 2 chữ số thập phân) và phần trợ giúp
    k1.metric(
        "Trung bình nồng độ PM2.5", 
        f"{avg_pm25:.2f} µg/m³",
        help="Nồng độ bụi mịn PM2.5 trung bình trong suốt khoảng thời gian và các trạm đã chọn"
    )
    
    k2.metric(
        "Tổng số ngày quan trắc", 
        f"{total_days:,}",
        help="Tổng số ngày có dữ liệu hợp lệ (tính theo lịch) trong khoảng thời gian đã lọc"
    )
    
    k3.metric(
        "Số ngày nguy hại", 
        f"{haz_days:,}",
        delta=f"{haz_pct:.1f}% trên tổng số ngày", 
        delta_color="inverse",
        help="Số ngày có nồng độ PM2.5 trung bình vượt ngưỡng 15 µg/m³ của WHO"
    )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 1 — Biểu đồ Donut + Bar theo trạm
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Tổng quan rủi ro và phân bố theo khu vực")
    col_donut, col_bar = st.columns(2)

    with col_donut:
        st.plotly_chart(Health_Risk_Donut(df_city_daily), use_container_width=True)
        # Nhận xét động cho biểu đồ Donut
        safe_pct = 100 - haz_pct
        if haz_pct > 0:
            st.info(
                f"Trong khoảng thời gian chọn, có {haz_pct:.1f}% số ngày "
                f"({haz_days}/{total_days} ngày) người dân phải tiếp xúc với "
                f"không khí nguy hại (PM2.5 trung bình vượt 15 µg/m³). "
                f"Chỉ có {safe_pct:.1f}% số ngày đạt mức an toàn theo khuyến cáo WHO."
            )
        else:
            st.info(
                f"Trong khoảng thời gian chọn, 100% số ngày ({total_days} ngày) "
                f"đều đạt mức an toàn theo khuyến cáo WHO."
            )

    with col_bar:
        st.plotly_chart(Station_Risk_Bar(df_station_daily), use_container_width=True)
        # Nhận xét động cho biểu đồ Bar
        valid_stn = df_station_daily[df_station_daily["Health_Risk"].notna()]
        if not valid_stn.empty:
            stn_haz = (
                valid_stn.groupby("Station_No")["Health_Risk"]
                .apply(lambda x: (x == "Hazardous").sum() / len(x) * 100)
            )
            worst_stn, worst_val = stn_haz.idxmax(), stn_haz.max()
            best_stn, best_val = stn_haz.idxmin(), stn_haz.min()
            st.info(
                f"Trạm có tỷ lệ ngày nguy hại cao nhất: Trạm {worst_stn} ({worst_val:.1f}%). "
                f"Trạm có tỷ lệ ngày nguy hại thấp nhất: Trạm {best_stn} ({best_val:.1f}%)."
            )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 2 — Biểu đồ đường cường độ rủi ro PM2.5
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Diễn biến cường độ rủi ro PM2.5 theo ngày")
    st.plotly_chart(Daily_PM25_Trend(df_city_daily), use_container_width=True)

    # Nhận xét động cho biểu đồ Trend
    if not df_city_daily.empty:
        peak_idx = df_city_daily["PM2.5"].idxmax()
        peak_row = df_city_daily.loc[peak_idx]
        peak_ratio = peak_row["PM2.5"] / PM25_SAFE_THRESHOLD if PM25_SAFE_THRESHOLD > 0 else np.nan
        trend_msg = (
            f"Ngày có nồng độ PM2.5 trung bình cao nhất: {peak_row['Date']} "
            f"với giá trị {peak_row['PM2.5']:.2f} µg/m³, "
            f"gấp {peak_ratio:.1f} lần ngưỡng an toàn WHO "
            f"({PM25_SAFE_THRESHOLD} µg/m³)."
        )
        if peak_ratio >= 2:
            st.error(trend_msg)
        elif peak_ratio > 1:
            st.warning(trend_msg)
        else:
            st.info(trend_msg)
    else:
        st.warning("Không có dữ liệu để rút ra nhận xét cho biểu đồ xu hướng.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 3 — Heatmap chu kỳ thời gian
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Mức độ rủi ro theo Chu kỳ thời gian")
    st.caption(
        "Lưu ý: Ngưỡng 15 µg/m³ là chuẩn trung bình 24 giờ của WHO, "
        "tại đây được dùng như ngưỡng tham chiếu để so sánh theo từng giờ."
    )
    st.plotly_chart(Hazardous_Heatmap(df_pre_risk), use_container_width=True)

    # Nhận xét động cho Heatmap
    haz = df_pre_risk[df_pre_risk["Health_Risk"] == "Hazardous"]
    if not haz.empty:
        haz_pivot = (
            haz.groupby(["DayOfWeek", "Hour_dt"]).size()
            .reset_index(name="Count")
            .pivot(index="DayOfWeek", columns="Hour_dt", values="Count")
            .reindex(index=WEEKDAY_ORDER_VI, columns=range(24))
            .fillna(0)
        )
        max_val = haz_pivot.values.max()
        if max_val > 0:
            max_row, max_col = np.unravel_index(haz_pivot.values.argmax(), haz_pivot.values.shape)
            day_label = WEEKDAY_ORDER_VI[max_row]
            hour_label = f"{int(max_col):02d}h"
            total_haz = int(haz.shape[0])
            share = (max_val / total_haz * 100) if total_haz > 0 else 0
            heat_msg = (
                f"Điểm nóng nguy hại tập trung nhất rơi vào {hour_label} ngày {day_label}, "
                f"với {int(max_val)} lần xuất hiện."
            )
            if share >= 20:
                st.error(heat_msg)
            elif share >= 10:
                st.warning(heat_msg)
            else:
                st.info(heat_msg)
        else:
            st.info("Không ghi nhận giờ nguy hại trong khoảng lọc, heatmap cho thấy mức an toàn.")
    else:
        st.warning("Không có dữ liệu để rút ra điểm nóng theo chu kỳ thời gian.")


# Main
def main() -> None:
    st.set_page_config(page_title="Dashboard Goal 5", page_icon="", layout="wide")
    render_Health_Risk_Profiling()


if __name__ == "__main__":
    main()