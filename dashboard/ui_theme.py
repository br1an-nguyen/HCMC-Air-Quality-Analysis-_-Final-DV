"""
ui_theme.py — Shared design tokens & UI helpers cho HCMC Air Quality Dashboard.
Import vào mỗi goal file để đảm bảo giao diện nhất quán.
"""
from __future__ import annotations
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────

# Màu nền
CANVAS_BG   = "#F4F8FB"
CARD_BG     = "#FFFFFF"

# Màu chữ
TEXT_PRIMARY   = "#16324F"
TEXT_SECONDARY = "#4F6B7A"

# Màu đường lưới & viền
GRIDLINE = "#E5EEF3"
BORDER   = "#D9E4EC"

# Màu accent cho từng chất ô nhiễm (nhất quán toàn app)
POLLUTANT_COLORS = {
    "PM2.5":       "#B23A2F",
    "TSP":         "#6F1D1B",
    "O3":          "#1F8A70",
    "CO":          "#4E5D8A",
    "NO2":         "#D98E04",
    "SO2":         "#2B7BBB",
    "Temperature": "#D65A31",
    "Humidity":    "#2F80ED",
}

# Màu trạng thái
COLOR_SAFE      = "#2A9D8F"
COLOR_HAZARDOUS = "#E63946"
COLOR_HIGHLIGHT = "#FFB703"
COLOR_POSITIVE  = "#1F8A70"
COLOR_NEGATIVE  = "#B23A2F"

# Font chung
FONT_FAMILY = "Segoe UI, Arial, sans-serif"

# WHO threshold
WHO_PM25 = 15.0


# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY BASE LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

def base_layout(**overrides) -> dict:
    """Layout mặc định cho mọi Plotly figure có trục X/Y."""
    defaults = dict(
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY, size=16),
        xaxis=dict(gridcolor=GRIDLINE, showgrid=True, zeroline=False),
        yaxis=dict(gridcolor=GRIDLINE, showgrid=True, zeroline=False),
        margin=dict(l=55, r=30, t=65, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor=CARD_BG, font_size=16),
    )
    defaults.update(overrides)
    return defaults


def base_layout_no_axes(**overrides) -> dict:
    """Layout mặc định không có xaxis/yaxis (cho Pie/Donut/Radar)."""
    d = {k: v for k, v in base_layout().items() if k not in ("xaxis", "yaxis")}
    d.update(overrides)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# CSS INJECT
# ─────────────────────────────────────────────────────────────────────────────

def inject_global_css() -> None:
    """
    Inject CSS toàn cục vào trang Streamlit.
    Gọi một lần ở đầu hàm main() của mỗi goal.
    """
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

    /* ── Nền trang ── */
    .stApp {{
        background-color: {CANVAS_BG};
        font-family: {FONT_FAMILY};
        font-size: 18px;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background-color: {CARD_BG};
        border-right: 1px solid {GRIDLINE};
        border-left: none;
    }}
    /* ── Sidebar controls: đen thay cho đỏ ── */
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stDownloadButton > button {{
        background-color: {TEXT_PRIMARY} !important;
        color: #FFFFFF !important;
        border: 1px solid {TEXT_PRIMARY} !important;
        border-radius: 10px !important;
    }}
    section[data-testid="stSidebar"] button[kind="primary"]:hover,
    section[data-testid="stSidebar"] .stButton > button:hover,
    section[data-testid="stSidebar"] .stDownloadButton > button:hover {{
        background-color: #0F172A !important;
        border-color: #0F172A !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:focus,
    section[data-testid="stSidebar"] .stDownloadButton > button:focus {{
        box-shadow: 0 0 0 3px rgba(22,50,79,0.18) !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        border-color: {BORDER} !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {{
        border-color: {TEXT_PRIMARY} !important;
        box-shadow: 0 0 0 1px {TEXT_PRIMARY} inset !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="slider"] [role="slider"] {{
        background-color: {TEXT_PRIMARY} !important;
        border-color: {TEXT_PRIMARY} !important;
    }}

    /* ── Multiselect: tag được chọn màu đen/xám thay vì đỏ ── */
    span[data-baseweb="tag"] {{
        background-color: {TEXT_PRIMARY} !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        font-size: 16px !important;
    }}
    span[data-baseweb="tag"] span {{
        color: #FFFFFF !important;
    }}
    /* Nút xóa (×) trong tag */
    span[data-baseweb="tag"] button {{
        color: rgba(255,255,255,0.7) !important;
    }}
    span[data-baseweb="tag"] button:hover {{
        color: #FFFFFF !important;
        background: rgba(255,255,255,0.15) !important;
    }}

    /* ── Headers ── */
    h3[data-testid="stHeader"] {{
        font-size: 34px !important;
        font-weight: 700 !important;
        color: {TEXT_PRIMARY} !important;
        margin-bottom: 0.5rem !important;
    }}
    .section-header-main {{
        font-size: 34px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 0.5rem;
        margin-top: 1.5rem;
    }}
    .section-header-insight {{
        font-size: 20px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 0.5rem;
        margin-top: 1rem;
    }}

    /* ── KPI metric cards ── */
    div[data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {GRIDLINE};
        border-radius: 12px;
        padding: 20px 20px 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        min-height: 145px;
        display: flex;
        flex-direction: column;
    }}
    div[data-testid="stMetric"] label {{
        color: {TEXT_SECONDARY};
        font-size: 17px;
        font-weight: 500;
        margin-bottom: 0px !important;
        min-height: 24px;
        display: flex;
        align-items: flex-start;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        font-size: 30px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        min-height: 36px;
        display: flex;
        align-items: center;
        margin-top: 0px !important;
    }}
    /* Định nghĩa màu sắc cho phần delta theo yêu cầu */
    /* normal: Green, inverse: Red, off: Gray */
    div[data-testid="stMetricDelta"][data-delta-color="normal"] > div {{
        color: #22C55E !important; /* Xanh lá */
    }}
    div[data-testid="stMetricDelta"][data-delta-color="inverse"] > div {{
        color: #EF4444 !important; /* Đỏ */
    }}
    div[data-testid="stMetricDelta"][data-delta-color="off"] > div {{
        color: #64748B !important; /* Xám */
    }}

    /* Ẩn mũi tên và căn chỉnh lại văn bản trong phần delta */
    div[data-testid="stMetricDelta"] {{
        min-height: 20px;
        margin-top: 10px !important;
        display: flex !important;
        align-items: center !important;
    }}
    div[data-testid="stMetricDelta"] svg {{
        display: none !important;
    }}
    
    /* Trick: Nếu delta bắt đầu bằng dấu trừ '-', chúng ta ẩn nó đi để hiện số đỏ không dấu */
    /* Lưu ý: Đây là giải pháp CSS để đáp ứng yêu cầu 'số không cộng thì màu đỏ' */
    div[data-testid="stMetricDelta"][data-delta-color="inverse"] > div::first-letter {{
        font-size: 0 !important;
        color: transparent !important;
    }}
    
    div[data-testid="stMetricDelta"] > div {{
        margin-left: 0 !important;
    }}

    /* ── Section divider ── */
    .section-divider {{
        border: none;
        border-top: 1px solid {GRIDLINE};
        margin: 24px 0 18px 0;
    }}

    /* ── Insight box ── */
    .insight-box {{
        background: #F0F7FF;
        border-left: 4px solid #1E88E5;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 8px;
        margin-bottom: 8px;
    }}
    .insight-box .insight-title {{
        color: #1E88E5;
        font-weight: 700;
        margin-bottom: 6px;
        font-size: 17px;
    }}
    .insight-box ul {{
        margin: 0;
        padding-left: 18px;
        color: {TEXT_PRIMARY};
        font-size: 17.5px;
        line-height: 1.7;
    }}

    /* ── Conclusion box ── */
    .conclusion-box {{
        background: linear-gradient(135deg, #EEF4F8 0%, #F4F8FB 100%);
        border-left: 5px solid {POLLUTANT_COLORS["CO"]};
        border-radius: 8px;
        padding: 24px 28px;
        color: {TEXT_PRIMARY};
        line-height: 1.8;
        margin-top: 1rem;
        margin-bottom: 2rem;
    }}
    .conclusion-box h3, .conclusion-box h4 {{
        margin-top: 0;
        color: #0F172A;
    }}
    .conclusion-box ul, .conclusion-box ol {{
        margin-bottom: 0;
    }}

    /* ── Ẩn menu mặc định (giữ header để nút sidebar không bị mất) ── */
    #MainMenu, footer {{ visibility: hidden; }}
    header {{ visibility: visible; }}
    [data-testid="stToolbar"] {{ visibility: visible; }}
    [data-testid="stSidebarCollapsedControl"] {{ visibility: visible; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UI COMPONENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def render_page_header(title: str, subtitle: str = "") -> None:
    """
    Render tiêu đề trang nhất quán trong một khối HTML duy nhất
    để tránh bị nhảy (jump) giao diện khi chuyển trang.
    """
    sub_html = f"<p style='margin:0; color:{TEXT_SECONDARY}; font-size:18px;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style='margin-bottom:25px;'>
            <h1 style='color:{TEXT_PRIMARY}; font-family:{FONT_FAMILY};
                       margin:0 0 4px 0; font-size:40px; font-weight:700;
                       line-height:1.2;'>
                {title}
            </h1>
            {sub_html}
            <hr style='border:none; border-top:1px solid {GRIDLINE}; margin:16px 0 0 0;'>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_header(label: str = "Bộ lọc dữ liệu") -> None:
    """Render header sidebar nhất quán."""
    st.sidebar.markdown(
        f"<div style='background:{TEXT_PRIMARY};border-radius:8px;"
        f"padding:10px 14px;margin-bottom:14px;'>"
        f"<span style='color:white;font-size:17px;font-weight:700;'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = "") -> None:
    """Render tiêu đề section với kích thước linh hoạt (Insight nhỏ hơn, các tiêu đề khác lớn hơn)."""
    # Tự động phát hiện nếu tiêu đề chứa chữ "Insight"
    is_insight = "Insight" in title or "Phân tích" in title or "Kết luận" in title
    cls = "section-header-insight" if is_insight else "section-header-main"
    
    st.markdown(f'<div class="{cls}">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


def render_divider() -> None:
    """Render divider nhất quán."""
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ── Icons (SVG) ─────────────────────────────────────────────────────────────
ICONS = {
    "insight": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"></path><path d="M9 18h6"></path><path d="M10 22h4"></path></svg>""",
    "analysis": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>""",
    "warning": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>""",
    "trend": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>""",
    "location": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>""",
    "weather": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path></svg>""",
    "activity": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>""",
    "discovery": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>""",
    "search": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>""",
}


def get_icon_html(name: str) -> str:
    """Trả về HTML chứa SVG icon chuyên nghiệp."""
    svg = ICONS.get(name, ICONS["insight"])
    return f"<span style='display:inline-flex; align-items:center; gap:8px; vertical-align:middle;'>{svg}</span>"


def render_insight_box(lines: list[str], title: str = "Insight", icon_name: str = "insight") -> None:
    """
    Render insight box nhất quán thay cho st.info() và custom HTML riêng lẻ.
    Sử dụng bộ icon SVG chuyên nghiệp.
    """
    icon_svg = ICONS.get(icon_name, ICONS["insight"])
    bullets = "".join(f"<li style='margin:4px 0'>{l}</li>" for l in lines)
    
    st.markdown(
        f"""
        <div class="insight-box">
            <div class="insight-title">
                {get_icon_html(icon_name)}
                <span>{title}</span>
            </div>
            <ul>{bullets}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_conclusion_box(content_html: str, accent_color: str = "#4E5D8A") -> None:
    """
    Render conclusion box nhất quán ở cuối trang.
    content_html: nội dung HTML bên trong box (h3/h4 + ul/ol).
    accent_color: màu border-left (mặc định màu CO).
    """
    st.markdown(
        f"<div class='conclusion-box' style='border-left-color:{accent_color};'>"
        f"{content_html}</div>",
        unsafe_allow_html=True,
    )


def render_standard_sidebar(
    df,
    datetime_col: str = "Date",
    station_col: str = "Station_No",
    station_format_func=None,
    extra_widgets_fn=None,
    sidebar_key_prefix: str = "sb",
) -> dict:
    """
        Render bộ lọc chuẩn cho tất cả các trang:
            - Header sidebar
            - Multiselect trạm
            - Date range picker
            - Divider + caption dữ liệu

    Parameters
    ----------
    df               : DataFrame đã load
    datetime_col     : tên cột ngày (Date hoặc datetime)
    station_col      : tên cột trạm
    extra_widgets_fn : callable(sidebar) để thêm widget riêng của từng goal
    sidebar_key_prefix: prefix tránh key conflict giữa các trang
    station_format_func: optional callable để định dạng nhãn trạm

    Returns
    -------
    dict với keys: stations, start_date, end_date, + bất kỳ key nào extra_widgets_fn trả về
    """
    import pandas as pd

    result = {}

    with st.sidebar:
        # ── Header ──
        st.markdown(
            f"<div style='background:{TEXT_PRIMARY};border-radius:8px;"
            f"padding:10px 14px;margin-bottom:16px;'>"
            f"<span style='color:white;font-size:17px;font-weight:700;'>"
            f"Bộ lọc dữ liệu</span></div>",
            unsafe_allow_html=True,
        )

        # ── Trạm quan trắc ──
        all_stations = sorted(df[station_col].unique().tolist())
        format_station = station_format_func if station_format_func is not None else (lambda x: f"Trạm {x}")
        sel_stations = st.multiselect(
            "Trạm quan trắc",
            options=all_stations,
            default=all_stations,
            format_func=format_station,
            key=f"{sidebar_key_prefix}_stations",
        )
        result["stations"] = sel_stations

        # ── Khoảng thời gian ──
        if pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
            min_d = df[datetime_col].dt.date.min()
            max_d = df[datetime_col].dt.date.max()
        else:
            min_d = pd.to_datetime(df[datetime_col]).dt.date.min()
            max_d = pd.to_datetime(df[datetime_col]).dt.date.max()

        date_range = st.date_input(
            "Khoảng thời gian",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
            key=f"{sidebar_key_prefix}_dates",
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            result["start_date"], result["end_date"] = date_range
        else:
            result["start_date"] = result["end_date"] = min_d

        # ── Widget bổ sung riêng từng goal ──
        if extra_widgets_fn is not None:
            extra = extra_widgets_fn()
            if isinstance(extra, dict):
                result.update(extra)

        # ── Footer ──
        st.markdown("---")
        st.caption(
            f"Dữ liệu: HealthyAir HCMC  \n"
            f"02/2021 – 06/2022 · 6 trạm quan trắc  \n"
            f"Flag = 2 → loại bỏ trước khi tính toán"
        )

    return result
    return result
