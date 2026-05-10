from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui_theme import get_icon_html, render_conclusion_box


class GoalOneConclusion:
    """Reusable conclusion block for Goal 1 time-trend analysis."""

    WHO_PM25 = 15.0
    DRY_MONTHS = {11, 12, 1, 2, 3, 4}
    RAIN_MONTHS = {5, 6, 7, 8, 9, 10}

    @staticmethod
    def render(
        station_df: pd.DataFrame,
        time_df: pd.DataFrame,
        start_date,
        end_date,
        n_days: int,
    ) -> None:
        if len(station_df) < 10 or len(time_df) < 10:
            st.markdown(
                "<div style='background:#F0F7FF; border-left:4px solid #2E86AB; border-radius:8px; padding:20px; color:#16324F; font-weight:600;'>Không đủ dữ liệu để tổng hợp kết luận</div>",
                unsafe_allow_html=True,
            )
            return

        if n_days <= 7:
            title, bullet_lines, action_line = GoalOneConclusion._build_short_range(
                station_df=station_df,
                time_df=time_df,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            title, bullet_lines, action_line = GoalOneConclusion._build_long_range(station_df)

        bullets_html = "".join(
            f"<li>{line}</li>" for line in bullet_lines
        )

        st.markdown("---")
        st.markdown(f"### {get_icon_html('trend')} Kết luận", unsafe_allow_html=True)

        content_html = f"""
            <h4 style="margin-top:0; color:#2E86AB;">
                {get_icon_html('analysis')} {title}
            </h4>
            <ol style="margin-bottom: 0;">
                {bullets_html}
                <li><i style="color:#2E86AB; font-weight:600;">{action_line}</i></li>
            </ol>
        """
        render_conclusion_box(content_html, accent_color="#2E86AB")

    @staticmethod
    def _build_long_range(station_df: pd.DataFrame):
        tmp = station_df.copy()
        tmp["month"] = tmp["Datetime"].dt.month
        tmp["hour"] = tmp["Datetime"].dt.hour
        tmp["year_month"] = tmp["Datetime"].dt.to_period("M")

        dry = tmp[tmp["month"].isin(GoalOneConclusion.DRY_MONTHS)]["PM2.5"].mean()
        rain = tmp[tmp["month"].isin(GoalOneConclusion.RAIN_MONTHS)]["PM2.5"].mean()
        seasonal_diff_pct = ((dry - rain) / rain * 100) if pd.notna(dry) and pd.notna(rain) and rain > 0 else float("nan")

        hourly = tmp.groupby("hour")["PM2.5"].mean().reindex(range(24))
        peak_hour = int(hourly.idxmax())
        peak_val = float(hourly.max())
        low_hour = int(hourly.idxmin())
        low_hour_val = float(hourly.min())

        monthly = tmp.groupby("year_month")[["PM2.5", "CO"]].mean().reset_index()
        monthly["Date"] = monthly["year_month"].dt.to_timestamp()
        co_dry = tmp[tmp["month"].isin(GoalOneConclusion.DRY_MONTHS)]["CO"].mean()
        co_rain = tmp[tmp["month"].isin(GoalOneConclusion.RAIN_MONTHS)]["CO"].mean()
        co_diff_pct = ((co_dry - co_rain) / co_rain * 100) if pd.notna(co_dry) and pd.notna(co_rain) and co_rain > 0 else float("nan")
        r = monthly["PM2.5"].corr(monthly["CO"])

        peak_month_row = monthly.loc[monthly["PM2.5"].idxmax()]
        clean_month_row = monthly.loc[monthly["PM2.5"].idxmin()]
        peak_month_label = peak_month_row["year_month"].strftime("%m/%Y")
        clean_month_label = clean_month_row["year_month"].strftime("%m/%Y")
        peak_month_val = float(peak_month_row["PM2.5"])
        clean_month_val = float(clean_month_row["PM2.5"])
        wh_ratio = peak_month_val / GoalOneConclusion.WHO_PM25 if GoalOneConclusion.WHO_PM25 > 0 else float("nan")

        if pd.notna(seasonal_diff_pct):
            title = (
                f"Ô nhiễm PM2.5 mang tính chu kỳ mùa rõ rệt — "
                f"mùa khô ô nhiễm hơn mùa mưa {seasonal_diff_pct:.1f}%"
            )
        else:
            title = "Ô nhiễm PM2.5 mang tính chu kỳ mùa rõ rệt"

        bullet_1 = (
            f"Mùa khô (tháng 11–4): PM2.5 trung bình <b>{dry:.1f} µg/m³</b> — "
            f"cao hơn {seasonal_diff_pct:.1f}% so với mùa mưa (<b>{rain:.1f} µg/m³</b>)"
            if pd.notna(seasonal_diff_pct)
            else "Thiếu dữ liệu mùa khô/mùa mưa để so sánh đầy đủ trong khoảng trạm đã chọn."
        )

        if pd.notna(peak_val):
            if peak_hour in range(6, 10):
                peak_note = "— trùng giờ cao điểm giao thông buổi sáng"
            elif peak_hour in range(16, 20):
                peak_note = "— trùng giờ cao điểm giao thông buổi chiều"
            else:
                peak_note = "— lệch khỏi giờ cao điểm giao thông thông thường"
            bullet_2 = (
                f"Giờ ô nhiễm nhất: <b>{peak_hour}:00</b> (PM2.5 = <b>{peak_val:.1f} µg/m³</b>) {peak_note}"
            )
        else:
            bullet_2 = "Không xác định được giờ ô nhiễm nhất do thiếu dữ liệu hợp lệ."

        if pd.notna(co_diff_pct) and pd.notna(r):
            co_dir = "cao hơn" if co_diff_pct >= 0 else "thấp hơn"
            bullet_3 = (
                f"CO {co_dir} <b>{abs(co_diff_pct):.1f}%</b> vào mùa khô "
                f"(r = <b>{r:.2f}</b> với PM2.5 theo tháng) — xác nhận giao thông là nguồn phát thải chính"
            )
        else:
            bullet_3 = "Chưa đủ dữ liệu để xác nhận đồng biến giữa CO và PM2.5 theo tháng."

        bullet_4 = (
            f"Tháng ô nhiễm nhất: <b>Tháng {peak_month_label}</b> (<b>{peak_month_val:.1f} µg/m³</b>, gấp <b>{wh_ratio:.1f}</b> lần ngưỡng WHO). "
            f"Tháng sạch nhất: <b>Tháng {clean_month_label}</b> (<b>{clean_month_val:.1f} µg/m³</b>)"
        )

        action = (
            f"Hạn chế ra đường vào <b>{peak_hour}:00</b> trong tháng <b>{peak_month_label}</b>. "
            f"Thời điểm an toàn nhất: tháng <b>{clean_month_label}</b>, sau <b>{low_hour}:00</b> "
            f"(PM2.5 = <b>{low_hour_val:.1f} µg/m³</b>)"
        )

        return title, [bullet_1, bullet_2, bullet_3, bullet_4], action

    @staticmethod
    def _build_short_range(station_df: pd.DataFrame, time_df: pd.DataFrame, start_date, end_date):
        range_tmp = time_df.copy()
        overall_tmp = station_df.copy()

        range_tmp["hour"] = range_tmp["Datetime"].dt.hour
        overall_tmp["hour"] = overall_tmp["Datetime"].dt.hour

        range_mean = range_tmp["PM2.5"].mean()
        overall_mean = overall_tmp["PM2.5"].mean()
        diff_pct = ((range_mean - overall_mean) / overall_mean * 100) if pd.notna(range_mean) and pd.notna(overall_mean) and overall_mean > 0 else float("nan")
        direction = "cao hơn" if pd.notna(diff_pct) and diff_pct >= 0 else "thấp hơn"

        range_hourly = range_tmp.groupby("hour")["PM2.5"].mean().reindex(range(24))
        overall_hourly = overall_tmp.groupby("hour")["PM2.5"].mean().reindex(range(24))

        peak_hour = int(range_hourly.idxmax())
        peak_val = float(range_hourly.max())
        baseline_peak_hour = int(overall_hourly.idxmax())

        if 6 <= peak_hour <= 9:
            peak_context = "trong"
        else:
            peak_context = "ngoài"

        if abs(peak_hour - baseline_peak_hour) <= 1:
            pattern_text = "Pattern điển hình — nhất quán với xu hướng toàn giai đoạn"
        else:
            pattern_text = (
                f"Pattern bất thường — PM2.5 đỉnh lúc <b>{peak_hour}:00</b>, "
                f"lệch khỏi giờ cao điểm toàn giai đoạn (<b>{baseline_peak_hour}:00</b>). "
                "Có thể do sự kiện cục bộ hoặc khí tượng đặc biệt"
            )

        hours_meeting_who = int((range_hourly < GoalOneConclusion.WHO_PM25).sum())
        lowest_hour = int(range_hourly.idxmin())
        lowest_val = float(range_hourly.min())

        title = (
            f"Phân tích chi tiết: {start_date.strftime('%d/%m/%Y')} – {end_date.strftime('%d/%m/%Y')}"
        )
        bullet_1 = (
            f"PM2.5 trung bình khoảng này: <b>{range_mean:.1f} µg/m³</b> — {direction} "
            f"<b>{abs(diff_pct):.1f}%</b> so với toàn giai đoạn (<b>{overall_mean:.1f} µg/m³</b>)"
            if pd.notna(diff_pct)
            else "Chưa đủ dữ liệu để so sánh với toàn giai đoạn."
        )
        bullet_2 = (
            f"Giờ ô nhiễm nhất: <b>{peak_hour}:00</b> (<b>{peak_val:.1f} µg/m³</b>) — {peak_context} giờ cao điểm thông thường (6–9h)"
        )
        bullet_3 = pattern_text
        bullet_4 = (
            f"Có <b>{hours_meeting_who}/24 giờ</b> đạt chuẩn WHO (<15 µg/m³) trong khoảng này"
        )
        action = (
            f"Thời điểm ra đường an toàn nhất trong khoảng này: <b>{lowest_hour}:00</b> "
            f"(PM2.5 = <b>{lowest_val:.1f} µg/m³</b>)"
        )

        return title, [bullet_1, bullet_2, bullet_3, bullet_4], action
