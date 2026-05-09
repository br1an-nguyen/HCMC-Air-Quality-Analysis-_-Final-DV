from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
from groq import Groq
from dotenv import load_dotenv
try:
    from backend import database
except ImportError:
    import database


load_dotenv()

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "dummy_key"))

class ChatRequest(BaseModel):
    prompt: str
    context: str = ""

class ExecuteRequest(BaseModel):
    code: str

SYSTEM_PROMPT = """Bạn là một Chuyên gia Phân tích Dữ liệu Chất lượng Không khí tại TP.HCM. 
Nhiệm vụ của bạn là hỗ trợ người dùng phân tích tập dữ liệu chất lượng không khí của dự án.
Dữ liệu chính nằm tại file: 'data/cleaned/Air_Quality_HCMC_Cleaned.csv'.
Đây là dữ liệu quan trắc tại 6 trạm ở TPHCM (tháng 2/2021 - 6/2022) theo từng giờ.
Các cột trong dữ liệu bao gồm:
- Date: Ngày đo (YYYY-MM-DD)
- Hour: Giờ đo (0-23)
- Station_No: Trạm quan trắc (1-6)
- PM2.5, TSP: Nồng độ bụi mịn và bụi lơ lửng (µg/m³)
- SO2, O3, NO2, CO: Nồng độ khí thải
- Temperature: Nhiệt độ (°C)
- Humidity: Độ ẩm (%)
- Các cột cờ chất lượng (nếu cờ != 0 nghĩa là dữ liệu lỗi): TSP_flag, PM2.5_flag, O3_flag, CO_flag, NO2_flag, SO2_flag, Temperature_flag, Humidity_flag. Nếu người dùng yêu cầu tính toán chính xác, hãy khuyên họ nên lọc bỏ các giá trị có cờ != 0 (set bằng NaN).

LUẬT BẮT BUỘC:
1. LUÔN sử dụng đường dẫn 'data/cleaned/Air_Quality_HCMC_Cleaned.csv' khi load dữ liệu bằng pandas.
2. CHỈ SỬ DỤNG các thư viện đã được cài đặt: pandas, numpy, plotly, matplotlib, seaborn, statsmodels, scikit-learn. KHÔNG tự ý import các module lạ khác.
3. LUÔN restrict bản thân: Chỉ trả lời các câu hỏi liên quan đến phân tích dữ liệu, xử lý dữ liệu (Python), vẽ biểu đồ hoặc chất lượng không khí TPHCM. Nếu hỏi ngoài lề, từ chối lịch sự.
4. Khi người dùng yêu cầu phân tích, hãy trả về kết quả dưới định dạng JSON:
{
    "code": "mã python ở đây, sử dụng pandas, numpy, plotly",
    "explanation": "giải thích chi tiết logic của mã"
}
Code phải tự chứa đầy đủ thư viện (import pandas as pd, v.v.). Nếu code sinh ra biểu đồ bằng Plotly, hãy dùng fig.show().
"""

@app.post("/api/chat")
async def chat_with_ai(req: ChatRequest):
    if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "your_api_key_here":
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured. Vui lòng thêm key vào file .env")
        
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context data schema: {req.context}\n\nUser request: {req.prompt}"}
        ]
        
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        
        result_str = chat_completion.choices[0].message.content
        import json
        import textwrap
        result = json.loads(result_str)
        
        code = result.get("code", "")
        if code:
            code = textwrap.dedent(code).strip()
            # Remove markdown code blocks if the LLM hallucinated them
            if code.startswith("```python"):
                code = code[9:].strip()
            elif code.startswith("```"):
                code = code[3:].strip()
            if code.endswith("```"):
                code = code[:-3].strip()
                
        explanation = result.get("explanation", "")
        
        database.log_chat(req.prompt, code, explanation)
        
        return {"code": code, "explanation": explanation}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute")
async def execute_code(req: ExecuteRequest):
    # LƯU Ý BẢO MẬT: Sandbox lỏng (Chạy trực tiếp)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    temp_file = os.path.join(temp_dir, "run.py")
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(req.code)
        
    try:
        # Chạy code bằng subprocess, đặt cwd về thư mục gốc dự án
        process = subprocess.run(
            ["python", temp_file],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=project_root
        )
        
        success = process.returncode == 0
        database.log_execution(req.code, process.stdout, process.stderr, success)
        
        return {
            "success": success,
            "stdout": process.stdout,
            "stderr": process.stderr
        }
    except subprocess.TimeoutExpired:
        database.log_execution(req.code, "", "Timeout Expired (20s)", False)
        return {
            "success": False,
            "stdout": "",
            "stderr": "Execution timed out after 20 seconds."
        }
    except Exception as e:
        database.log_execution(req.code, "", str(e), False)
        raise HTTPException(status_code=500, detail=str(e))
