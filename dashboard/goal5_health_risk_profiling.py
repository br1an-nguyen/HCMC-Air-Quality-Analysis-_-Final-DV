from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.ui_theme import (
    inject_global_css, render_page_header, render_sidebar_header,
    render_section_header, render_divider, render_standard_sidebar,
    render_insight_box, render_conclusion_box, get_icon_html
)

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

    # Đồng bộ với Goal 1: loại bỏ flag=2 (sensor offline/NaN)
    # Giữ lại flag=0 (tin cậy) và flag=1 (hợp lệ, chưa xác nhận đầy đủ)
    flag_cols = [c for c in df.columns if c.endswith("_flag")]
    if flag_cols:
        df = df[(df[flag_cols] <= 1).all(axis=1)]

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


def Monthly_Risk_Stacked_Bar(df_city_daily: pd.DataFrame) -> go.Figure:
    """
    Stacked bar: số ngày An toàn và Nguy hại theo tháng.
    Dựa trên df_city_daily (trung bình ngày toàn thành phố).
    """
    if df_city_daily.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout(
            title=dict(text="Số ngày an toàn và nguy hại theo tháng", font=dict(size=15)),
            height=380,
            showlegend=True,
        ))
        return fig

    plot_df = df_city_daily.copy()
    plot_df["Date_dt"] = pd.to_datetime(plot_df["Date"])
    plot_df["YearMonth"] = plot_df["Date_dt"].dt.to_period("M")

    counts = (
        plot_df.groupby(["YearMonth", "Health_Risk"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    counts["total"] = counts.sum(axis=1)
    counts["haz_pct"] = np.where(
        counts["total"] > 0,
        counts.get("Hazardous", 0) / counts["total"] * 100,
        0,
    )

    x_labels = counts.index.to_timestamp().strftime("%m/%Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels,
        y=counts.get("Safe", 0),
        name="An toàn",
        marker=dict(color=HEALTH_RISK_COLORS.get("Safe", COLOR_SAFE)),
        hovertemplate=(
            "<b>%{x}</b><br>An toàn: %{y:,.0f} ngày<extra></extra>"
        ),
    ))
    fig.add_trace(go.Bar(
        x=x_labels,
        y=counts.get("Hazardous", 0),
        name="Nguy hại",
        marker=dict(color=HEALTH_RISK_COLORS.get("Hazardous", COLOR_HAZARDOUS)),
        text=[f"{v:.0f}%" if v > 0 else "" for v in counts["haz_pct"]],
        textposition="inside",
        textfont=dict(color=CARD_BG, size=11),
        hovertemplate=(
            "<b>%{x}</b><br>Nguy hại: %{y:,.0f} ngày<extra></extra>"
        ),
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="Số ngày an toàn và nguy hại theo tháng", font=dict(size=15)),
        barmode="stack",
        xaxis=dict(title="Tháng", gridcolor=GRIDLINE, showgrid=False),
        yaxis=dict(title="Số ngày", gridcolor=GRIDLINE, showgrid=True),
        height=380,
        showlegend=True,
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
        [0.0,  "#FFFFFF"],
        [0.35, "#FFCC80"],
        [0.65, "#FF6600"],
        [1.0,  "#8B0000"],
    ]

    z_vals = pivot.values.astype(float)
    z_max = float(z_vals.max()) if z_vals.size else 0.0
    z_max = max(1.0, z_max)

    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=list(range(24)),
        y=WEEKDAY_ORDER_VI,
        colorscale=custom_scale,
        zmin=0,
        zmax=z_max,
        xgap=1, 
        ygap=1,
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

    inject_global_css()

    render_page_header(
        "Rủi ro sức khỏe",
        'Phân tích rủi ro sức khỏe do bụi mịn PM2.5 theo tiêu chí ngày "Nguy hại" khi PM2.5 trung bình > 15 µg/m³ (ngưỡng WHO)'
    )

    # ── CSS bổ sung riêng Goal 5 (section-divider) ──
    st.markdown(f"""
    <style>
    .section-divider {{ border:none; border-top:1px solid {GRIDLINE}; margin:24px 0 18px 0; }}
    </style>
    """, unsafe_allow_html=True)

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
    def _g5_extra():
        st.sidebar.button(
            "Đặt lại bộ lọc",
            on_click=reset_filters,
            args=(sorted(df_all["Station_No"].unique().tolist()),
                  df_all["datetime"].dt.date.min(),
                  df_all["datetime"].dt.date.max()),
        )
        return {}

    sb = render_standard_sidebar(
        df_all,
        datetime_col="datetime",
        station_col="Station_No",
        sidebar_key_prefix="g5",
        extra_widgets_fn=_g5_extra,
    )
    sel_stations = sb["stations"]
    d_start      = sb["start_date"]
    d_end        = sb["end_date"]

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
        delta="Chỉ số chính",
        delta_color="off"
    )
    
    k2.metric(
        "Tổng số ngày quan trắc", 
        f"{total_days:,}",
        delta="Toàn kỳ",
        delta_color="off"
    )
    
    k3.metric(
        "Số ngày nguy hại", 
        f"{haz_days:,}",
        delta=f"-{haz_pct:.1f}% trên tổng số ngày", # Dấu - để hiện màu đỏ
        delta_color="inverse",
    )

    render_divider()

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 1 — Biểu đồ Donut + Bar theo trạm
    # ─────────────────────────────────────────────────────────────────────────
    render_section_header("Tổng quan rủi ro và phân bố theo khu vực")
    col_donut, col_bar = st.columns(2)

    with col_donut:
        st.plotly_chart(Health_Risk_Donut(df_city_daily), use_container_width=True)
        # Nhận xét động cho biểu đồ Donut
        safe_pct = 100 - haz_pct
        if haz_pct > 0:
            render_insight_box([
                f"Có <b>{haz_pct:.1f}%</b> số ngày ({haz_days}/{total_days} ngày) tiếp xúc với không khí nguy hại (PM2.5 > 15 µg/m³).",
                f"Chỉ có <b>{safe_pct:.1f}%</b> số ngày đạt mức an toàn theo khuyến cáo WHO."
            ], title="Tỷ lệ an toàn - nguy hại", icon_name="activity")
        else:
            render_insight_box([
                f"100% số ngày ({total_days} ngày) đều đạt mức an toàn theo khuyến cáo WHO."
            ], title="Mức độ an toàn tuyệt đối")

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
            render_insight_box([
                f"Trạm có tỷ lệ ngày nguy hại cao nhất: <b>Trạm {worst_stn}</b> ({worst_val:.1f}%).",
                f"Trạm có tỷ lệ ngày nguy hại thấp nhất: <b>Trạm {best_stn}</b> ({best_val:.1f}%)."
            ], title="Phân hóa theo trạm", icon_name="location")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 2 — Biểu đồ stacked bar theo tháng
    # ─────────────────────────────────────────────────────────────────────────
    render_section_header("Số ngày an toàn và nguy hại theo tháng")
    st.plotly_chart(Monthly_Risk_Stacked_Bar(df_city_daily), use_container_width=True)

    # Nhận xét động cho biểu đồ Stacked Bar
    if not df_city_daily.empty:
        tmp = df_city_daily.copy()
        tmp["Date_dt"] = pd.to_datetime(tmp["Date"])
        tmp["YearMonth"] = tmp["Date_dt"].dt.to_period("M")
        monthly = tmp.groupby(["YearMonth", "Health_Risk"]).size().unstack(fill_value=0)
        monthly["total"] = monthly.sum(axis=1)
        monthly["haz_pct"] = np.where(
            monthly["total"] > 0,
            monthly.get("Hazardous", 0) / monthly["total"] * 100,
            0,
        )
        if not monthly.empty:
            worst_month = monthly["haz_pct"].idxmax()
            best_month = monthly["haz_pct"].idxmin()
            worst_label = worst_month.to_timestamp().strftime("%m/%Y")
            best_label = best_month.to_timestamp().strftime("%m/%Y")
            worst_pct = monthly.loc[worst_month, "haz_pct"]
            best_pct = monthly.loc[best_month, "haz_pct"]
            target_months = [
                pd.Period("2021-03", freq="M"),
                pd.Period("2021-11", freq="M"),
                pd.Period("2021-12", freq="M"),
                pd.Period("2022-01", freq="M"),
            ]
            full_haz = [m for m in target_months if m in monthly.index and monthly.loc[m, "haz_pct"] >= 100]
            full_haz_labels = ", ".join([m.to_timestamp().strftime("%m/%Y") for m in full_haz])

            insight_lines = [
                f"Các tháng có tỷ lệ ngày nguy hại cao nhất: <b>{full_haz_labels}</b> ({worst_pct:.1f}%).",
                f"Tháng an toàn nhất: <b>{best_label}</b> ({best_pct:.1f}% ngày nguy hại).",
            ]

            render_insight_box(
                insight_lines,
                title="Bức tranh rủi ro theo tháng",
                icon_name="analysis",
            )
        else:
            st.info("Không có dữ liệu để rút ra nhận xét cho biểu đồ theo tháng.")
    else:
        st.warning("Không có dữ liệu để rút ra nhận xét cho biểu đồ theo tháng.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HÀNG 3 — Heatmap chu kỳ thời gian
    # ─────────────────────────────────────────────────────────────────────────
    render_section_header("Mức độ rủi ro theo Chu kỳ thời gian")
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
            nonzero_vals = haz_pivot.values[haz_pivot.values > 0]
            min_msg = ""
            if nonzero_vals.size > 0:
                min_val = nonzero_vals.min()
                min_positions = np.argwhere(haz_pivot.values == min_val)
                min_row, min_col = min_positions[0]
                min_day_label = WEEKDAY_ORDER_VI[min_row]
                min_hour_label = f"{int(min_col):02d}h"
                min_msg = (
                    f"Mức nguy hại thấp nhất rơi vào <b>{min_hour_label}</b> ngày <b>{min_day_label}</b>, "
                    f"với <b>{int(min_val)}</b> lần xuất hiện."
                )
            total_haz = int(haz.shape[0])
            share = (max_val / total_haz * 100) if total_haz > 0 else 0
            heat_msg = (
                f"Điểm nóng nguy hại tập trung nhất rơi vào <b>{hour_label}</b> ngày <b>{day_label}</b>, "
                f"với <b>{int(max_val)}</b> lần xuất hiện."
            )
            insight_lines = [heat_msg]
            if min_msg:
                insight_lines.append(min_msg)
            if share >= 20:
                title = "Cảnh báo điểm nóng"
                icon_name = "warning"
            elif share >= 10:
                title = "Điểm nóng đáng chú ý"
                icon_name = "activity"
            else:
                title = "Điểm nóng rải rác"
                icon_name = "insight"
            render_insight_box(insight_lines, title=title, icon_name=icon_name)
        else:
            render_insight_box(
                ["Không ghi nhận giờ nguy hại trong khoảng lọc, heatmap cho thấy mức an toàn."],
                title="An toàn theo chu kỳ",
                icon_name="insight",
            )
    else:
        render_insight_box(
            ["Không có dữ liệu để rút ra điểm nóng theo chu kỳ thời gian."],
            title="Không có dữ liệu",
            icon_name="warning",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # KẾT LUẬN
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### {get_icon_html('trend')} Kết luận", unsafe_allow_html=True)

    if df_city_daily.empty or df_station_daily.empty:
        st.markdown(
            "<div style='background:#F0F7FF; border-left:4px solid #2E86AB; border-radius:8px; "
            "padding:20px; color:#16324F; font-weight:600;'>Không đủ dữ liệu để tổng hợp kết luận</div>",
            unsafe_allow_html=True,
        )
        return

    monthly = (
        df_city_daily.assign(Date_dt=pd.to_datetime(df_city_daily["Date"]))
        .assign(YearMonth=lambda d: d["Date_dt"].dt.to_period("M"))
        .groupby(["YearMonth", "Health_Risk"]).size().unstack(fill_value=0)
    )
    monthly["total"] = monthly.sum(axis=1)
    monthly["haz_pct"] = np.where(
        monthly["total"] > 0,
        monthly.get("Hazardous", 0) / monthly["total"] * 100,
        0,
    )

    worst_month = monthly["haz_pct"].idxmax()
    best_month = monthly["haz_pct"].idxmin()
    worst_month_label = worst_month.to_timestamp().strftime("%m/%Y")
    best_month_label = best_month.to_timestamp().strftime("%m/%Y")

    worst_station_row = (
        df_station_daily.groupby("Station_No")["Health_Risk"]
        .apply(lambda x: (x == "Hazardous").mean() * 100)
    )
    worst_station = int(worst_station_row.idxmax())
    worst_station_pct = float(worst_station_row.max())

    haz_pivot = (
        df_pre_risk[df_pre_risk["Health_Risk"] == "Hazardous"]
        .groupby(["DayOfWeek", "Hour_dt"]).size()
        .reset_index(name="Count")
        .pivot(index="DayOfWeek", columns="Hour_dt", values="Count")
        .reindex(index=WEEKDAY_ORDER_VI, columns=range(24))
        .fillna(0)
    )
    if haz_pivot.values.max() > 0:
        max_row, max_col = np.unravel_index(haz_pivot.values.argmax(), haz_pivot.values.shape)
        peak_day = WEEKDAY_ORDER_VI[max_row]
        peak_hour = f"{int(max_col):02d}h"
    else:
        peak_day = "N/A"
        peak_hour = "N/A"

    full_haz = monthly[monthly["haz_pct"] >= 100].index
    full_haz_label = ", ".join([m.to_timestamp().strftime("%m/%Y") for m in full_haz])

    nonzero_vals = haz_pivot.values[haz_pivot.values > 0]
    if nonzero_vals.size > 0:
        min_val = nonzero_vals.min()
        min_row, min_col = np.argwhere(haz_pivot.values == min_val)[0]
        min_day = WEEKDAY_ORDER_VI[min_row]
        min_hour = f"{int(min_col):02d}h"
        min_note = f"Khung giờ ít nguy hại nhất: <b>{min_hour}</b> ngày <b>{min_day}</b> ({int(min_val)} lần)."
    else:
        min_note = "Không có khung giờ nguy hại trong khoảng lọc."

    title = "Rủi ro sức khỏe tập trung theo mùa và theo nhịp ngày"
    bullets = [
        f"Bức tranh tổng thể cho thấy <b>{haz_pct:.1f}%</b> số ngày là nguy hại — tức <b>{haz_days}/{total_days}</b> ngày vượt ngưỡng WHO.",
        f"Rủi ro dồn vào một số tháng rõ rệt: đỉnh rơi vào <b>{worst_month_label}</b>, trong khi <b>{best_month_label}</b> là giai đoạn an toàn nhất.",
        f"Không gian cũng phân hóa: <b>Trạm {worst_station}</b> ghi nhận <b>{worst_station_pct:.1f}%</b> ngày nguy hại — cao hơn mặt bằng chung.",
        f"Theo chu kỳ ngày, điểm nóng tập trung vào <b>{peak_hour}</b> ngày <b>{peak_day}</b>; {min_note}",
    ]
    if full_haz_label:
        bullets.insert(2, f"Các tháng có <b>100%</b> ngày nguy hại: <b>{full_haz_label}</b>.")

    content_html = f"""
        <h4 style="margin-top:0; color:#2E86AB;">{get_icon_html('analysis')} {title}</h4>
        <ol style="margin-bottom: 0;">
            {''.join(f'<li>{line}</li>' for line in bullets)}
        </ol>
    """
    render_conclusion_box(content_html, accent_color="#2E86AB")


# Main
def main() -> None:
    render_Health_Risk_Profiling()


if __name__ == "__main__":
    main()