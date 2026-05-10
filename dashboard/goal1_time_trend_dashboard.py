"""
Air Quality Dashboard — Ho Chi Minh City
Goal 1: Time-based Pollution Trend Analysis

Dataset: Air_Quality_HCMC_Cleaned.csv
Columns used: Date, Hour, Station_No, PM2.5, O3, CO, NO2, Temperature, Humidity, *_flag
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from scipy.stats import gaussian_kde

from dashboard.ui_theme import (
    inject_global_css, render_page_header, render_sidebar_header, render_section_header,
    render_divider, render_standard_sidebar, render_insight_box
)

_insight_box = render_insight_box

# ── Constants ────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "data" / "cleaned" / "Air_Quality_HCMC_Cleaned.csv"

# All flag columns in the dataset — rows where ANY flag ≠ 0 are dirty data
FLAG_COLS = [
    "TSP_flag", "PM2.5_flag", "O3_flag", "CO_flag",
    "NO2_flag", "SO2_flag", "Temperature_flag", "Humidity_flag",
]

# WHO 24-hour PM2.5 guideline (µg/m³)
WHO_PM25 = 15.0

# Plotly color sequence — one distinct color per station
STATION_COLORS = px.colors.qualitative.Bold


# ── Data loading & preprocessing ─────────────────────────────────────────────
@st.cache_data(show_spinner="Đang tải dữ liệu…")
def load_data() -> pd.DataFrame:
    """
    Load CSV, build a proper Datetime column, and strip dirty rows.

    Dirty rows = any flag column has a non-zero value.
    Returns a clean DataFrame sorted by Datetime.
    """
    df = pd.read_csv(DATA_PATH)

    # Combine Date (YYYY-MM-DD) + Hour (int 0-23) → Datetime
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Hour"].astype(str).str.zfill(2) + ":00:00",
        errors="coerce",
    )

    # Drop rows where Datetime could not be parsed
    df = df.dropna(subset=["Datetime"])

    # Keep rows where every flag column is 0 or 1 (drop flag = 2 = sensor offline/NaN)
    clean_mask = (df[FLAG_COLS] <= 1).all(axis=1)
    df = df[clean_mask].copy()

    df = df.sort_values("Datetime").reset_index(drop=True)
    return df


# ── Sidebar filters ───────────────────────────────────────────────────────────
def build_sidebar(df: pd.DataFrame):
    """Render sidebar chuẩn và trả về (start_date, end_date, selected_stations)."""
    result = render_standard_sidebar(
        df,
        datetime_col="Datetime",
        station_col="Station_No",
        sidebar_key_prefix="g1",
    )
    return result["start_date"], result["end_date"], result["stations"]


# ── Filtering ─────────────────────────────────────────────────────────────────
def apply_filters(
    df: pd.DataFrame,
    start_date,
    end_date,
    selected_stations: list,
) -> pd.DataFrame:
    """Apply date-range and station filters to the clean DataFrame."""
    mask = (
        (df["Datetime"].dt.date >= start_date)
        & (df["Datetime"].dt.date <= end_date)
        & (df["Station_No"].isin(selected_stations))
    )
    return df[mask].copy()


# ── Section 1: KPI cards ──────────────────────────────────────────────────────
def render_kpis(df: pd.DataFrame) -> None:
    """Display top-level KPI metric cards."""

    avg_pm25 = df["PM2.5"].mean()
    avg_temp = df["Temperature"].mean()
    avg_hum  = df["Humidity"].mean()

    # WHO 15 µg/m³ là ngưỡng TRUNG BÌNH 24 GIỜ — phải tính daily mean trước rồi mới so sánh
    daily_mean_pm25 = (
        df.groupby(df["Datetime"].dt.date)["PM2.5"].mean()
    )
    pct_above_who = (daily_mean_pm25 > WHO_PM25).mean() * 100

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        label="PM2.5 trung bình",
        value=f"{avg_pm25:.1f} µg/m³",
        delta=f"+{avg_pm25:.1f} (Hiện tại)", # Dùng + để hiện màu xanh theo yêu cầu
        delta_color="normal",
    )
    c2.metric(
        label="Nhiệt độ trung bình",
        value=f"{avg_temp:.1f} °C",
    )
    c3.metric(
        label="Độ ẩm trung bình",
        value=f"{avg_hum:.1f} %",
    )
    c4.metric(
        label="% ngày vượt WHO",
        value=f"{pct_above_who:.1f} %",
        delta=f"Ngưỡng > {WHO_PM25} µg/m³",
        delta_color="off", # Chữ khác màu xám
    )


# ── Shared helper: render insight box ────────────────────────────────────────



def _insight_chart1(df: pd.DataFrame) -> None:
    """Insight động cho Chart 1 — tính từ filtered data."""
    if len(df) < 10:
        _insight_box(["Không đủ dữ liệu để tính insight."])
        return

    tmp = df.copy()
    tmp["month"] = tmp["Datetime"].dt.month
    tmp["Date"]  = tmp["Datetime"].dt.date

    # Dòng 1: mean PM2.5 mùa khô vs mùa mưa
    dry  = tmp[tmp["month"].isin([11, 12, 1, 2, 3, 4])]["PM2.5"].mean()
    rain = tmp[tmp["month"].isin([5, 6, 7, 8, 9, 10])]["PM2.5"].mean()
    lines = []
    if pd.notna(dry) and pd.notna(rain) and rain > 0:
        diff_pct = (dry - rain) / rain * 100
        lines.append(
            f"Mùa khô: <b>{dry:.1f} µg/m³</b> | Mùa mưa: <b>{rain:.1f} µg/m³</b> "
            f"— mùa khô cao hơn <b>{diff_pct:+.1f}%</b> so với mùa mưa"
        )
    elif pd.notna(dry):
        lines.append(f"Mùa khô: <b>{dry:.1f} µg/m³</b> (không có dữ liệu mùa mưa trong khoảng này)")
    else:
        lines.append(f"Mùa mưa: <b>{rain:.1f} µg/m³</b> (không có dữ liệu mùa khô trong khoảng này)")

    # Dòng 2: % ngày rolling mean > 15
    daily = (
        tmp.groupby("Date")["PM2.5"].mean()
        .rolling(7, min_periods=1, center=True).mean()
    )
    pct_exceed = (daily > 15).mean() * 100
    lines.append(f"<b>{pct_exceed:.1f}%</b> số ngày có rolling mean PM2.5 vượt ngưỡng WHO 15 µg/m³")

    # Dòng 3: spike bất thường (rolling mean > 60)
    daily_df = daily.reset_index()
    daily_df.columns = ["Date", "roll"]
    daily_df["Date"] = pd.to_datetime(daily_df["Date"])
    spikes = daily_df[daily_df["roll"] > 60]
    if not spikes.empty:
        worst = spikes.loc[spikes["roll"].idxmax()]
        lines.append(
            f"⚠️ Ghi nhận spike bất thường <b>{worst['roll']:.1f} µg/m³</b> "
            f"vào <b>{worst['Date'].strftime('%m/%Y')}</b> — cần kiểm tra nguồn"
        )

    _insight_box(lines)


def _insight_chart2(df: pd.DataFrame) -> None:
    """Insight động cho Chart 2 — tính từ toàn bộ dataset (station-filtered)."""
    if len(df) < 10:
        _insight_box(["Không đủ dữ liệu để tính insight."])
        return

    tmp = df.copy()
    tmp["hour"]  = tmp["Datetime"].dt.hour
    tmp["month"] = tmp["Datetime"].dt.month

    hourly_mean  = tmp.groupby("hour")["PM2.5"].mean()
    monthly_mean = tmp.groupby("month")["PM2.5"].mean()

    peak_hour  = int(hourly_mean.idxmax())
    peak_h_val = hourly_mean.max()
    peak_month = int(monthly_mean.idxmax())
    peak_m_val = monthly_mean.max()
    clean_month = int(monthly_mean.idxmin())
    clean_m_val = monthly_mean.min()

    _insight_box([
        f"Giờ ô nhiễm nhất trong ngày: <b>{peak_hour}:00</b> "
        f"(trung bình <b>{peak_h_val:.1f} µg/m³</b>)",
        f"Tháng ô nhiễm nhất: <b>Tháng {peak_month}</b> "
        f"(trung bình <b>{peak_m_val:.1f} µg/m³</b>)",
        f"Không khí sạch nhất: <b>Tháng {clean_month}</b> "
        f"(trung bình <b>{clean_m_val:.1f} µg/m³</b>)",
    ])


def _insight_chart3(df: pd.DataFrame) -> None:
    """Insight động cho Chart 3 — tính từ toàn bộ dataset (station-filtered)."""
    if len(df) < 10:
        _insight_box(["Không đủ dữ liệu để tính insight."])
        return

    tmp = df.copy()
    co_p99 = tmp["CO"].quantile(0.99)
    tmp = tmp[(tmp["CO"] >= 0) & (tmp["CO"] <= co_p99)]
    tmp["hour"]  = tmp["Datetime"].dt.hour
    tmp["month"] = tmp["Datetime"].dt.month

    morning_co = tmp[tmp["hour"].between(6, 9)]["CO"].mean()
    evening_co = tmp[tmp["hour"].between(16, 19)]["CO"].mean()

    monthly_co = tmp.groupby("month")["CO"].mean()
    peak_month = int(monthly_co.idxmax())
    peak_val   = monthly_co.max()
    low_val    = monthly_co.min()
    ratio      = peak_val / low_val if low_val > 0 else float("nan")

    dry_co  = tmp[tmp["month"].isin([11, 12, 1, 2, 3, 4])]["CO"].mean()
    rain_co = tmp[tmp["month"].isin([5, 6, 7, 8, 9, 10])]["CO"].mean()
    diff_pct = (dry_co - rain_co) / rain_co * 100 if rain_co > 0 else float("nan")

    lines = [
        f"CO giờ cao điểm sáng (6–9h): <b>{morning_co:,.0f} µg/m³</b> | "
        f"chiều (16–19h): <b>{evening_co:,.0f} µg/m³</b>",
        f"CO cao nhất vào <b>Tháng {peak_month}</b>: <b>{peak_val:,.0f} µg/m³</b> "
        f"— gấp <b>{ratio:.1f} lần</b> so với tháng thấp nhất",
    ]
    if pd.notna(diff_pct):
        lines.append(f"Mùa khô CO cao hơn mùa mưa <b>{diff_pct:.1f}%</b>")
    _insight_box(lines)


def _insight_chart4(df: pd.DataFrame) -> None:
    """Insight động cho Chart 4 — tính từ toàn bộ dataset (station-filtered)."""
    if len(df) < 10:
        _insight_box(["Không đủ dữ liệu để tính insight."])
        return

    tmp = df.copy()
    tmp["YearMonth"] = tmp["Datetime"].dt.to_period("M")
    monthly = tmp.groupby("YearMonth")[["PM2.5", "CO", "NO2"]].mean().reset_index()
    monthly["Date"] = monthly["YearMonth"].dt.to_timestamp()

    # Dòng 1: tháng cả 3 chất đồng loạt trong top 3
    top3 = {
        col: set(monthly.nlargest(3, col)["YearMonth"].astype(str))
        for col in ["PM2.5", "CO", "NO2"]
    }
    common = top3["PM2.5"] & top3["CO"] & top3["NO2"]
    if common:
        label = pd.Period(sorted(common)[0], freq="M").strftime("%m/%Y")
        line1 = f"3 chất đạt đỉnh đồng thời vào: <b>{label}</b>"
    else:
        line1 = "3 chất không có tháng đồng đỉnh rõ ràng"

    # Dòng 2: tháng 3 chất đồng loạt thấp nhất (mean normalized)
    for col in ["PM2.5", "CO", "NO2"]:
        mn, mx = monthly[col].min(), monthly[col].max()
        denom = mx - mn if mx != mn else 1.0
        monthly[f"{col}_n"] = (monthly[col] - mn) / denom
    monthly["avg_norm"] = monthly[["PM2.5_n", "CO_n", "NO2_n"]].mean(axis=1)
    cleanest = monthly.loc[monthly["avg_norm"].idxmin(), "YearMonth"]
    line2 = f"Không khí sạch nhất đồng thời: <b>{pd.Period(cleanest, freq='M').strftime('%m/%Y')}</b>"

    # Dòng 3: Pearson PM2.5 vs CO
    r = monthly["PM2.5"].corr(monthly["CO"])
    strength = "mạnh" if abs(r) >= 0.7 else ("trung bình" if abs(r) >= 0.4 else "yếu")
    line3 = f"PM2.5 và CO tương quan <b>{strength}</b> theo tháng (r = <b>{r:.2f}</b>)"

    _insight_box([line1, line2, line3])


def _insight_chart5(df: pd.DataFrame) -> None:
    """Insight động cho Chart 5 — tính từ filtered data (date + station)."""
    if len(df) < 10:
        _insight_box(["Không đủ dữ liệu để tính insight."])
        return

    tmp = df.copy()
    tmp["hour"] = tmp["Datetime"].dt.hour
    hourly = (
        tmp.groupby("hour")[["PM2.5", "CO"]]
        .mean()
        .reindex(range(24))
    )

    # Dòng 1: giờ PM2.5 cao nhất
    pm25_peak_h = int(hourly["PM2.5"].idxmax())
    pm25_peak_v = hourly["PM2.5"].max()
    who_cmp = "trên" if pm25_peak_v > 15 else "dưới"
    line1 = (
        f"PM2.5 cao nhất lúc <b>{pm25_peak_h}:00</b> — "
        f"<b>{pm25_peak_v:.1f} µg/m³</b> ({who_cmp} ngưỡng WHO 15 µg/m³)"
    )

    # Dòng 2: giờ CO cao nhất
    co_peak_h = int(hourly["CO"].idxmax())
    co_peak_v = hourly["CO"].max()
    line2 = f"CO đạt đỉnh lúc <b>{co_peak_h}:00</b> — <b>{co_peak_v:,.0f} µg/m³</b>"

    # Dòng 3: nhận xét pattern
    morning_peak = set(range(6, 10))
    evening_peak = set(range(16, 20))
    if pm25_peak_h in morning_peak:
        line3 = "Pattern điển hình: PM2.5 tăng theo giờ cao điểm sáng"
    elif pm25_peak_h in evening_peak:
        line3 = "Pattern điển hình: PM2.5 tăng theo giờ cao điểm chiều"
    else:
        line3 = (
            f"⚠️ Pattern bất thường: PM2.5 đạt đỉnh ngoài giờ cao điểm giao thông "
            f"({pm25_peak_h}:00)"
        )

    _insight_box([line1, line2, line3])
def render_chart1_pm25_trend(df: pd.DataFrame) -> None:
    """
    Chart 1: PM2.5 xu hướng theo thời gian.
    Fix 3: Hiển thị warning nếu date range < 7 ngày thay vì vẽ rolling chart.
    """
    render_section_header("Xu hướng PM2.5 theo thời gian (Rolling 7 ngày)")

    # Fix 3: guard — rolling 7 ngày cần ít nhất 7 ngày dữ liệu
    n_days = df["Datetime"].dt.date.nunique()
    if n_days < 7:
        st.warning(
            "⚠️ Rolling 7 ngày cần ít nhất 7 ngày dữ liệu. "
            "Vui lòng chọn khoảng thời gian rộng hơn, "
            "hoặc xem phân tích 24 giờ tại **Chart 5** bên dưới."
        )
        return

    # Aggregate all stations → daily mean/min/max
    tmp = df.copy()
    tmp["Date"] = tmp["Datetime"].dt.date
    daily_all = (
        tmp.groupby("Date")["PM2.5"]
        .agg(mean="mean", min_val="min", max_val="max")
        .reset_index()
    )
    daily_all["Date"] = pd.to_datetime(daily_all["Date"])
    daily_all = daily_all.sort_values("Date")

    # Rolling 7-day smoothing
    daily_all["roll_mean"] = daily_all["mean"].rolling(7, min_periods=1, center=True).mean()
    daily_all["roll_min"]  = daily_all["min_val"].rolling(7, min_periods=1, center=True).mean()
    daily_all["roll_max"]  = daily_all["max_val"].rolling(7, min_periods=1, center=True).mean()

    fig = go.Figure()

    # ── Fix 2: Dải min–max màu #BBDEFB opacity 0.4 — vẽ TRƯỚC (layer below)
    fig.add_trace(go.Scatter(
        x=pd.concat([daily_all["Date"], daily_all["Date"][::-1]]),
        y=pd.concat([daily_all["roll_max"], daily_all["roll_min"][::-1]]),
        fill="toself",
        fillcolor="rgba(187, 222, 251, 0.4)",   # #BBDEFB @ 0.4
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        name="Dải min–max (7 ngày)",
        showlegend=True,
    ))

    # ── Rolling mean line
    fig.add_trace(go.Scatter(
        x=daily_all["Date"],
        y=daily_all["roll_mean"].round(2),
        mode="lines",
        line=dict(color="#1A5FA8", width=2.5),
        name="Trung bình 7 ngày (tất cả trạm)",
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>PM2.5 TB: %{y:.1f} µg/m³<extra></extra>",
    ))

    # ── WHO guideline
    fig.add_hline(
        y=WHO_PM25,
        line_dash="dash",
        line_color="red",
        line_width=1.8,
        annotation_text="Ngưỡng WHO: 15 µg/m³",
        annotation_position="top left",
        annotation_font=dict(color="red", size=12),
    )

    # ── Fix 2: Season bands — vẽ SAU (layer "above" traces nhưng below lines)
    # Dùng layer="above" để mùa khô hiện rõ ranh giới trên dải shading
    date_min = daily_all["Date"].min()
    date_max = daily_all["Date"].max()
    years = range(date_min.year, date_max.year + 2)

    dry_label_added  = False
    rain_label_added = False

    for yr in years:
        # ── Mùa khô: Nov(yr-1) → Apr(yr)
        dry_start = max(pd.Timestamp(yr - 1, 11, 1), date_min)
        dry_end   = min(pd.Timestamp(yr, 4, 30),     date_max)
        if dry_start < dry_end:
            fig.add_vrect(
                x0=dry_start, x1=dry_end,
                fillcolor="#FFF3CD",          # Fix 2: #FFF3CD opacity 0.25
                opacity=0.25,
                line_width=0,
                layer="above",               # Fix 2: vẽ SAU dải min–max
                annotation_text="Mùa khô" if not dry_label_added else "",
                annotation_position="top left",
                annotation_font=dict(size=11, color="#8B6914"),
            )
            dry_label_added = True

        # ── Mùa mưa: May(yr) → Oct(yr)  — Fix 2: thêm nhãn "Mùa mưa"
        rain_start = max(pd.Timestamp(yr, 5, 1),  date_min)
        rain_end   = min(pd.Timestamp(yr, 10, 31), date_max)
        if rain_start < rain_end:
            # Không tô màu mùa mưa — chỉ thêm text annotation ở giữa vùng
            center_rain = rain_start + (rain_end - rain_start) / 2
            fig.add_annotation(
                x=center_rain,
                y=1.04,
                yref="paper",
                text="Mùa mưa" if not rain_label_added else "",
                showarrow=False,
                font=dict(size=11, color="#888888"),
                xanchor="center",
            )
            rain_label_added = True

    fig.update_layout(
        height=500,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(
            text="Xu hướng PM2.5 theo thời gian — Trung bình 7 ngày (tất cả trạm)",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Tháng",
            tickformat="%m/%Y",
            dtick="M1",
            tickangle=-30,
            showgrid=True,
            gridcolor="#EEEEEE",
        ),
        yaxis=dict(
            title="PM2.5 (µg/m³)",
            showgrid=True,
            gridcolor="#EEEEEE",
            zeroline=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        margin=dict(t=80, b=60, l=60, r=30),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Đường xanh đậm = trung bình rolling 7 ngày gộp tất cả trạm. "
        "Dải xanh nhạt = dao động min–max. Nền vàng = mùa khô (tháng 11–4)."
    )
    _insight_chart1(df)
def render_chart2_heatmap(df: pd.DataFrame) -> None:
    """
    Chart 2: Heatmap PM2.5 trung bình theo (giờ trong ngày × tháng).
    Trục X = giờ (0–23), Trục Y = tháng (1–12).
    Màu gradient: trắng → cam → đỏ đậm.
    """
    render_section_header("Heatmap PM2.5 theo Giờ × Tháng")

    tmp = df.copy()
    tmp["hour"]  = tmp["Datetime"].dt.hour
    tmp["month"] = tmp["Datetime"].dt.month

    pivot = (
        tmp.groupby(["month", "hour"])["PM2.5"]
        .mean()
        .round(1)
        .unstack(level="hour")          # shape: 12 rows (month) × 24 cols (hour)
        .reindex(index=range(1, 13), columns=range(24))
    )

    MONTH_LABELS = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
        "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
        "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
    ]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(range(24)),
        y=MONTH_LABELS,
        colorscale=[
            [0.0,  "#FFFFFF"],
            [0.35, "#FFCC80"],
            [0.65, "#FF6600"],
            [1.0,  "#8B0000"],
        ],
        colorbar=dict(
            title=dict(text="PM2.5<br>(µg/m³)", side="right"),
            thickness=16,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Giờ: %{x}:00<br>"
            "PM2.5 TB: %{z:.1f} µg/m³<extra></extra>"
        ),
        xgap=1,
        ygap=1,
    ))

    fig.update_layout(
        height=500,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(
            text="Heatmap PM2.5 trung bình theo Giờ trong ngày × Tháng",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Giờ trong ngày",
            tickmode="array",
            tickvals=list(range(0, 24, 2)),
            ticktext=[f"{h}:00" for h in range(0, 24, 2)],
        ),
        yaxis=dict(
            title="Tháng",
            autorange="reversed",   # Tháng 1 ở trên cùng
        ),
        margin=dict(t=70, b=60, l=100, r=30),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Màu đỏ đậm = PM2.5 cao nhất. "
        "Nhìn theo cột để thấy giờ cao điểm, nhìn theo hàng để thấy tháng ô nhiễm nhất."
    )
    st.caption("\\* Hiển thị toàn bộ giai đoạn 2021–2022, không bị ảnh hưởng bởi bộ lọc ngày.")
    _insight_chart2(df)


# ── Shared helper: 2D density + regression ───────────────────────────────────
def _build_density_fig(
    df: pd.DataFrame,
    x_col: str,
    x_label: str,
    title: str,
    extra_mask: pd.Series | None = None,   # additional boolean filter (Fix 1)
    ylim: tuple[float, float] = (0, 80),   # Fix 3: fixed y-axis range
) -> tuple[go.Figure, float, float, float, int]:
    """
    Vẽ 2D hexbin density + đường hồi quy tuyến tính + đường WHO.

    Parameters
    ----------
    extra_mask : boolean Series aligned to df, applied BEFORE the PM2.5 filter.
    ylim       : (ymin, ymax) cho trục Y — mặc định (0, 80).

    Returns
    -------
    fig, r², slope, intercept, n_outliers_removed
    """
    # ── Fix 1: apply caller-supplied extra filter first
    base = df.copy()
    if extra_mask is not None:
        base = base[extra_mask]

    # Count outliers BEFORE the PM2.5 < 150 cut so we can annotate
    n_total_before = len(base.dropna(subset=[x_col, "PM2.5"]))
    n_outliers = int((base["PM2.5"] >= 150).sum())

    # Keep PM2.5 in [1, 150) — Fix 1 also removes PM2.5 < 1
    clean = base[
        (base["PM2.5"] >= 1) & (base["PM2.5"] < 150)
    ].dropna(subset=[x_col, "PM2.5"]).copy()

    x_vals = clean[x_col].values
    y_vals = clean["PM2.5"].values

    fig = go.Figure()

    # ── Hexbin-style density
    fig.add_trace(go.Histogram2d(
        x=x_vals,
        y=y_vals,
        colorscale=[
            [0.0,  "rgba(255,255,255,0)"],
            [0.15, "#FFF3CD"],
            [0.4,  "#FFAA00"],
            [0.7,  "#E05000"],
            [1.0,  "#6B0000"],
        ],
        nbinsx=40,
        nbinsy=40,
        colorbar=dict(
            title=dict(text="Mật độ<br>điểm", side="right"),
            thickness=16,
        ),
        hovertemplate=(
            f"{x_label}: %{{x:.1f}}<br>"
            "PM2.5: %{y:.1f} µg/m³<br>"
            "Số điểm: %{z}<extra></extra>"
        ),
        name="Mật độ",
    ))

    # ── OLS regression line
    slope, intercept, r_val, _p, _ = stats.linregress(x_vals, y_vals)
    x_line = np.linspace(x_vals.min(), x_vals.max(), 200)
    y_line = slope * x_line + intercept

    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode="lines",
        line=dict(color="#1A5FA8", width=2.5, dash="solid"),
        name=f"Hồi quy tuyến tính (R²={r_val**2:.3f})",
        hovertemplate=f"Hồi quy: y = {slope:.2f}x + {intercept:.1f}<extra></extra>",
    ))

    # ── WHO guideline
    fig.add_hline(
        y=WHO_PM25,
        line_dash="dash",
        line_color="red",
        line_width=1.8,
        annotation_text="Ngưỡng WHO: 15 µg/m³",
        annotation_position="top left",
        annotation_font=dict(color="red", size=12),
    )

    # ── Fix 3: outlier count annotation — top-right corner
    fig.add_annotation(
        text=f"{n_outliers} điểm outlier đã lọc (PM2.5 ≥ 150)",
        xref="paper", yref="paper",
        x=0.99, y=0.97,
        xanchor="right", yanchor="top",
        showarrow=False,
        font=dict(size=11, color="#888888"),
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="#CCCCCC",
        borderwidth=1,
    )

    fig.update_layout(
        height=500,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(
            title=x_label,
            showgrid=True,
            gridcolor="#EEEEEE",
        ),
        # Fix 3: fixed y-axis range (0, 80)
        yaxis=dict(
            title="PM2.5 (µg/m³)",
            range=list(ylim),
            showgrid=True,
            gridcolor="#EEEEEE",
            zeroline=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=80, b=60, l=60, r=30),
    )
    return fig, r_val**2, slope, intercept, n_outliers


# ── Section 4: Chart 3 — Heatmap CO theo Giờ × Tháng ────────────────────────
def render_chart3_co_heatmap(df: pd.DataFrame) -> None:
    """
    Chart 3: Heatmap CO trung bình theo (giờ trong ngày × tháng).
    Lọc CO < 0 và CO > percentile 99 trước khi tính pivot.
    Gradient: trắng → xanh lá nhạt → xanh lá đậm.
    """
    render_section_header("Heatmap CO trung bình theo Giờ × Tháng")

    tmp = df.copy()
    tmp["hour"]  = tmp["Datetime"].dt.hour
    tmp["month"] = tmp["Datetime"].dt.month

    # Lọc CO < 0 và CO > p99
    co_p99 = tmp["CO"].quantile(0.99)
    tmp = tmp[(tmp["CO"] >= 0) & (tmp["CO"] <= co_p99)]

    pivot = (
        tmp.groupby(["month", "hour"])["CO"]
        .mean()
        .round(1)
        .unstack(level="hour")          # 12 hàng (tháng) × 24 cột (giờ)
        .reindex(index=range(1, 13), columns=range(24))
    )

    MONTH_LABELS = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
        "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
        "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
    ]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(range(24)),
        y=MONTH_LABELS,
        # Gradient: trắng → xanh lá nhạt → xanh lá đậm
        colorscale=[
            [0.00, "#FFFFFF"],
            [0.30, "#C8E6C9"],
            [0.60, "#43A047"],
            [1.00, "#1B5E20"],
        ],
        colorbar=dict(
            title=dict(text="CO<br>(µg/m³)", side="right"),
            thickness=16,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Giờ: %{x}:00<br>"
            "CO TB: %{z:.0f} µg/m³<extra></extra>"
        ),
        xgap=1,
        ygap=1,
    ))

    fig.update_layout(
        height=450,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(
            text="Heatmap CO trung bình theo Giờ × Tháng",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Giờ trong ngày",
            tickmode="array",
            tickvals=list(range(0, 24, 2)),
            ticktext=[f"{h}:00" for h in range(0, 24, 2)],
        ),
        yaxis=dict(
            title="Tháng",
            autorange="reversed",   # Tháng 1 ở trên cùng
        ),
        margin=dict(t=70, b=60, l=100, r=30),
    )

    # Annotation: ngưỡng lọc p99
    fig.add_annotation(
        text=f"Đã lọc CO > p99 ({co_p99:,.0f} µg/m³)",
        xref="paper", yref="paper",
        x=0.99, y=0.01,
        xanchor="right", yanchor="bottom",
        showarrow=False,
        font=dict(size=11, color="#888888"),
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="#CCCCCC",
        borderwidth=1,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Màu đậm = CO cao. "
        "CO phản ánh trực tiếp khí thải giao thông theo giờ cao điểm và mùa khô."
    )
    st.caption("\\* Hiển thị toàn bộ giai đoạn 2021–2022, không bị ảnh hưởng bởi bộ lọc ngày.")
    _insight_chart3(df)


# ── Section 5: Chart 4 — Xu hướng tháng PM2.5, CO, NO2 chuẩn hóa ────────────
def render_chart4_normalized_trend(df: pd.DataFrame) -> None:
    """
    Chart 4: Xu hướng tháng của PM2.5, CO, NO2 sau min-max normalization.
    Vẽ 3 đường trên cùng trục Y (0–1), nền vàng mùa khô.
    """
    render_section_header("Xu hướng PM2.5, CO, NO2 theo tháng (chuẩn hóa)")

    tmp = df.copy()
    tmp["YearMonth"] = tmp["Datetime"].dt.to_period("M")

    # Trung bình tháng, gộp tất cả trạm
    monthly = (
        tmp.groupby("YearMonth")[["PM2.5", "CO", "NO2"]]
        .mean()
        .reset_index()
        .sort_values("YearMonth")
    )
    monthly["Date"] = monthly["YearMonth"].dt.to_timestamp()   # Period → Timestamp để Plotly hiểu

    # Min-max normalization (0–1) cho từng biến
    for col in ["PM2.5", "CO", "NO2"]:
        col_min = monthly[col].min()
        col_max = monthly[col].max()
        monthly[f"{col}_norm"] = (
            (monthly[col] - col_min) / (col_max - col_min)
        ).round(4)

    fig = go.Figure()

    # ── Nền mùa khô (Nov–Apr) — giống Chart 1
    date_min = monthly["Date"].min()
    date_max = monthly["Date"].max()
    dry_label_added = False
    rain_label_added = False
    for yr in range(date_min.year, date_max.year + 2):
        dry_start = max(pd.Timestamp(yr - 1, 11, 1), date_min)
        dry_end   = min(pd.Timestamp(yr, 4, 30),     date_max)
        if dry_start < dry_end:
            fig.add_vrect(
                x0=dry_start, x1=dry_end,
                fillcolor="#FFF3CD",
                opacity=0.35,
                line_width=0,
                layer="below",
                annotation_text="Mùa khô" if not dry_label_added else "",
                annotation_position="top left",
                annotation_font=dict(size=11, color="#8B6914"),
            )
            dry_label_added = True

        rain_start = max(pd.Timestamp(yr, 5, 1),   date_min)
        rain_end   = min(pd.Timestamp(yr, 10, 31), date_max)
        if rain_start < rain_end:
            center_rain = rain_start + (rain_end - rain_start) / 2
            if not rain_label_added:
                fig.add_annotation(
                    x=center_rain, y=1.0, yref="paper",
                    text="Mùa mưa",
                    showarrow=False,
                    font=dict(size=11, color="#888888"),
                    xanchor="center",
                )
                rain_label_added = True

    # ── 3 đường chuẩn hóa
    LINES = [
        ("PM2.5_norm", "PM2.5",  "#1A5FA8", "circle"),    # xanh đậm
        ("CO_norm",    "CO",     "#2E7D32", "square"),    # xanh lá
        ("NO2_norm",   "NO2",    "#E65100", "diamond"),   # cam
    ]
    for col_norm, label, color, symbol in LINES:
        # Build tooltip showing both normalized and original value
        orig_col = label
        fig.add_trace(go.Scatter(
            x=monthly["Date"],
            y=monthly[col_norm],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.5),
            marker=dict(symbol=symbol, size=7, color=color),
            customdata=monthly[[orig_col]].round(1).values,
            hovertemplate=(
                f"<b>{label}</b><br>"
                "%{x|%m/%Y}<br>"
                "Chuẩn hóa: %{y:.3f}<br>"
                f"Giá trị gốc: %{{customdata[0]:.1f}}<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=450,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(
            text="Xu hướng PM2.5, CO, NO2 theo tháng (chuẩn hóa 0–1)",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Tháng",
            tickformat="%m/%Y",
            dtick="M1",
            tickangle=-30,
            showgrid=True,
            gridcolor="#EEEEEE",
            range=[
                pd.Timestamp("2021-02-01"),
                pd.Timestamp("2022-07-01"),
            ],
        ),
        yaxis=dict(
            title="Giá trị chuẩn hóa (0–1)",
            range=[-0.05, 1.15],
            showgrid=True,
            gridcolor="#EEEEEE",
            zeroline=False,
        ),
        legend=dict(
            title=dict(text="Chất ô nhiễm"),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#CCCCCC",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(t=80, b=70, l=60, r=30),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "3 chất ô nhiễm biến động cùng chiều trong mùa khô — "
        "xác nhận nguồn thải chủ yếu từ giao thông và đốt sinh khối. "
        "Trục Y chuẩn hóa 0–1 giúp so sánh xu hướng giữa các biến có đơn vị khác nhau."
    )
    st.caption("\\* Hiển thị toàn bộ giai đoạn 2021–2022, không bị ảnh hưởng bởi bộ lọc ngày.")
    _insight_chart4(df)


# ── Section 6: Chart 5 — Drill-down 24 giờ ──────────────────────────────────
def render_chart5_hourly_drilldown(df: pd.DataFrame, start_date, end_date) -> None:
    """
    Chart 5: PM2.5, CO, NO2 theo từng giờ với toggle 2 chế độ.

    Aggregation logic:
    - 1 ngày  → dùng data thực của ngày đó, group by hour
    - >1 ngày → group by hour rồi tính MEAN qua tất cả ngày + trạm đã chọn
                (1 bộ 3 đường duy nhất, chuẩn hóa SAU khi group)
    """
    from plotly.subplots import make_subplots

    is_single_day = (start_date == end_date)
    n_days = (end_date - start_date).days + 1

    # ── Tiêu đề động
    if is_single_day:
        date_label    = start_date.strftime("%d/%m/%Y")
        title_prefix  = "Chất lượng không khí theo giờ"
    else:
        date_label    = f"{start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}"
        title_prefix  = "Chất lượng không khí trung bình theo giờ"

    render_section_header(f"{title_prefix} — {date_label}")
    st.caption("Hiển thị pattern 24 giờ — trung bình toàn khoảng thời gian đã chọn")

    # ── Toggle 2 nút pill-style
    col_toggle, col_spacer = st.columns([0.3, 0.7])
    with col_toggle:
        view_mode = st.radio(
            label="Chế độ hiển thị",
            options=["📈 Xu hướng (0–1)", "🔢 Giá trị thực"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )
    is_normalized = (view_mode == "📈 Xu hướng (0–1)")

    # ── Aggregation: group by hour → mean (gộp tất cả ngày + trạm trong range)
    # Cả 1 ngày lẫn nhiều ngày đều dùng cùng logic này —
    # khi 1 ngày thì mean chỉ có 1 giá trị/giờ nên kết quả = data thực.
    tmp = df.copy()
    tmp["hour"] = tmp["Datetime"].dt.hour
    hourly = (
        tmp.groupby("hour")[["PM2.5", "CO", "NO2"]]
        .mean()
        .round(3)
        .reindex(range(24))
        .reset_index()
    )

    # ── Min-max normalization SAU khi group by hour
    norm = {}
    raw_min, raw_max = {}, {}
    for col in ["PM2.5", "CO", "NO2"]:
        col_min = hourly[col].min()
        col_max = hourly[col].max()
        raw_min[col] = col_min
        raw_max[col] = col_max
        denom = col_max - col_min if col_max != col_min else 1.0
        norm[col] = ((hourly[col] - col_min) / denom).round(4)

    # ── Phát hiện PM2.5 peak bất thường
    NORMAL_PEAK_HOURS = set(range(5, 11)) | set(range(15, 21))
    peak_hour = int(hourly["PM2.5"].idxmax())
    peak_is_abnormal = peak_hour not in NORMAL_PEAK_HOURS

    # ── Tạo figure — normalized mode: single axis, actual mode: dual axis
    if is_normalized:
        fig = go.Figure()
        peak_y_val = float(norm["PM2.5"].iloc[peak_hour])
    else:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        peak_y_val = float(hourly["PM2.5"].iloc[peak_hour])

    # ── Vùng highlight giờ cao điểm (#FFF9C4, opacity 0.4) — giữ cả 2 chế độ
    PEAK_BANDS = [
        (6,  9,  "Cao điểm sáng",  0.93),
        (16, 19, "Cao điểm chiều", 0.93),
    ]
    for h_start, h_end, label, y_ann in PEAK_BANDS:
        fig.add_vrect(
            x0=h_start - 0.5, x1=h_end + 0.5,
            fillcolor="#FFF9C4",
            opacity=0.4,
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            x=(h_start + h_end) / 2,
            y=y_ann,
            yref="paper",
            text=label,
            showarrow=False,
            font=dict(size=10, color="#B8860B"),
            xanchor="center",
            bgcolor="rgba(255,249,196,0.7)",
        )

    # ── Vẽ 3 đường theo chế độ
    if is_normalized:
        # ── Chế độ "Xu hướng (0–1)" — chuẩn hóa cả 3, 1 trục Y
        fig.add_trace(go.Scatter(
            x=hourly["hour"],
            y=norm["PM2.5"],
            mode="lines+markers",
            name="PM2.5",
            line=dict(color="#1A5FA8", width=3.5, dash="solid"),
            marker=dict(size=6, symbol="circle"),
            customdata=hourly[["PM2.5"]].round(1).values,
            hovertemplate=(
                "<b>PM2.5</b><br>"
                "Giờ %{x}:00<br>"
                "%{y:.3f} (norm) | %{customdata[0]:.1f} µg/m³ (thực)<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=hourly["hour"],
            y=norm["CO"],
            mode="lines+markers",
            name="CO",
            line=dict(color="#2E7D32", width=2.5, dash="dash"),
            marker=dict(size=6, symbol="square"),
            customdata=hourly[["CO"]].round(0).values,
            hovertemplate=(
                "<b>CO</b><br>"
                "Giờ %{x}:00<br>"
                "%{y:.3f} (norm) | %{customdata[0]:,.0f} µg/m³ (thực)<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=hourly["hour"],
            y=norm["NO2"],
            mode="lines+markers",
            name="NO2",
            line=dict(color="#E65100", width=2.5, dash="dot"),
            marker=dict(size=6, symbol="diamond"),
            customdata=hourly[["NO2"]].round(1).values,
            hovertemplate=(
                "<b>NO2</b><br>"
                "Giờ %{x}:00<br>"
                "%{y:.3f} (norm) | %{customdata[0]:.1f} µg/m³ (thực)<extra></extra>"
            ),
        ))
        # Không có đường WHO trong chế độ normalized

    else:
        # ── Chế độ "Giá trị thực" — PM2.5 trục trái, CO+NO2 trục phải
        fig.add_trace(
            go.Scatter(
                x=hourly["hour"],
                y=hourly["PM2.5"],
                mode="lines+markers",
                name="PM2.5",
                line=dict(color="#1A5FA8", width=3.5, dash="solid"),
                marker=dict(size=6, symbol="circle"),
                hovertemplate="Giờ %{x}:00<br>PM2.5: %{y:.1f} µg/m³<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=hourly["hour"],
                y=hourly["CO"],
                mode="lines+markers",
                name="CO",
                line=dict(color="#2E7D32", width=2.5, dash="dash"),
                marker=dict(size=6, symbol="square"),
                hovertemplate="Giờ %{x}:00<br>CO: %{y:,.0f} µg/m³<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(
                x=hourly["hour"],
                y=hourly["NO2"],
                mode="lines+markers",
                name="NO2",
                line=dict(color="#E65100", width=2.5, dash="dot"),
                marker=dict(size=6, symbol="diamond"),
                hovertemplate="Giờ %{x}:00<br>NO2: %{y:.1f} µg/m³<extra></extra>",
            ),
            secondary_y=True,
        )
        # Đường WHO chỉ cho PM2.5 (trục trái)
        fig.add_hline(
            y=WHO_PM25,
            line_dash="dash",
            line_color="red",
            line_width=1.8,
            annotation_text=f"WHO PM2.5: {WHO_PM25} µg/m³",
            annotation_position="bottom right",
            annotation_font=dict(color="red", size=11),
            secondary_y=False,
        )

    # ── Annotation peak bất thường — giữ cả 2 chế độ
    if peak_is_abnormal:
        fig.add_annotation(
            x=peak_hour,
            y=peak_y_val,
            text=f"⚠️ Peak bất thường — {peak_hour}:00",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor="#D84315",
            font=dict(size=11, color="#D84315"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#D84315",
            borderwidth=1,
            ax=40,
            ay=-45,
        )

    # ── Layout chung
    fig.update_layout(
        height=450,
        width=1200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=13),
        title=dict(
            text=f"{title_prefix} — {date_label}",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Giờ trong ngày",
            tickmode="array",
            tickvals=list(range(0, 24)),
            ticktext=[f"{h}:00" for h in range(0, 24)],
            tickangle=-45,
            showgrid=True,
            gridcolor="#EEEEEE",
            range=[-0.5, 23.5],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left",   x=0,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#CCCCCC",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(t=90, b=70, l=60, r=80),
    )

    # ── Trục Y theo chế độ
    if is_normalized:
        fig.update_yaxes(
            title_text="Giá trị chuẩn hóa (0–1)",
            range=[-0.05, 1.15],
            showgrid=True,
            gridcolor="#EEEEEE",
            zeroline=False,
        )
        avg_note = "" if is_single_day else f" (trung bình {n_days} ngày)"
        caption_text = (
            f"Trung bình theo giờ trong ngày của {n_days} ngày được chọn. "
            "Khoảng trắng = giờ bị loại do sensor flag lỗi. "
            "Chuẩn hóa 0–1 để so sánh xu hướng 3 chất cùng scale. "
            "Hover để xem giá trị thực. "
            "Vùng vàng = giờ cao điểm giao thông."
        )
    else:
        fig.update_yaxes(
            title_text="PM2.5 (µg/m³)",
            showgrid=True,
            gridcolor="#EEEEEE",
            zeroline=False,
            secondary_y=False,
        )
        fig.update_yaxes(
            title_text="CO / NO2 (µg/m³)",
            showgrid=False,
            zeroline=False,
            secondary_y=True,
        )
        avg_note = "" if is_single_day else f" (trung bình {n_days} ngày)"
        caption_text = (
            f"Trung bình theo giờ trong ngày của {n_days} ngày được chọn. "
            "Khoảng trắng = giờ bị loại do sensor flag lỗi. "
            "Giá trị đo thực tế. "
            "Đường đỏ = ngưỡng WHO cho PM2.5 (15 µg/m³). "
            "Vùng vàng = giờ cao điểm giao thông."
        )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(caption_text)
    _insight_chart5(df)


# ── Main app ──────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Air Quality Dashboard — HCMC",
        page_icon="🌫️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_global_css()

    render_page_header(
        "Xu hướng ô nhiễm theo thời gian",
        "Phân tích chất lượng không khí dựa trên dữ liệu từ 6 trạm quan trắc, giai đoạn 2021–2022."
    )

    # ── Pill-style toggle CSS (áp dụng cho st.radio horizontal trong Chart 5)
    st.markdown("""
    <style>
    div[data-testid="stRadio"] > label { display: none; }
    div[data-testid="stRadio"] > div {
        display: flex; flex-direction: row; gap: 6px; background: transparent;
    }
    div[data-testid="stRadio"] > div > label {
        display: flex !important; align-items: center;
        padding: 4px 14px; border-radius: 20px;
        border: 1.5px solid #CCCCCC; background: #FFFFFF;
        color: #888888; font-size: 13px; cursor: pointer;
        transition: all 0.15s ease; white-space: nowrap;
    }
    div[data-testid="stRadio"] > div > label > div:first-child { display: none; }
    div[data-testid="stRadio"] > div > label:has(input:checked) {
        background: #16324F; border-color: #16324F; color: #FFFFFF; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    # Load data (cached)
    df = load_data()

    # Sidebar → filter values
    start_date, end_date, selected_stations = build_sidebar(df)

    # Validate selections
    if not selected_stations:
        st.warning("⚠️ Vui lòng chọn ít nhất một trạm quan trắc ở thanh bên trái.")
        st.stop()

    if start_date > end_date:
        st.warning("⚠️ Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")
        st.stop()

    # ── Fix 1: Tách scope bộ lọc
    # filtered_time  = date + station  → dùng cho Chart 1, Chart 5, KPIs
    # filtered_station = station only  → dùng cho Chart 2, 3, 4 (toàn bộ giai đoạn)
    filtered_time = apply_filters(df, start_date, end_date, selected_stations)
    filtered_station = df[df["Station_No"].isin(selected_stations)].copy()

    if filtered_time.empty:
        st.warning("⚠️ Không có dữ liệu sạch trong khoảng thời gian và trạm đã chọn.")
        st.stop()
    n_days = (end_date - start_date).days + 1


    # ── KPIs — dùng filtered_time (date + station)
    render_kpis(filtered_time)

    render_divider()

    # ── Chart 1 — dùng filtered_time (date + station)
    render_chart1_pm25_trend(filtered_time)

    st.divider()

    # ── Chart 2 — Fix 1: dùng filtered_station (toàn bộ giai đoạn)
    render_chart2_heatmap(filtered_station)

    st.divider()

    # ── Chart 3 — Fix 1: dùng filtered_station (toàn bộ giai đoạn)
    render_chart3_co_heatmap(filtered_station)

    st.divider()

    # ── Chart 4 — Fix 1: dùng filtered_station (toàn bộ giai đoạn)
    render_chart4_normalized_trend(filtered_station)

    st.divider()

    # ── Chart 5 — Fix 2: chỉ hiển thị khi date range ≤ 7 ngày
    if n_days <= 7:
        render_chart5_hourly_drilldown(filtered_time, start_date, end_date)
    else:
        render_insight_box([
            "Chọn khoảng thời gian <b>≤ 7 ngày</b> để xem phân tích chi tiết theo từng giờ."
        ], title="Phân tích chi tiết 24 giờ", icon_name="trend")


if __name__ == "__main__":
    main()
