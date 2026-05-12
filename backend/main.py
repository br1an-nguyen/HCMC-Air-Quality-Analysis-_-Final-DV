import os
import sys
import subprocess
import json
import textwrap
import re
import uuid
import base64

import pandas as pd
import google.generativeai as genai
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    from backend import database
except ImportError:
    import database

# ─────────────────────────────────────────────────────────────
# App & environment setup
# ─────────────────────────────────────────────────────────────

load_dotenv()
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="HCMC Air Quality AI API", version="2.0.0")

# Cấu hình bảo mật CORS cho Chatbot Widget (Phase 1)
# Cho phép Streamlit (port 8080, 8501) gọi API an toàn. Cấu hình FRONTEND_URL trên production.
origins = [
    os.environ.get("FRONTEND_URL", "http://localhost:8080"),
    "http://localhost:8501", 
    "http://localhost:3000",
    "http://127.0.0.1:8080"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated chart HTML files as static assets.
# Frontend fetches /charts/output_<chat_id>.html to display Plotly charts.
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
app.mount("/charts", StaticFiles(directory=TEMP_DIR), name="charts")


# ─────────────────────────────────────────────────────────────
# Gemini client
# ─────────────────────────────────────────────────────────────

# Model name — đổi trong file .env (GEMINI_MODEL=...), không hardcode ở đây.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

api_key = os.environ.get("GOOGLE_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# Model cho chat thông thường (JSON output)
gemini_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config={
        "response_mime_type": "application/json",
    },
) if api_key else None

# Model cho hỏi về chart (multimodal, text output)
# gemini-2.5-flash hỗ trợ vision nên dùng cùng model, chỉ khác generation_config
gemini_vision_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
) if api_key else None


# ─────────────────────────────────────────────────────────────
# Startup: DB init + auto-context
# ─────────────────────────────────────────────────────────────

AUTO_CONTEXT: str = ""

@app.on_event("startup")
def startup_event() -> None:
    # Initialise / migrate DB tables
    try:
        database.init_db()
    except Exception as exc:
        print(f"[WARN] DB init failed: {exc}")

    # Build a lightweight schema summary that is injected into every prompt.
    # This makes context attachment automatic — the frontend does not need to
    # send anything in the `context` field for basic schema awareness.
    global AUTO_CONTEXT
    csv_path = os.path.join(project_root, "data", "cleaned", "Air_Quality_HCMC_Cleaned.csv")
    try:
        df = pd.read_csv(csv_path, nrows=5)          # read only 5 rows for speed
        full_df = pd.read_csv(csv_path, usecols=["Date", "Station_No"])
        AUTO_CONTEXT = (
            f"Columns     : {list(df.columns)}\n"
            f"Total rows  : {len(full_df):,}\n"
            f"Date range  : {full_df['Date'].min()} → {full_df['Date'].max()}\n"
            f"Stations    : {sorted(full_df['Station_No'].unique().tolist())}\n"
        )
        print("[INFO] AUTO_CONTEXT built successfully.")
    except Exception as exc:
        print(f"[WARN] Could not build AUTO_CONTEXT: {exc}")


# ─────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Bạn là một Chuyên gia Phân tích Dữ liệu Chất lượng Không khí tại TP.HCM, được xây dựng riêng
để hỗ trợ phân tích dự án gồm 5 mục tiêu nghiên cứu (Goal 1–5). Bạn có hiểu biết sâu về dữ liệu,
ngưỡng tiêu chuẩn, logic xử lý và các insight đã được xác lập của từng mục tiêu.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN I — DỮ LIỆU & CẤU TRÚC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILE DỮ LIỆU CHÍNH: 'data/cleaned/Air_Quality_HCMC_Cleaned.csv'
Phạm vi thời gian  : Tháng 2/2021 – Tháng 6/2022 (17 tháng, tần suất theo giờ)
Số trạm quan trắc  : 6 trạm

SCHEMA CÁC CỘT:
| Cột             | Mô tả                                    | Đơn vị  |
|-----------------|------------------------------------------|---------|
| Date            | Ngày đo (YYYY-MM-DD)                     | —       |
| Hour            | Giờ đo                                   | 0–23    |
| Station_No      | Mã trạm quan trắc                        | 1–6     |
| PM2.5           | Bụi mịn                                  | µg/m³   |
| TSP             | Tổng bụi lơ lửng                         | µg/m³   |
| SO2             | Lưu huỳnh điôxit                         | µg/m³   |
| O3              | Ôzôn                                     | µg/m³   |
| NO2             | Nitơ điôxit                              | µg/m³   |
| CO              | Carbon monoxit                           | µg/m³   |
| Temperature     | Nhiệt độ                                 | °C      |
| Humidity        | Độ ẩm tương đối                          | %       |
| *_flag          | Cờ chất lượng cho mỗi chỉ số trên        | 0/1/2   |

METADATA 6 TRẠM QUAN TRẮC:
| Station_No | Location        | Region                | Lat      | Lon       |
|------------|-----------------|-----------------------|----------|-----------|
| 1          | VNU Ho Chi Minh | Urban background      | 10.8699  | 106.7960  |
| 2          | Binh Tan        | Traffic               | 10.7410  | 106.6171  |
| 3          | Tan Binh IP     | Industry              | 10.8162  | 106.6204  |
| 4          | Thanh Da        | Residential           | 10.8158  | 106.7174  |
| 5          | District 3      | Traffic               | 10.7764  | 106.6878  |
| 6          | District 10     | Traffic + Residential | 10.7805  | 106.6595  |

LƯU Ý DỮ LIỆU BẤT THƯỜNG:
- Trạm 5 (District 3) thường xuyên ghi nhận NO2 và SO2 ở mức cực thấp hoặc bằng 0
  do hiện tượng sensor drift. Khi phân tích trạm này, hãy cảnh báo người dùng và
  ưu tiên dùng PM2.5, CO, O3 thay thế.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN II — NGƯỠNG TIÊU CHUẨN (BẮT BUỘC GHI NHỚ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHO 2021 (Khuyến nghị 24 giờ):
  PM2.5 : 15 µg/m³
  CO     : 4,000 µg/m³
  NO2    : 25 µg/m³
  SO2    : 40 µg/m³
  O3     : 100 µg/m³  (Trung bình trượt 8 giờ)
  TSP    : 150 µg/m³  (Proxy cho PM10)

QCVN 05:2023/BTNMT (Tiêu chuẩn 24 giờ Việt Nam):
  PM2.5 : 50 µg/m³
  CO     : 10,000 µg/m³
  NO2    : 100 µg/m³
  SO2    : 125 µg/m³
  O3     : 200 µg/m³  (Trung bình 1 giờ)
  TSP    : 200 µg/m³

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN III — LOGIC XỬ LÝ DỮ LIỆU BẮT BUỘC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LỌC FLAG: df_clean = df[df['<pollutant>_flag'] <= 1]
2. O3 ROLLING: df['O3_8h'] = df.groupby('Station_No')['O3'].transform(
       lambda x: x.rolling(8, min_periods=6).mean())
3. TRUNG BÌNH 24H: group by ['Date', 'Station_No'] rồi .mean()
4. MÙA KHÔ: tháng 11,12,1,2,3,4 | MÙA MƯA: tháng 5,6,7,8,9,10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN IV — 5 MỤC TIÊU DỰ ÁN & INSIGHT ĐÃ XÁC LẬP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GOAL 1 — XU HƯỚNG THEO THỜI GIAN
[G1-I1] PM2.5 đỉnh 7–9h sáng và 17–19h chiều.
[G1-I2] PM2.5 cao hơn mùa khô do thiếu washout mưa.
[G1-I3] CO và NO2 tương quan chặt với giờ cao điểm giao thông.

GOAL 2 — PHÂN BỐ KHÔNG GIAN
[G2-I1] Thanh Da Paradox: khu dân cư nhưng PM2.5 cao nhất.
[G2-I2] O3 đạt đỉnh 11h–14h, thấp nhất ban đêm.
[G2-I3] Tất cả 6 trạm vượt ngưỡng WHO PM2.5 (15 µg/m³) theo trung bình.
[G2-I4] Tháng 7–9/2021 giảm đồng loạt toàn trạm (COVID lockdown).

GOAL 3 — TƯƠNG QUAN KHÍ TƯỢNG
[G3-I1] Nhiệt độ và O3 tương quan dương mạnh.
[G3-I2] Độ ẩm và PM2.5 tương quan âm.
[G3-I3] Noon Peak Effect: 11h–14h nhiệt cao + O3 đỉnh.
[G3-I4] Night-time inversion: PM2.5 tích tụ ban đêm.

GOAL 4 — TƯƠNG QUAN GIỮA CÁC CHẤT
[G4-I1] CO–SO2 tương quan dương mạnh (nguồn đốt nhiên liệu chung).
[G4-I2] CO–PM2.5 tương quan dương vừa.
[G4-I3] PM2.5 đa nguồn, không tương quan mạnh với khí thải đơn lẻ.

GOAL 5 — RỦI RO SỨC KHỎE
[G5-I1] Tỷ lệ ngày nguy hiểm (PM2.5 > 15 µg/m³) chiếm phần lớn.
[G5-I2] Trạm dân cư và gần đường lớn có ngày nguy hiểm cao nhất.
[G5-I3] Giờ nguy hiểm: sáng sớm (nghịch nhiệt) và chiều tối (giao thông).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN V — LUẬT KỸ THUẬT BẮT BUỘC CHO CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ĐỌC DỮ LIỆU : Sử dụng đường dẫn tuyệt đối hoặc tương ứng với ROOT. 
                  Gợi ý code: 
                  import os
                  root = os.getcwd() # Hoặc logic phù hợp
                  path = 'data/cleaned/Air_Quality_HCMC_Cleaned.csv'
2. LỌC FLAG    : df[df['col_flag'] <= 1] — bắt buộc trước mọi tính toán
3. PLOTLY      : ưu tiên Plotly. KẾT THÚC BẰNG fig.write_html('backend/temp/output.html').
                 TUYỆT ĐỐI KHÔNG DÙNG fig.show() — code chạy trong server subprocess.
4. MATPLOTLIB  : plt.savefig('backend/temp/output.png') — KHÔNG dùng plt.show()
5. THƯ VIỆN   : pandas, numpy, plotly, matplotlib, seaborn, statsmodels, scikit-learn
6. COMMENT     : mỗi bước quan trọng phải có comment tiếng Việt ngắn gọn.
                 Ví dụ: # Lọc bỏ các hàng có flag = 2 (cảm biến lỗi)

ĐỊNH DẠNG ĐẦU RA — BẮT BUỘC JSON:
{"code": "<full self-contained python>", "explanation": "<mục tiêu, logic, insight>"}

QUY TẮC CODE:
- Tự chứa đầy đủ import + merge metadata + lọc flag.
- Không dùng biến toàn cục, không giả định data đã xử lý sẵn.
- Tên biến rõ ràng: df_pm25_daily, not df2.
- F-STRING QUOTES: LUÔN dùng dấu nháy kép cho f-string bên ngoài: f"text {{row['col']}}"
  TUYỆT ĐỐI KHÔNG dùng escaped quotes bên trong f-string: f'text {{row[\"col\"]}}' → SyntaxError.
  Nếu cần truy cập dict/DataFrame trong f-string, gán biến trước:
    val = row['Date']; print(f"Ngày: {{val}}")  ← ĐÚNG
    print(f'Ngày: {{row[\"Date\"]}}')            ← SAI, gây SyntaxError

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHẦN VI — HÀNH VI TRẢ LỜI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Insight: chỉ trích dẫn G1-I1…G5-I3. Không suy diễn ngoài dữ liệu.
- Code: xác định Goal → áp dụng đúng logic → dùng đúng ngưỡng.
- Không rõ: hỏi lại Goal (1–5) và gợi ý KPI liên quan.
- Ngôn ngữ: tiếng Việt, luôn kèm đơn vị và nguồn ngưỡng.
"""


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _export_chart_png(html_path: str, png_path: str) -> str | None:
    """
    Đọc PNG đã được export bởi patch_code trong subprocess.
    Trả về base64 string, hoặc None nếu file không tồn tại.
    """
    try:
        if os.path.exists(png_path):
            with open(png_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None


def _fix_fstring_quotes(code: str) -> str:
    """
    Auto-fix lỗi escaped quotes trong f-string do AI gen ra.
    Ví dụ: f'text {row[\"col\"]}' → f"text {row['col']}"

    Cách tiếp cận: tìm f-string nháy đơn có chứa \" bên trong,
    đổi outer quotes thành nháy kép và bỏ escape.
    """
    if code is None:
        return ""
    # Pattern: f'...' hoặc f'...' có chứa \" bên trong
    # Thay f'<content với \">' → f"<content với '>"
    import re as _re

    def replace_fstring(m):
        inner = m.group(1)
        if '\\"' in inner:
            # Bỏ escape, đổi outer sang nháy kép
            inner_fixed = inner.replace('\\"', '"')
            # Nếu inner_fixed có nháy đơn, giữ nguyên (đã dùng nháy kép bên ngoài)
            return f'f"{inner_fixed}"'
        return m.group(0)  # không thay đổi nếu không có vấn đề

    # Match f'...' (non-greedy, không qua newline)
    code = _re.sub(r"f'((?:[^'\\]|\\.)*)'", replace_fstring, code)
    return code


def _strip_code_fences(code: str) -> str:
    """
    Remove markdown code fences. handle None input safely.
    """
    if code is None:
        return ""
    code = textwrap.dedent(code).strip()
    # Remove leading fence (```python, ```Python, ```py, ``` …)
    code = re.sub(r"^```[a-zA-Z]*\n?", "", code)
    # Remove trailing fence
    code = re.sub(r"\n?```$", "", code)
    return code.strip()


def _build_gemini_history(history: list[dict]) -> list[dict]:
    """
    Convert frontend history format  {"role": "user"|"assistant", "content": "…"}
    to Gemini SDK format              {"role": "user"|"model",     "parts": ["…"]}

    FIX 3: previously the history was flattened into a plain string, losing
    the multi-turn structure.  Gemini's start_chat() API requires this format.
    """
    converted = []
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "assistant":
            role = "model"                # Gemini uses "model" not "assistant"
        if role not in ("user", "model"):
            continue                      # skip unknown roles
        converted.append({"role": role, "parts": [content]})
    return converted


# ─────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str
    context: str = ""
    history: list[dict] = []

class ExecuteRequest(BaseModel):
    code: str
    chat_id: str

class AskChartRequest(BaseModel):
    """Hỏi AI về biểu đồ đã gen. image_b64 là PNG encode base64."""
    prompt: str
    image_b64: str          # data:image/png;base64,<...> hoặc chỉ phần base64
    chart_context: str = "" # mô tả ngắn về chart (tên, loại) để AI có thêm context
    stdout: str = ""        # stdout từ lần execute — chứa giá trị số chính xác


# ─────────────────────────────────────────────────────────────
# Logs endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/api/logs")
async def get_chat_logs(limit: int = 50, offset: int = 0):
    """Return paginated chat history (newest first)."""
    return database.get_chat_logs(limit=limit, offset=offset)

@app.get("/api/logs/executions")
async def get_execution_logs(limit: int = 50, offset: int = 0):
    """Return paginated execution history (newest first)."""
    return database.get_execution_logs(limit=limit, offset=offset)

@app.get("/api/logs/stats")
async def get_log_stats():
    """Return aggregate counts: total chats, total executions, success rate."""
    return database.get_log_stats()


# ─────────────────────────────────────────────────────────────
# Chat endpoint
# ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat_with_ai(req: ChatRequest):
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY not configured. Vui lòng thêm key vào file .env"
        )
    if gemini_model is None:
        raise HTTPException(
            status_code=500,
            detail="Gemini model chưa được khởi tạo. Kiểm tra GOOGLE_API_KEY trong .env"
        )

    try:
        # Build the initial system + context turn that Gemini will see first.
        # AUTO_CONTEXT is generated at startup from the CSV so the frontend
        # does not need to send anything for basic schema awareness.
        system_turn = SYSTEM_PROMPT
        if AUTO_CONTEXT:
            system_turn += f"\n\nAuto-generated dataset context:\n{AUTO_CONTEXT}"

        # FIX 3: use start_chat() with proper history structure instead of
        # concatenating everything into one flat string.
        # The system prompt is injected as the first user→model exchange so
        # Gemini treats it as established context rather than a live request.
        seed_history = [
            {"role": "user",  "parts": [system_turn]},
            {"role": "model", "parts": ['{"code":"","explanation":"Đã hiểu. Tôi sẵn sàng hỗ trợ phân tích dữ liệu chất lượng không khí TPHCM theo 5 mục tiêu đã xác lập."]}']}
        ]
        prior_turns  = _build_gemini_history(req.history)
        full_history = seed_history + prior_turns

        chat_session = gemini_model.start_chat(history=full_history)

        # Compose the current user message
        user_message = req.prompt
        if req.context:
            user_message = f"Thông tin context bổ sung: {req.context}\n\n{req.prompt}"

        response     = chat_session.send_message(user_message)
        result_str   = response.text.strip()
        
        # Tiền xử lý chuỗi: cắt bỏ các mã markdown lừa đảo hoặc Extra data bên ngoài khối JSON.
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        elif result_str.startswith("```"):
            result_str = result_str[3:]
        if result_str.endswith("```"):
            result_str = result_str[:-3]
        result_str = result_str.strip()
        
        # Nếu model trả về nhiều object nối tiếp (vd: `{...}\n{...}`), lấy block đầu tiên.
        # Dùng JSONDecoder().raw_decode để nhặt đúng 1 object JSON đầu tiên,
        # bỏ qua văn bản giải thích thừa phía sau (Extra data error).
        try:
            # Tìm vị trí bắt đầu của JSON ({ hoặc [)
            start_bracket = result_str.find('{')
            start_array = result_str.find('[')
            start_idx = -1
            if start_bracket != -1 and start_array != -1:
                start_idx = min(start_bracket, start_array)
            else:
                start_idx = max(start_bracket, start_array)
            
            if start_idx == -1:
                raise json.JSONDecodeError("Không tìm thấy dấu ngoặc mở JSON", result_str, 0)
                
            json_snippet = result_str[start_idx:]
            decoder = json.JSONDecoder()
            result, end_ptr = decoder.raw_decode(json_snippet)
        except json.JSONDecodeError:
            # Fallback cuối cùng: dùng regex tham lam nếu raw_decode thất bại vì lý do nào đó
            match = re.search(r'(\{.*\}|\[.*\])', result_str, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
            else:
                raise

        # Xử lý trường hợp Gemini trả về mảng [{...}] thay vì dict {...}
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        elif isinstance(result, list):
            result = {}

        # Đảm bảo code và explanation luôn là chuỗi (tránh lỗi null từ AI)
        code_raw    = result.get("code") or ""
        explanation = result.get("explanation") or ""
        code        = _strip_code_fences(code_raw)
        code        = _fix_fstring_quotes(code)

        chat_id = database.log_chat(req.prompt, code, explanation)

        return {"chat_id": chat_id, "code": code, "explanation": explanation}

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model trả về JSON không hợp lệ: {exc}. Raw: {result_str[:300]}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────
# Execute endpoint
# ─────────────────────────────────────────────────────────────

@app.post("/api/execute")
async def execute_code(req: ExecuteRequest):
    # ── Verify chat_id tồn tại ────────────────────────────────
    chat_log = database.get_chat_by_id(req.chat_id)
    if not chat_log:
        raise HTTPException(status_code=404, detail="chat_id không tồn tại.")

    # ── Write code to a unique temp file ─────────────────────
    run_filename = f"run_{req.chat_id[:8]}.py"
    temp_file    = os.path.join(TEMP_DIR, run_filename)

    # Xóa file output cũ trước khi chạy để tránh hiển thị nhầm biểu đồ của lần chạy trước
    html_out  = os.path.join(TEMP_DIR, "output.html")
    png_out   = os.path.join(TEMP_DIR, "output.png")
    if os.path.exists(html_out): os.remove(html_out)
    if os.path.exists(png_out): os.remove(png_out)

    with open(temp_file, "w", encoding="utf-8") as f:
        # Sử dụng Monkey Patching để đánh chặn các hàm hiển thị biểu đồ mặc định
        patch_code = """
import sys, os
import shutil
# Đảm bảo stdout/stderr dùng UTF-8 trên Windows (tránh cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.makedirs('backend/temp', exist_ok=True)
try:
    import plotly.graph_objects as go
    import plotly.io as pio

    def _mirror_to_standard_output(source_path, target_path):
        try:
            source_abs = os.path.abspath(source_path)
            target_abs = os.path.abspath(target_path)
            if os.path.exists(source_abs) and source_abs != target_abs:
                shutil.copyfile(source_abs, target_abs)
        except Exception:
            pass

    def _export_png_from_fig(fig):
        \"\"\"Export figure sang PNG để dùng cho Gemini Vision.\"\"\"
        try:
            fig.write_image('backend/temp/output.png', format='png', width=1000, height=550, scale=2)
        except Exception:
            pass  # kaleido chưa cài hoặc lỗi — bỏ qua

    _original_write_html = go.Figure.write_html
    _original_pio_write_html = pio.write_html

    def _new_show(self, *args, **kwargs):
        _original_write_html(self, 'backend/temp/output.html')
        _export_png_from_fig(self)

    def _new_write_html(self, file='backend/temp/output.html', *args, **kwargs):
        _original_write_html(self, file, *args, **kwargs)
        _mirror_to_standard_output(file, 'backend/temp/output.html')
        _export_png_from_fig(self)

    def _new_pio_write_html(fig, file='backend/temp/output.html', *args, **kwargs):
        _original_pio_write_html(fig, file, *args, **kwargs)
        _mirror_to_standard_output(file, 'backend/temp/output.html')
        _export_png_from_fig(fig)

    go.Figure.show = _new_show
    go.Figure.write_html = _new_write_html
    pio.write_html = _new_pio_write_html
except Exception:
    pass

try:
    import matplotlib.pyplot as plt
    _original_savefig = plt.savefig

    def _new_plt_show(*args, **kwargs):
        _original_savefig('backend/temp/output.png')

    def _new_savefig(fname='backend/temp/output.png', *args, **kwargs):
        _original_savefig(fname, *args, **kwargs)
        try:
            fname_abs = os.path.abspath(fname)
            target_abs = os.path.abspath('backend/temp/output.png')
            if os.path.exists(fname_abs) and fname_abs != target_abs:
                shutil.copyfile(fname_abs, target_abs)
        except Exception:
            pass

    plt.show = _new_plt_show
    plt.savefig = _new_savefig
except Exception:
    pass
"""
        f.write(patch_code + "\n" + req.code)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    stdout = ""
    stderr = ""
    success = False
    
    try:
        try:
            # sys.executable is always the interpreter running this FastAPI process.
            process = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,              # timeout for heavy analysis
                cwd=project_root,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            success = process.returncode == 0
            stdout  = process.stdout
            stderr  = process.stderr
        except subprocess.TimeoutExpired as e:
            success = False
            stdout  = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr  = f"Lỗi: Thực thi quá 60 giây (Timeout).\n{e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or '')}"
        except KeyboardInterrupt:
            success = False
            stdout  = ""
            stderr  = "Lỗi: Tiến trình thực thi bị ngắt quãng (KeyboardInterrupt: client disconnect hoặc cancel)."
        except Exception as e:
            success = False
            stdout  = ""
            stderr  = f"Lỗi hệ thống khi chạy code: {str(e)}"

        # Ghi log kết quả thực thi
        database.log_execution(req.code, stdout, stderr, success, chat_id=req.chat_id)

        # ── Detect chart output ───────────────────────────────
        chart_url = None
        chart_png_b64 = None
        html_out  = os.path.join(TEMP_DIR, "output.html")
        png_out   = os.path.join(TEMP_DIR, "output.png")

        if success:
            if os.path.exists(html_out):
                chart_url = f"/charts/output.html"
                # Thử export PNG từ HTML để dùng cho ask_chart (Gemini Vision)
                chart_png_b64 = _export_chart_png(html_out, png_out)
            elif os.path.exists(png_out):
                chart_url = f"/charts/output.png"
                # Đọc PNG sẵn có thành base64
                try:
                    with open(png_out, "rb") as f:
                        chart_png_b64 = base64.b64encode(f.read()).decode()
                except Exception:
                    pass

        return {
            "success":        success,
            "stdout":         stdout,
            "stderr":         stderr,
            "chart_url":      chart_url,
            "chart_png_b64":  chart_png_b64,  # PNG base64 để frontend dùng cho ask_chart
        }
    finally:
        # Clean up the unique temp script (keep output.html / output.png for serving)
        if os.path.exists(temp_file):
            os.remove(temp_file)


# ─────────────────────────────────────────────────────────────
# Ask-about-chart endpoint
# ─────────────────────────────────────────────────────────────

@app.post("/api/ask_chart")
async def ask_about_chart(req: AskChartRequest):
    """
    Nhận ảnh PNG (base64) của chart đã gen + câu hỏi từ user.
    Gửi lên Gemini Vision để phân tích và trả lời bằng tiếng Việt.
    """
    if not api_key or gemini_vision_model is None:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY chưa được cấu hình.")

    # Tách phần base64 thuần (bỏ data URI prefix nếu có)
    b64_data = req.image_b64
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(b64_data)
    except Exception:
        raise HTTPException(status_code=400, detail="image_b64 không hợp lệ.")

    # Xây dựng prompt cho Gemini Vision
    system_context = """Bạn là chuyên gia phân tích dữ liệu chất lượng không khí TP.HCM.
Người dùng vừa tạo ra một biểu đồ từ dữ liệu thực tế và đang hỏi về nó.

QUY TẮC ĐỌC BIỂU ĐỒ — BẮT BUỘC TUÂN THỦ:
1. Đọc kỹ nhãn trục X và trục Y trước khi trả lời. Không suy đoán vị trí pixel.
2. Nếu trục X có nhãn ngày/tháng (ví dụ "Jan 4", "Jan 14"), hãy đọc chính xác nhãn đó.
3. Nếu không đọc được nhãn rõ ràng, hãy nói "không thể xác định chính xác từ biểu đồ" thay vì đoán.
4. Chỉ trích dẫn giá trị khi nhìn thấy rõ trên biểu đồ (từ colorbar, trục, tooltip label).
5. Phân biệt rõ: đây là biểu đồ tĩnh (PNG), không có tooltip — chỉ đọc được giá trị từ colorbar và nhãn trục.

Trả lời bằng tiếng Việt, ngắn gọn, chính xác.
Nếu biểu đồ liên quan đến chất lượng không khí, so sánh với ngưỡng WHO (PM2.5: 15 µg/m³) hoặc QCVN khi phù hợp."""

    chart_ctx = f"\nLoại biểu đồ: {req.chart_context}" if req.chart_context else ""

    # Nếu có stdout từ lần chạy code, đính kèm làm ground truth số liệu
    stdout_ctx = ""
    if req.stdout and req.stdout.strip():
        stdout_ctx = f"\n\nDỮ LIỆU SỐ CHÍNH XÁC (từ kết quả chạy code — ưu tiên dùng thay vì đọc từ ảnh):\n{req.stdout.strip()[:2000]}"

    full_prompt = f"{system_context}{chart_ctx}{stdout_ctx}\n\nCâu hỏi của người dùng: {req.prompt}"

    try:
        # Gemini multimodal: gửi cả text lẫn image
        image_part = {
            "mime_type": "image/png",
            "data": image_bytes,
        }
        response = gemini_vision_model.generate_content([full_prompt, image_part])
        answer = response.text.strip()
        return {"answer": answer}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
