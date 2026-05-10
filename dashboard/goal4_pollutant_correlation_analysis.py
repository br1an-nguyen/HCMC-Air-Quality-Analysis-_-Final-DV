import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from itertools import combinations
import os

from dashboard.ui_theme import (
    inject_global_css, render_standard_sidebar, render_page_header, render_divider,
    render_section_header, render_insight_box, render_conclusion_box, get_icon_html,
    BORDER, CANVAS_BG, TEXT_PRIMARY, TEXT_SECONDARY, GRIDLINE, POLLUTANT_COLORS,
    COLOR_POSITIVE, COLOR_NEGATIVE
)

# ── Design tokens ──────────────────────────────────────────────────────────────
C = {
    "CO": "#4E5D8A", "NO2": "#D98E04", "SO2": "#2B7BBB", "PM2.5": "#B23A2F",
    "hi": "#FFB703", "bg": "#FFFFFF", "card": "#FFFFFF",
    "border": "#D9E4EC", "text": "#16324F", "sub": "#4F6B7A",
    "grid": "#E5EEF3", "pos": "#1F8A70", "neg": "#B23A2F",
}

# WHO 24h guideline (μg/m³) — dùng cho KPI context
WHO = {"PM2.5": 15.0, "CO": 4000.0, "NO2": 25.0, "SO2": 40.0}

COLS      = ["CO", "NO2", "SO2", "PM2.5"]
UNITS     = {"CO": "μg/m³", "NO2": "μg/m³", "SO2": "μg/m³", "PM2.5": "μg/m³"}
ALL_PAIRS = list(combinations(COLS, 2))


# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    for col, flag in {"CO":"CO_flag","NO2":"NO2_flag","SO2":"SO2_flag","PM2.5":"PM2.5_flag"}.items():
        df.loc[df[flag] == 2, col] = np.nan
    return df


# ── Helpers ────────────────────────────────────────────────────────────────────
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
                font=dict(family="Segoe UI, sans-serif", color=C["text"]))

def _pair_key(a, b):
    return tuple(sorted([a, b]))

def _strength_label(r):
    if pd.isna(r): return "Không đủ dữ liệu", "ins-weak"
    ar = abs(r)
    if r < -0.1:   return "Nghịch biến nhẹ",       "ins-neg"
    if ar >= 0.6:  return "Tương quan mạnh",        "ins-strong"
    if ar >= 0.3:  return "Tương quan trung bình",  "ins-mid"
    return             "Tương quan yếu",            "ins-weak"

def _fmt_r(r):
    return "N/A" if pd.isna(r) else f"{r:+.3f}"

def _pair_insight(a, b, r):
    """Trả về (label, css_class, text) cho từng cặp — đủ 6 cặp."""
    lbl, css = _strength_label(r)
    key = _pair_key(a, b)

    # ── CO – SO2 ──────────────────────────────────────────────────────────────
    if key == ("CO", "SO2"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để đánh giá CO–SO₂ trong bộ lọc này."
        elif r >= 0.6:
            txt = ("CO và SO₂ tăng/giảm cùng pha rõ rệt (r = <b>{}</b>). "
                   "Cả hai đều sinh ra từ quá trình đốt cháy nhiên liệu — "
                   "đây là bằng chứng định lượng cho thấy giao thông diesel "
                   "đang chi phối nguồn phát thải tại các trạm được chọn.").format(_fmt_r(r))
        elif r >= 0.2:
            txt = ("CO–SO₂ đồng biến ở mức trung bình (r = <b>{}</b>). "
                   "Nguồn đốt cháy vẫn là yếu tố chung, nhưng sự khác biệt "
                   "theo trạm hoặc khung giờ đang làm suy giảm mức tương quan.").format(_fmt_r(r))
        else:
            txt = ("CO–SO₂ yếu trong phạm vi lọc này (r = <b>{}</b>). "
                   "Có thể do trạm/khung giờ được chọn phản ánh nguồn phát thải đa dạng hơn.").format(_fmt_r(r))

    # ── CO – NO2 ──────────────────────────────────────────────────────────────
    elif key == ("CO", "NO2"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để đánh giá CO–NO₂ trong bộ lọc này."
        elif abs(r) < 0.15:
            txt = ("CO–NO₂ rất yếu (r = <b>{}</b>) dù cùng từ khói xe. "
                   "Nguyên nhân: NO₂ còn được sinh ra từ phản ứng quang hóa ban ngày "
                   "và bị tiêu thụ bởi O₃, khiến nó không tích lũy song song với CO.").format(_fmt_r(r))
        elif r > 0.15:
            txt = ("CO–NO₂ dương rõ hơn mức thông thường (r = <b>{}</b>). "
                   "Bộ lọc hiện tại (khung giờ/trạm) đang nắm bắt giai đoạn "
                   "phát thải sơ cấp từ giao thông mà chưa có quang hóa đáng kể.").format(_fmt_r(r))
        else:
            txt = ("CO–NO₂ âm nhẹ (r = <b>{}</b>): khi CO cao (sáng sớm, tắc xe) "
                   "thì NO₂ quang hóa chưa kịp tích lũy, và ngược lại.").format(_fmt_r(r))

    # ── CO – PM2.5 ────────────────────────────────────────────────────────────
    elif key == ("CO", "PM2.5"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để kết luận CO–PM2.5."
        elif r >= 0.3:
            txt = ("CO–PM2.5 ở mức <b>{}</b>: giao thông đang đóng góp đáng kể "
                   "vào bụi mịn trong giai đoạn/trạm được chọn. "
                   "PM2.5 tại đây có thành phần sơ cấp từ đốt cháy là nổi bật.").format(_fmt_r(r))
        else:
            txt = ("CO–PM2.5 yếu (r = <b>{}</b>): PM2.5 là bài toán đa nguồn — "
                   "ngoài giao thông còn có gió, độ ẩm, mưa, xây dựng và đốt rác. "
                   "Không thể dùng CO đơn lẻ để dự báo PM2.5.").format(_fmt_r(r))

    # ── NO2 – PM2.5 ───────────────────────────────────────────────────────────
    elif key == ("NO2", "PM2.5"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để đánh giá NO₂–PM2.5."
        elif r < -0.1:
            txt = ("NO₂–PM2.5 âm nhẹ (r = <b>{}</b>): lệch pha thời gian rõ ràng — "
                   "NO₂ đỉnh ban ngày khi quang hóa mạnh, còn PM2.5 "
                   "tích lũy cao nhất sáng sớm khi ít gió và độ ẩm cao. "
                   "PM2.5 tại TP.HCM chủ yếu là bụi sơ cấp, chưa phải thứ cấp từ quang hóa.").format(_fmt_r(r))
        else:
            txt = ("NO₂–PM2.5 không âm trong bộ lọc này (r = <b>{}</b>). "
                   "Có thể điều kiện tích tụ không khí hoặc đóng góp bụi thứ cấp "
                   "đang xuất hiện rõ hơn trong giai đoạn/trạm được chọn.").format(_fmt_r(r))

    # ── NO2 – SO2 ─────────────────────────────────────────────────────────────
    elif key == ("NO2", "SO2"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để đánh giá NO₂–SO₂."
        elif abs(r) < 0.15:
            txt = ("NO₂–SO₂ rất yếu (r = <b>{}</b>): SO₂ chủ yếu từ diesel và công nghiệp, "
                   "trong khi NO₂ có thêm nguồn quang hóa ban ngày — "
                   "hai cơ chế hình thành khác nhau khiến chúng không đồng pha.").format(_fmt_r(r))
        elif r >= 0.15:
            txt = ("NO₂–SO₂ dương (r = <b>{}</b>): trong bộ lọc này, "
                   "có thể cả hai cùng tăng do điều kiện khí tượng tích tụ "
                   "hoặc nguồn công nghiệp/giao thông nặng tập trung.").format(_fmt_r(r))
        else:
            txt = ("NO₂–SO₂ âm nhẹ (r = <b>{}</b>): gợi ý nguồn phát thải "
                   "và chu kỳ hóa học của hai chất đang không đồng pha "
                   "trong phạm vi trạm/giờ đã lọc.").format(_fmt_r(r))

    # ── SO2 – PM2.5 ───────────────────────────────────────────────────────────
    elif key == ("PM2.5", "SO2"):
        if pd.isna(r):
            txt = "Chưa đủ dữ liệu để đánh giá SO₂–PM2.5."
        elif r >= 0.3:
            txt = ("SO₂–PM2.5 ở mức <b>{}</b>: SO₂ có thể đang đóng vai trò "
                   "tiền chất cho bụi thứ cấp sulfate (SO₄²⁻) — "
                   "thành phần PM2.5 thứ cấp hình thành khi SO₂ phản ứng với hơi nước.").format(_fmt_r(r))
        else:
            txt = ("SO₂–PM2.5 yếu (r = <b>{}</b>): đóng góp thứ cấp sulfate "
                   "chưa đủ để tạo tương quan rõ ràng; "
                   "PM2.5 tại đây chủ yếu vẫn là bụi sơ cấp từ giao thông và xây dựng.").format(_fmt_r(r))

    else:
        txt = ("r = <b>{}</b>. Mối quan hệ giữa hai chất trong phạm vi lọc này "
               "cần đánh giá thêm theo trạm cụ thể.").format(_fmt_r(r))

    return lbl, css, txt


def _pair_caption(xa, ya, r):
    """Caption ngắn 1 dòng cho pair-scatter nhỏ dưới mỗi chart."""
    key = _pair_key(xa, ya)
    ar  = abs(r) if not pd.isna(r) else 0

    if key == ("CO", "SO2"):
        if ar >= 0.5:
            return f"{get_icon_html('insight')} Đồng biến mạnh — cùng nguồn đốt cháy nhiên liệu."
        return f"{get_icon_html('warning')} Đồng biến yếu hơn kỳ vọng — kiểm tra trạm/giờ trong bộ lọc."
    elif key == ("CO", "NO2"):
        if ar < 0.15:
            return f"{get_icon_html('insight')} Rất yếu — NO₂ có thêm nguồn quang hóa, không chỉ từ giao thông."
        return f"{get_icon_html('insight')} Dương nhẹ (r = {_fmt_r(r)}) — phát thải sơ cấp đang nổi bật trong khung giờ này."
    elif key == ("CO", "PM2.5"):
        if ar >= 0.3:
            return f"{get_icon_html('insight')} Trung bình — giao thông có đóng góp rõ vào bụi mịn."
        return f"{get_icon_html('insight')} Yếu — PM2.5 chịu đa nguồn, giao thông chỉ là một phần."
    return f"r = {_fmt_r(r)} · {get_icon_html('insight')} Xem insight bên dưới để biết thêm."


def _scatter_dynamic_insights(sdf, x_col, y_col, color_mode, r_val):
    """Tối đa 4 insight động cho scatter tùy chỉnh."""
    insights = []
    n        = len(sdf)
    strength, _ = _strength_label(r_val)

    # 1. Tổng quan mức tương quan
    insights.append(
        f"Bộ lọc tạo ra <b>{n:,}</b> điểm hợp lệ cho cặp <b>{x_col}–{y_col}</b>. "
        f"Mức quan hệ tuyến tính: <b>{strength}</b> (r = {_fmt_r(r_val)})."
    )

    # 2. Chiều tương quan + slope OLS
    if not pd.isna(r_val) and n >= 20 and sdf[x_col].std() > 0:
        slope = np.polyfit(sdf[x_col].values, sdf[y_col].values, 1)[0]
        if r_val >= 0.3:
            insights.append(
                f"Đường xu hướng OLS dốc <b>+{slope:.4f}</b>: "
                f"khi <b>{x_col}</b> tăng 1 μg/m³, <b>{y_col}</b> trung bình tăng {slope:.4f} μg/m³."
            )
        elif r_val <= -0.1:
            insights.append(
                f"Đường xu hướng OLS âm (<b>{slope:.4f}</b>): "
                f"<b>{x_col}</b> và <b>{y_col}</b> có xu hướng ngược chiều nhẹ — "
                f"kiểm tra lệch pha theo thời gian trong dữ liệu."
            )
        else:
            insights.append(
                f"Slope OLS gần bằng 0 (<b>{slope:.4f}</b>): "
                f"không có chiều tăng/giảm rõ ràng — "
                f"có thể tồn tại nhiều nhóm dữ liệu khác nhau ẩn trong scatter."
            )

    # 3. Insight theo màu (station hoặc hour)
    if color_mode == "Station_No":
        st_rs = []
        for st_no, g in sdf.groupby("Station_No"):
            if len(g) >= 12:
                r_st = g[[x_col, y_col]].corr().iloc[0, 1]
                if not pd.isna(r_st):
                    st_rs.append((st_no, r_st, len(g)))
        if st_rs:
            best  = max(st_rs, key=lambda x: abs(x[1]))
            worst = min(st_rs, key=lambda x: abs(x[1]))
            insights.append(
                f"Theo trạm: <b>Trạm {best[0]}</b> có quan hệ rõ nhất "
                f"(r = {_fmt_r(best[1])}, n = {best[2]}); "
                f"<b>Trạm {worst[0]}</b> có quan hệ mờ nhất (r = {_fmt_r(worst[1])}) — "
                f"gợi ý nguồn phát thải tại hai trạm này rất khác nhau."
            )
    else:
        hour_mean = sdf.groupby("Hour")[y_col].mean().dropna()
        if len(hour_mean) >= 3:
            h_max = int(hour_mean.idxmax())
            h_min = int(hour_mean.idxmin())
            v_max = hour_mean.max()
            v_min = hour_mean.min()
            insights.append(
                f"Theo giờ: <b>{y_col}</b> trung bình cao nhất lúc <b>{h_max:02d}h</b> "
                f"({v_max:.1f} μg/m³) và thấp nhất lúc <b>{h_min:02d}h</b> "
                f"({v_min:.1f} μg/m³) trong phạm vi lọc hiện tại."
            )

    # 4. Kết luận ngữ cảnh cho cặp cụ thể
    _, _, pair_txt = _pair_insight(x_col, y_col, r_val)
    insights.append(pair_txt)

    return insights[:4]


def _summary_conclusion(corr_ov, means, df, sel_hours_val):
    """Kết luận tổng hợp cuối trang — hoàn toàn reactive theo filter."""
    lines = []

    co_so2  = corr_ov.loc["CO",  "SO2"]
    co_no2  = corr_ov.loc["CO",  "NO2"]
    co_pm25 = corr_ov.loc["CO",  "PM2.5"]
    no2_pm  = corr_ov.loc["NO2", "PM2.5"]

    # 1. Nguồn chi phối
    if not pd.isna(co_so2) and co_so2 >= 0.5:
        lines.append(
            f"<b>Giao thông & đốt cháy nhiên liệu chi phối:</b> CO–SO₂ r = <b>{_fmt_r(co_so2)}</b> — "
            f"hai chất cùng nguồn tăng/giảm đồng pha trong bộ lọc hiện tại."
        )
    elif not pd.isna(co_so2):
        lines.append(
            f"<b>CO–SO₂ r = {_fmt_r(co_so2)}</b>: mức đồng biến thấp hơn thông thường, "
            f"gợi ý nguồn phát thải đa dạng hơn trong trạm/khung giờ đang chọn."
        )

    # 2. Đặc điểm NO2
    if not pd.isna(co_no2) and abs(co_no2) < 0.15:
        lines.append(
            f"<b>NO₂ hoạt động độc lập:</b> CO–NO₂ r = <b>{_fmt_r(co_no2)}</b> — "
            f"NO₂ chịu thêm nguồn quang hóa ban ngày, không phản ánh đơn thuần lưu lượng giao thông."
        )
    elif not pd.isna(co_no2) and co_no2 >= 0.3:
        h0, h1 = sel_hours_val
        lines.append(
            f"<b>CO–NO₂ r = {_fmt_r(co_no2)}</b> khá cao trong khung {h0:02d}h–{h1:02d}h: "
            f"phát thải sơ cấp đang nổi bật — quang hóa chưa có nhiều thời gian tích lũy."
        )

    # 3. PM2.5 đa nguồn
    max_r_with_pm = max(
        [(c, corr_ov.loc[c, "PM2.5"]) for c in ["CO","NO2","SO2"]
         if not pd.isna(corr_ov.loc[c, "PM2.5"])],
        key=lambda x: abs(x[1]), default=(None, float("nan"))
    )
    if max_r_with_pm[0] and not pd.isna(max_r_with_pm[1]):
        best_c, best_r = max_r_with_pm
        who_pm = WHO["PM2.5"]
        m_pm   = means["PM2.5"]
        ratio  = m_pm / who_pm if who_pm > 0 else 0
        who_note = (f"Mean PM2.5 hiện tại <b>{m_pm:.1f} μg/m³</b> = "
                    f"<b>{ratio:.1f}×</b> ngưỡng WHO 24h ({who_pm:.0f} μg/m³).")
        lines.append(
            f"<b>PM2.5 là bài toán đa nguồn:</b> chỉ số tương quan cao nhất với PM2.5 "
            f"là {best_c}–PM2.5 r = <b>{_fmt_r(best_r)}</b> — không có chỉ số đơn lẻ nào đủ "
            f"để dự báo PM2.5. {who_note}"
        )

    # 4. Gợi ý hành động
    lines.append(
        "<b>Gợi ý:</b> Thử thu hẹn bộ lọc giờ cao điểm (06h–09h hoặc 17h–19h) "
        "để quan sát tương quan CO–SO₂ và CO–NO₂ tăng rõ hơn do phát thải sơ cấp chiếm ưu thế."
    )

    return lines


def main():
    inject_global_css()

    render_page_header(
        "Tương quan nội bộ giữa các chất ô nhiễm",
        "Phân tích mối tương quan và phân phối dữ liệu giữa các chất ô nhiễm chính tại TP.HCM"
    )

    # ── CSS bổ sung riêng của P05 ──────────────────────────────────────────────
    st.markdown(f"""
    <style>
    .rtable {{
        width:100%; border-collapse:collapse;
        border:1px solid {BORDER}; border-radius:8px;
        overflow:hidden; font-size:12px;
    }}
    .rtable thead tr {{ background:{CANVAS_BG}; }}
    .rtable th {{
        padding:6px 10px; text-align:left; font-size:9.5px;
        font-weight:700; color:{TEXT_SECONDARY}; letter-spacing:.6px; text-transform:uppercase;
    }}
    .rtable td {{ padding:6px 10px; border-top:1px solid {GRIDLINE}; }}
    hr.div {{ border:none; border-top:1px solid {BORDER}; margin:18px 0; }}

    /* Caption dưới pair-scatter */
    .pair-caption {{
        text-align:center; font-size:11.5px; color:{TEXT_SECONDARY};
        margin-top:-8px; margin-bottom:6px; line-height:1.5;
        padding: 0 4px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    def _g4_extra():
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Scatter tùy chỉnh**")
        sx = st.sidebar.selectbox("Trục X", COLS, index=0, key="g4_sx")
        sy = st.sidebar.selectbox("Trục Y", COLS, index=2, key="g4_sy")
        cb = st.sidebar.radio("Màu theo", ["Station_No", "Hour"], horizontal=True, key="g4_cb")
        h_val = st.sidebar.slider("Khung giờ", 0, 23, (0, 23), key="g4_hours")
        st.sidebar.markdown(
            f"<div style='font-size:10.5px;color:{C['sub']};line-height:1.7;margin-top:8px;'>"
            "Flag=2: loại trước khi tính r · Outlier: giữ lại</div>",
            unsafe_allow_html=True,
        )
        return {"scatter_x": sx, "scatter_y": sy, "color_by": cb, "hours": h_val}

    paths = [
        "Air_Quality_HCMC_Cleaned.csv",
        "data/cleaned/Air_Quality_HCMC_Cleaned.csv",
        "../data/cleaned/Air_Quality_HCMC_Cleaned.csv",
    ]
    path = next((p for p in paths if os.path.exists(p)), None)
    if path:
        df_raw = load_data(path)
    else:
        st.warning("⚠️ Không tìm thấy file dữ liệu hệ thống (Air_Quality_HCMC_Cleaned.csv).")
        st.stop()

    sb = render_standard_sidebar(
        df_raw,
        datetime_col="Date",
        station_col="Station_No",
        sidebar_key_prefix="g4",
        extra_widgets_fn=_g4_extra,
    )
    sel_stations  = sb["stations"]
    sel_dates     = (sb["start_date"], sb["end_date"])
    scatter_x     = sb.get("scatter_x", "CO")
    scatter_y     = sb.get("scatter_y", "SO2")
    color_by      = sb.get("color_by", "Station_No")
    sel_hours_val = sb.get("hours", (0, 23))

    df = df_raw[
        df_raw["Station_No"].isin(sel_stations) &
        (df_raw["Date"] >= pd.Timestamp(sel_dates[0])) &
        (df_raw["Date"] <= pd.Timestamp(sel_dates[1])) &
        df_raw["Hour"].between(sel_hours_val[0], sel_hours_val[1])
    ].copy()

    if df.empty:
        st.warning("⚠️ Không có dữ liệu sau bộ lọc. Vui lòng mở rộng phạm vi ngày/giờ hoặc chọn thêm trạm.")
        st.stop()

    # ── Precompute ─────────────────────────────────────────────────────────────
    corr_ov      = df[COLS].corr().round(3)
    means        = {c: df[c].mean() for c in COLS}
    stations_sel = sorted(df["Station_No"].unique())
    st_corr      = {st: df[df["Station_No"]==st][COLS].corr().round(3) for st in stations_sel}
    cmap_st      = {str(s): px.colors.qualitative.Set2[i % 8]
                    for i, s in enumerate(sorted(df["Station_No"].unique()))}


    # ══════════════════════════════════════════════════════════════════════════
    # KPI ROW — mean + WHO ratio
    # ══════════════════════════════════════════════════════════════════════════
    c1, c2, c3, c4 = st.columns(4)
    for col_ui, metric, fmt in zip([c1, c2, c3, c4], COLS, [".0f", ".1f", ".1f", ".1f"]):
        val    = means[metric]
        who_v  = WHO.get(metric)
        if who_v:
            ratio   = val / who_v
            delta_s = f"{ratio:.1f}× WHO 24h"
            d_color = "inverse" if ratio > 1 else "off"
        else:
            delta_s = "Toàn kỳ"
            d_color = "off"
        with col_ui:
            st.metric(
                label=f"Trung bình {metric}",
                value=f"{val:{fmt}} μg/m³",
                delta=delta_s,
                delta_color=d_color,
            )

    render_divider()


    # ══════════════════════════════════════════════════════════════════════════
    # ROW 1 — Heatmap (trái) | Bảng r (phải) + Insight tổng hợp 6 cặp
    # ══════════════════════════════════════════════════════════════════════════
    r1_left, r1_right = st.columns([1.1, 1], gap="large")

    with r1_left:
        render_section_header(
            "Correlation Heatmap",
            "Pearson r · giá trị gốc (flag ≠ 2) · toàn bộ trạm đã chọn"
        )
        z = corr_ov.values
        fig_hm = go.Figure(go.Heatmap(
            z=z, x=COLS, y=COLS,
            text=[[f"{v:.2f}" for v in row] for row in z],
            texttemplate="%{text}",
            textfont={"size":15,"family":"Segoe UI, sans-serif","color":C["text"]},
            colorscale=[[0,"#B23A2F"],[.3,"#F2D4D0"],[.5,"#F9FBFC"],[.7,"#C8DFF0"],[1,"#2B7BBB"]],
            zmid=0, zmin=-1, zmax=1, showscale=True,
            colorbar=dict(
                thickness=10, len=.85,
                title=dict(text="r", font=dict(size=10, color=C["sub"])),
                tickfont=dict(size=9, color=C["sub"]),
                tickvals=[-1, -.5, 0, .5, 1],
            ),
            xgap=4, ygap=4,
        ))
        fig_hm.update_layout(
            **bl(340),
            xaxis=dict(showgrid=False, tickfont=dict(size=12, family="Segoe UI, sans-serif")),
            yaxis=dict(showgrid=False, tickfont=dict(size=12, family="Segoe UI, sans-serif"),
                       autorange="reversed"),
        )
        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar":False})

    with r1_right:
        render_section_header(
            "Hệ số Pearson r – 6 cặp biến",
            "Mức độ tương quan tuyến tính · toàn bộ trạm · giá trị gốc (flag ≠ 2)"
        )
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

    # ── INSIGHT ĐỘNG — đủ 6 cặp ──────────────────────────────────────────
    focus_pairs = [("CO","SO2"), ("CO","NO2"), ("CO","PM2.5"),
                   ("NO2","PM2.5"), ("NO2","SO2"), ("SO2","PM2.5")]
    insight_lines = []
    for a, b in focus_pairs:
        rv = corr_ov.loc[a, b]
        lbl, _, txt = _pair_insight(a, b, rv)
        insight_lines.append(f"<b>{a} – {b}</b> [{lbl}]: {txt}")

    render_insight_box(
        insight_lines,
        title="Phân tích tương quan – 6 cặp biến",
        icon_name="analysis"
    )

    st.markdown("<hr class='div'>", unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════════════════
    # ROW 2 — 3 Pair-scatter nhỏ + caption reactive dưới mỗi chart
    # ══════════════════════════════════════════════════════════════════════════
    render_section_header(
        "Pair-scatter: CO là trục trung tâm",
        "CO so với NO₂ · SO₂ · PM2.5 – 400 mẫu · trendline OLS · màu theo trạm"
    )

    pairs3  = [("CO","NO2"), ("CO","SO2"), ("CO","PM2.5")]
    labels3 = ["CO vs NO₂",  "CO vs SO₂",  "CO vs PM2.5"]

    for col_ui, (xa, ya), lbl in zip(st.columns(3, gap="small"), pairs3, labels3):
        sub = df[[xa, ya, "Station_No"]].dropna()
        sub = sub.sample(min(400, len(sub)), random_state=pairs3.index((xa,ya))*7)
        rp  = sub[[xa, ya]].corr().iloc[0, 1]

        fig_p = px.scatter(
            sub, x=xa, y=ya,
            color=sub["Station_No"].astype(str), color_discrete_map=cmap_st,
            opacity=.5, trendline="ols", trendline_scope="overall",
            trendline_color_override=C["text"], labels={"color":"Trạm"}
        )
        fig_p.update_traces(selector=dict(mode="markers"), marker=dict(size=5))
        fig_p.update_layout(
            height=360, margin=dict(l=52, r=16, t=16, b=150),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Segoe UI, sans-serif", color=C["text"]),
            xaxis=dict(title=dict(text=xa, font=dict(size=11)),
                       gridcolor=C["grid"], zeroline=False, tickfont=dict(size=10)),
            yaxis=dict(title=dict(text=ya, font=dict(size=11)),
                       gridcolor=C["grid"], zeroline=False, tickfont=dict(size=10)),
            legend=dict(
                title=dict(text="Trạm", font=dict(size=10)),
                font=dict(size=10),
                orientation="h", yanchor="bottom", y=-0.58,
                xanchor="center", x=0.5,
                bgcolor="rgba(255,255,255,.88)",
                bordercolor=C["border"], borderwidth=1,
            ),
        )
        with col_ui:
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})
            # Tiêu đề + r value
            st.markdown(
                f"<p style='text-align:center;font-size:13px;font-weight:700;"
                f"color:{C['text']};margin-top:-42px;'>"
                f"{lbl} &nbsp;·&nbsp; r = {rp:.3f}</p>",
                unsafe_allow_html=True,
            )
            # ── Caption reactive theo r tính được ────────────────────────────
            caption = _pair_caption(xa, ya, rp)
            st.markdown(
                f"<p class='pair-caption'>{caption}</p>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='div'>", unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════════════════
    # ROW 3 — Scatter tùy chỉnh (expandable)
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander(
        f":material/search:  Scatter tùy chỉnh – {scatter_x} vs {scatter_y}  (chọn biến trong sidebar)",
        expanded=False
    ):
        if scatter_x == scatter_y:
            st.warning("⚠️ Vui lòng chọn hai biến khác nhau.")
        else:
            sdf = df[[scatter_x, scatter_y, "Station_No", "Hour"]].dropna()
            sdf = sdf.sample(min(1000, len(sdf)), random_state=42)
            rv  = sdf[[scatter_x, scatter_y]].corr().iloc[0, 1]

            sc_left, sc_right = st.columns([2.2, 1], gap="large")

            with sc_left:
                _axis_x = dict(
                    title=dict(text=f"{scatter_x} ({UNITS[scatter_x]})", font=dict(size=12)),
                    gridcolor=C["grid"], zeroline=False,
                    showline=True, linecolor=C["border"], tickfont=dict(size=10)
                )
                _axis_y = dict(
                    title=dict(text=f"{scatter_y} ({UNITS[scatter_y]})", font=dict(size=12)),
                    gridcolor=C["grid"], zeroline=False,
                    showline=True, linecolor=C["border"], tickfont=dict(size=10)
                )

                if color_by == "Station_No":
                    fig_sc = px.scatter(
                        sdf, x=scatter_x, y=scatter_y,
                        color=sdf["Station_No"].astype(str),
                        color_discrete_map=cmap_st, opacity=.5,
                        trendline="ols", trendline_scope="overall",
                        trendline_color_override=C["text"], labels={"color":"Trạm"}
                    )
                    fig_sc.update_traces(selector=dict(mode="markers"), marker=dict(size=4))
                    fig_sc.update_layout(
                        **bl(340), xaxis=_axis_x, yaxis=_axis_y, hovermode="closest",
                        legend=dict(
                            title=dict(text="Trạm", font=dict(size=11)),
                            bgcolor="rgba(255,255,255,.85)",
                            bordercolor=C["border"], borderwidth=1, font=dict(size=11),
                            x=1.01, y=1, xanchor="left", yanchor="top",
                        ),
                    )
                else:
                    fig_sc = px.scatter(
                        sdf, x=scatter_x, y=scatter_y, color="Hour",
                        color_continuous_scale=["#2B7BBB","#FFB703","#B23A2F"],
                        opacity=.5, trendline="ols", trendline_scope="overall",
                        trendline_color_override=C["text"]
                    )
                    fig_sc.update_traces(selector=dict(mode="markers"), marker=dict(size=4))
                    fig_sc.update_layout(
                        **bl(340), xaxis=_axis_x, yaxis=_axis_y,
                        hovermode="closest", showlegend=False,
                        coloraxis_colorbar=dict(
                            title=dict(text="Giờ", font=dict(size=11)),
                            thickness=14, len=.75, tickfont=dict(size=10),
                            tickvals=[0, 6, 12, 18, 23],
                            ticktext=["0h","6h","12h","18h","23h"],
                            x=1.01,
                        ),
                    )

                fig_sc.add_annotation(
                    x=.97, y=.05, xref="paper", yref="paper",
                    text=f"<b>r = {rv:.3f}</b>", showarrow=False,
                    font=dict(size=13, color=C["text"], family="Segoe UI, sans-serif"),
                    bgcolor="rgba(255,255,255,.9)",
                    bordercolor=C["border"], borderwidth=1, borderpad=7
                )
                st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})

            with sc_right:
                st.markdown(f"**r của {scatter_x}–{scatter_y} theo trạm**")
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

            # ── Insight động cho scatter tùy chỉnh ───────────────────────────
            sc_ins = _scatter_dynamic_insights(sdf, scatter_x, scatter_y, color_by, rv)
            render_insight_box(
                sc_ins,
                title=f"Insight Scatter: {scatter_x} vs {scatter_y}",
                icon_name="analysis"
            )

    st.markdown("---")
    st.markdown(f"### {get_icon_html('insight')} Kết luận", unsafe_allow_html=True)

    conclusion_lines = _summary_conclusion(corr_ov, means, df, sel_hours_val)
    bullets = "".join(f"<li style='margin-bottom:8px;'>{l}</li>" for l in conclusion_lines)
    content_html = f"""
        <h4 style="color:#1F8A70;">
            {get_icon_html("analysis")} Tương quan đa chiều — Giao thông là nguồn phát thải chính
        </h4>
        <ul style="margin-top:10px;">{bullets}</ul>
    """
    render_conclusion_box(content_html, accent_color="#1F8A70")


if __name__ == '__main__':
    main()