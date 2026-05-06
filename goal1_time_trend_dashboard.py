from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


DEFAULT_DATA_PATH = Path("data/cleaned/Air_Quality_HCMC_Cleaned.csv")
STATIONS = [1, 2, 3, 4, 5, 6]
WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
VN_MONTH_LABELS = [f"Tháng {i}" for i in range(1, 13)]


def normalize_datetime_column(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa dữ liệu thời gian về một cột `date` từ `date` hoặc cặp `Date` + `Hour`."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif {"Date", "Hour"}.issubset(df.columns):
        hour_text = df["Hour"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        hour_text = hour_text.where(hour_text.str.contains(":"), hour_text.str.zfill(2) + ":00:00")
        df["date"] = pd.to_datetime(
            df["Date"].astype(str).str.strip() + " " + hour_text,
            errors="coerce",
        )
    else:
        raise ValueError("Thiếu cột thời gian: cần `date` hoặc cặp `Date` + `Hour`.")

    return df


@st.cache_data
def load_data_from_path(file_path: str) -> pd.DataFrame:
    """Đọc dữ liệu từ đường dẫn CSV, chuẩn hóa cột thời gian và loại bỏ giá trị thiếu."""
    df = pd.read_csv(file_path)
    df = normalize_datetime_column(df)
    df = df.dropna(subset=["date"])
    df = df.dropna(subset=["PM2.5", "CO", "NO2"])
    return df


@st.cache_data
def load_data_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    """Đọc dữ liệu từ file upload dạng bytes, chuẩn hóa cột thời gian và loại bỏ giá trị thiếu."""
    from io import BytesIO

    df = pd.read_csv(BytesIO(file_bytes))
    df = normalize_datetime_column(df)
    df = df.dropna(subset=["date"])
    df = df.dropna(subset=["PM2.5", "CO", "NO2"])
    return df


def season_from_month(month: int) -> str:
    """Phân loại mùa theo tháng tại TP.HCM (mùa khô: 11-4, mùa mưa: 5-10)."""
    return "Mùa khô" if month in [11, 12, 1, 2, 3, 4] else "Mùa mưa"


def plot_chart1(df: pd.DataFrame) -> go.Figure:
    """Vẽ biểu đồ đường PM2.5 trung bình theo từng giờ trong ngày."""
    hourly = df.groupby(df["date"].dt.hour)["PM2.5"].mean().reindex(range(24))
    hourly_df = hourly.reset_index().rename(columns={"date": "hour", "PM2.5": "mean_pm25"})
    hourly_df.columns = ["hour", "mean_pm25"]

    fig = px.line(
        hourly_df,
        x="hour",
        y="mean_pm25",
        title="Trung bình PM2.5 theo giờ trong ngày",
        markers=True,
    )
    fig.update_traces(line=dict(color="#378ADD", width=3))
    fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="WHO: 15 µg/m³")
    fig.add_vrect(x0=6, x1=9, fillcolor="#FFD166", opacity=0.2, line_width=0)
    fig.add_vrect(x0=17, x1=20, fillcolor="#FFD166", opacity=0.2, line_width=0)
    fig.update_layout(
        xaxis_title="Giờ trong ngày",
        yaxis_title="PM2.5 trung bình (µg/m³)",
        xaxis=dict(dtick=1, range=[-0.5, 23.5]),
    )
    return fig


def plot_chart2(df: pd.DataFrame) -> go.Figure:
    """Vẽ heatmap PM2.5 theo trục giờ và ngày trong tuần, đồng thời đánh dấu ô cực đại."""
    temp = df.copy()
    temp["hour"] = temp["date"].dt.hour
    temp["dow"] = temp["date"].dt.day_name().str[:3]

    pivot = temp.pivot_table(index="dow", columns="hour", values="PM2.5", aggfunc="mean")
    pivot = pivot.reindex(WEEKDAY_ORDER).reindex(columns=range(24))

    y_numeric = list(range(len(WEEKDAY_ORDER)))
    fig = px.imshow(
        pivot.values,
        x=list(range(24)),
        y=y_numeric,
        labels={"x": "Giờ", "y": "Ngày trong tuần", "color": "PM2.5 (µg/m³)"},
        color_continuous_scale="YlOrRd",
        aspect="auto",
        title="Heatmap PM2.5 — Giờ × Ngày trong tuần",
    )

    fig.update_yaxes(tickmode="array", tickvals=y_numeric, ticktext=WEEKDAY_ORDER)
    fig.update_xaxes(dtick=1)

    stacked = pivot.stack(dropna=True)
    if not stacked.empty:
        peak_day, peak_hour = stacked.idxmax()
        row_idx = WEEKDAY_ORDER.index(peak_day)
        fig.add_shape(
            type="rect",
            x0=peak_hour - 0.5,
            x1=peak_hour + 0.5,
            y0=row_idx - 0.5,
            y1=row_idx + 0.5,
            line=dict(color="white", width=2),
            fillcolor="rgba(0,0,0,0)",
        )
    return fig


def _add_season_bands(fig: go.Figure, monthly: pd.DataFrame) -> None:
    """Thêm dải nền theo mùa (mùa khô/mùa mưa) cho biểu đồ theo tháng."""
    if monthly.empty:
        return

    season_colors = {
        "Mùa khô": "rgba(186,117,23,0.10)",
        "Mùa mưa": "rgba(29,158,117,0.10)",
    }

    monthly = monthly.sort_values("date").copy()
    monthly["season"] = monthly["date"].dt.month.map(season_from_month)

    start_idx = 0
    while start_idx < len(monthly):
        current_season = monthly.iloc[start_idx]["season"]
        end_idx = start_idx
        while end_idx + 1 < len(monthly) and monthly.iloc[end_idx + 1]["season"] == current_season:
            end_idx += 1

        start_date = monthly.iloc[start_idx]["date"]
        if end_idx + 1 < len(monthly):
            end_date = monthly.iloc[end_idx + 1]["date"]
        else:
            end_date = monthly.iloc[end_idx]["date"] + pd.offsets.MonthBegin(1)

        fig.add_vrect(
            x0=start_date,
            x1=end_date,
            fillcolor=season_colors[current_season],
            line_width=0,
            layer="below",
        )

        center_date = start_date + (end_date - start_date) / 2
        fig.add_annotation(
            x=center_date,
            y=1.06,
            yref="paper",
            text=current_season,
            showarrow=False,
            font=dict(size=11, color="#5F5F5F"),
        )
        start_idx = end_idx + 1


def plot_chart3(df: pd.DataFrame) -> go.Figure:
    """Vẽ xu hướng trung bình theo tháng cho PM2.5, CO, NO2 với trục phụ cho CO."""
    monthly = (
        df.set_index("date")[["PM2.5", "CO", "NO2"]]
        .resample("MS")
        .mean()
        .reset_index()
        .sort_values("date")
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["PM2.5"],
            mode="lines+markers",
            name="PM2.5",
            line=dict(color="#378ADD", width=3),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["NO2"],
            mode="lines+markers",
            name="NO2",
            line=dict(color="#1D9E75", width=3),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["CO"],
            mode="lines+markers",
            name="CO",
            line=dict(color="#BA7517", width=3),
        ),
        secondary_y=True,
    )

    _add_season_bands(fig, monthly)

    fig.update_layout(
        title="Xu hướng ô nhiễm theo tháng — Mùa mưa vs Mùa khô",
        xaxis_title="Năm-Tháng",
        legend_title_text="Chất ô nhiễm",
    )
    fig.update_xaxes(tickformat="%Y-%m")
    fig.update_yaxes(title_text="PM2.5 / NO2 trung bình (µg/m³)", secondary_y=False)
    fig.update_yaxes(title_text="CO trung bình (µg/m³)", secondary_y=True)
    return fig


def plot_chart4(df: pd.DataFrame) -> go.Figure:
    """Vẽ box plot phân phối PM2.5 theo tháng và tô màu theo mùa."""
    temp = df.copy()
    temp["month"] = temp["date"].dt.month
    temp["month_label"] = temp["month"].apply(lambda m: f"Tháng {m}")
    temp["season"] = temp["month"].map(season_from_month)

    color_map = {"Mùa khô": "#BA7517", "Mùa mưa": "#1D9E75"}
    fig = px.box(
        temp,
        x="month_label",
        y="PM2.5",
        color="season",
        category_orders={"month_label": VN_MONTH_LABELS},
        color_discrete_map=color_map,
        points="outliers",
        title="Phân phối PM2.5 theo tháng",
        labels={"month_label": "Tháng", "PM2.5": "PM2.5 (µg/m³)", "season": "Mùa"},
    )
    fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="WHO: 15 µg/m³")
    fig.update_layout(boxmode="group")
    return fig


def render_goal1_section(file_path: Optional[str] = None) -> None:
    """Render toàn bộ dashboard Goal 1: Xu hướng ô nhiễm theo thời gian."""
    st.subheader("📊 Xu hướng Ô nhiễm Theo Thời gian")

    with st.sidebar:
        st.markdown("### Bộ lọc Goal 1")

    data_path = file_path if file_path else str(DEFAULT_DATA_PATH)
    uploaded = st.sidebar.file_uploader("Tải lên file CSV", type=["csv"])

    with st.spinner("Đang tải dữ liệu..."):
        if uploaded is not None:
            df = load_data_from_bytes(uploaded.getvalue())
        elif Path(data_path).exists():
            df = load_data_from_path(data_path)
        else:
            st.warning("Không tìm thấy file dữ liệu mặc định. Hãy tải lên file CSV.")
            return

    if df.empty:
        st.warning("Không có dữ liệu hợp lệ sau khi làm sạch")
        return

    min_date = df["date"].dt.date.min()
    max_date = df["date"].dt.date.max()

    selected_stations = st.sidebar.multiselect("Chọn trạm", options=STATIONS, default=STATIONS)
    selected_range = st.sidebar.date_input("Khoảng thời gian", value=(min_date, max_date))

    if not selected_stations:
        st.warning("Vui lòng chọn ít nhất một trạm")
        return

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date, end_date = min_date, max_date

    if start_date > end_date:
        st.warning("Khoảng thời gian không hợp lệ")
        return

    filtered = df[
        (df["Station_No"].isin(selected_stations))
        & (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
    ].copy()

    if filtered.empty:
        st.warning("Không có dữ liệu trong khoảng đã chọn")
        return

    kpi1 = filtered["PM2.5"].mean()
    peak_hour = filtered.groupby(filtered["date"].dt.hour)["PM2.5"].mean().idxmax()
    peak_month_ts = (
        filtered.set_index("date")["PM2.5"].resample("MS").mean().idxmax()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("PM2.5 trung bình", f"{kpi1:.2f} µg/m³")
    c2.metric("Giờ ô nhiễm nhất", f"{int(peak_hour):02d}:00")
    c3.metric("Tháng ô nhiễm nhất", peak_month_ts.strftime("%Y-%m"))

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        with st.container():
            fig1 = plot_chart1(filtered)
            st.plotly_chart(fig1, use_container_width=True)
            st.caption("PM2.5 thường tăng vào khung giờ cao điểm sáng và chiều, cho thấy ảnh hưởng từ mật độ giao thông.")
    with row1_col2:
        with st.container():
            fig2 = plot_chart2(filtered)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Heatmap cho thấy các điểm nóng PM2.5 tập trung theo giờ cố định trong tuần, hữu ích cho cảnh báo theo lịch.")

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        with st.container():
            fig3 = plot_chart3(filtered)
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Xu hướng theo tháng phản ánh khác biệt mùa mưa và mùa khô, đặc biệt rõ ở PM2.5 và NO2.")
    with row2_col2:
        with st.container():
            fig4 = plot_chart4(filtered)
            st.plotly_chart(fig4, use_container_width=True)
            st.caption("Phân phối theo tháng cho thấy mức biến động PM2.5 không đồng đều và xuất hiện nhiều ngoại lệ vào một số tháng.")


def main() -> None:
    """Điểm khởi chạy ứng dụng Streamlit cho Goal 1."""
    st.set_page_config(page_title="Goal 1 - Time-based Air Pollution Trend Analysis", layout="wide")
    render_goal1_section()


if __name__ == "__main__":
    main()
