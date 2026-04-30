import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import sys

output_path = r"c:\Users\Acer\source\repos\Nam3_Ki2\tqhdl\final_pj\dataset\Bao_Cao_Air_Quality_HCMC.pdf"

doc = SimpleDocTemplate(output_path, pagesize=A4,
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=18)

font_path = "C:\\Windows\\Fonts\\arial.ttf"
font_bold_path = "C:\\Windows\\Fonts\\arialbd.ttf"
try:
    pdfmetrics.registerFont(TTFont('Arial', font_path))
    pdfmetrics.registerFont(TTFont('Arial-Bold', font_bold_path))
    font_regular = 'Arial'
    font_bold = 'Arial-Bold'
except Exception as e:
    print(f"Error loading fonts: {e}")
    sys.exit(1)

styles = getSampleStyleSheet()
style_normal = ParagraphStyle('Normal_VN', parent=styles['Normal'], fontName=font_regular, fontSize=11, leading=16)
style_bold = ParagraphStyle('Bold_VN', parent=styles['Normal'], fontName=font_bold, fontSize=11, leading=16)
style_h1 = ParagraphStyle('Heading1_VN', parent=styles['Heading1'], fontName=font_bold, fontSize=16, leading=22, spaceAfter=12, textColor=colors.HexColor('#2c3e50'))
style_h2 = ParagraphStyle('Heading2_VN', parent=styles['Heading2'], fontName=font_bold, fontSize=14, leading=18, spaceAfter=10, textColor=colors.HexColor('#2980b9'))
style_h3 = ParagraphStyle('Heading3_VN', parent=styles['Heading3'], fontName=font_bold, fontSize=12, leading=16, spaceAfter=6, textColor=colors.HexColor('#c0392b'))

Story = []

def add_heading1(text):
    Story.append(Paragraph(text, style_h1))
    
def add_heading2(text):
    Story.append(Paragraph(text, style_h2))
    
def add_heading3(text):
    Story.append(Paragraph(text, style_h3))

def add_para(text):
    Story.append(Paragraph(text, style_normal))
    Story.append(Spacer(1, 6))

add_heading1("BÁO CÁO PHÂN TÍCH DATASET CHẤT LƯỢNG KHÔNG KHÍ TP.HCM")
Story.append(Spacer(1, 12))

# I. Thông tin dataset
add_heading2("I. Tiêu chí và Chi tiết")

data_table = [
    ["Tiêu chí", "Chi tiết"],
    ["Tên", "The HelthyAir Dataset: Outdoor Air Quality in Ho Chi Minh City"],
    ["Link tải", "https://data.mendeley.com/datasets/pk6tzrjks8/1"],
    ["Số dòng", "52,549 bản ghi (sau làm sạch còn 32,510 bản ghi)"],
    ["Số biến", "9 biến (PM2.5, TSP, SO₂, O₃, NO₂, CO, Nhiệt độ, Độ ẩm, Trạm đo)"],
    ["Tần suất", "Theo giờ (hourly)"],
    ["Thời gian", "2/2021 – 6/2022"],
    ["Địa điểm", "TP.HCM – 6 trạm quan trắc"],
    ["Định dạng", "CSV"]
]

table_data = [[Paragraph(cell, style_bold if i==0 else style_normal) for cell in row] for i, row in enumerate(data_table)]
t = Table(table_data, colWidths=[100, 350])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (1,0), colors.HexColor('#ecf0f1')),
    ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
    ('BOX', (0,0), (-1,-1), 0.25, colors.black),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ('TOPPADDING', (0,0), (-1,-1), 8),
]))
Story.append(t)
Story.append(Spacer(1, 20))

# II. Cấu trúc biến
add_heading2("II. Cấu trúc biến và ý nghĩa")
add_para("<b>date:</b> Ngày và giờ ghi nhận dữ liệu.")
add_para("<b>Station_No:</b> Định danh trạm đo quan trắc (từ 1 đến 6).")
add_para("<b>TSP, PM2.5:</b> Nồng độ tổng bụi lơ lửng và bụi mịn PM2.5 (đơn vị: µg/m³).")
add_para("<b>SO2, O3, NO2, CO:</b> Nồng độ các khí thải gây ô nhiễm (đơn vị: µg/m³ hoặc ppb).")
add_para("<b>Temperature:</b> Nhiệt độ môi trường (°C).")
add_para("<b>Humidity:</b> Độ ẩm không khí (%).")
Story.append(Spacer(1, 10))

# III. Nguồn
add_heading2("III. Nguồn và độ tin cậy")
add_para("<b>📄 Chuỗi minh chứng độ tin cậy đầy đủ</b>")
add_para("Dataset này được thu thập từ Mạng lưới quan trắc chất lượng không khí thời gian thực (AQMN) gồm 6 trạm đặt tại các khu vực giao thông, dân cư và công nghiệp tại TP.HCM. Mỗi trạm đo PM2.5, TSP, NO₂, SO₂, O₃, CO và hai thông số khí tượng là nhiệt độ và độ ẩm. Dữ liệu được ghi theo tần suất phút, sau đó tổng hợp theo giờ để phân tích và mô hình hóa. PubMed Central")
add_para("<b>Bài báo khoa học đính kèm (peer-reviewed):</b>")
add_para("• PubMed/PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/")
add_para("• ScienceDirect: https://www.sciencedirect.com/science/article/pii/S2352340922009775")
add_para("• DOI bài báo gốc AI forecasting: 10.1016/j.uclim.2022.101315")
add_para("Dữ liệu PM2.5 từ dataset này đã được sử dụng để xây dựng mô hình dự báo PM2.5 theo giờ, công bố trong bài báo <i>\"AI-based Air Quality PM2.5 Forecasting Models for Developing Countries: A Case Study of Ho Chi Minh City, Vietnam\"</i>. PubMed")
Story.append(Spacer(1, 10))

# IV. Mục tiêu phân tích
add_heading2("IV. Mục tiêu phân tích")

add_heading3("🎯 Mục tiêu 1: Phân tích xu hướng ô nhiễm theo thời gian")
add_para("<b>Số liệu dùng:</b> date, PM2.5, CO, NO2")
add_para("<b>Lý do chọn:</b> Mức độ ô nhiễm thay đổi rõ rệt theo chu kỳ: biến động trong ngày (giờ cao điểm giao thông) và biến động trong năm (mùa mưa/mùa khô).")
add_para("<b>Giá trị mang lại:</b> Người dùng nắm được khung giờ hoặc tháng nào chất lượng không khí suy giảm nhất, từ đó giúp người dân có kế hoạch sinh hoạt và ra đường hợp lý.")
Story.append(Spacer(1, 6))

add_heading3("🎯 Mục tiêu 2: Đánh giá sự phân bố ô nhiễm giữa các khu vực")
add_para("<b>Số liệu dùng:</b> Station_No, PM2.5, TSP, CO")
add_para("<b>Lý do chọn:</b> Ô nhiễm mang tính cục bộ. Tùy thuộc vào vị trí trạm đo (gần quốc lộ, khu công nghiệp hay khu dân cư) mà mức độ ô nhiễm sẽ khác nhau.")
add_para("<b>Giá trị mang lại:</b> Khoanh vùng cảnh báo các khu vực có chất lượng không khí kém thường xuyên tại TP.HCM, hỗ trợ phân tích không gian (spatial analysis).")
Story.append(Spacer(1, 6))

add_heading3("🎯 Mục tiêu 3: Tác động của yếu tố thời tiết đến nồng độ ô nhiễm")
add_para("<b>Số liệu dùng:</b> Temperature, Humidity, PM2.5, O3")
add_para("<b>Lý do chọn:</b> Khí hậu ảnh hưởng rất mạnh đến ô nhiễm. Nhiệt độ cao làm O3 tăng nhanh do phản ứng quang hóa, mưa và độ ẩm giúp khuếch tán bụi PM2.5.")
add_para("<b>Giá trị mang lại:</b> Hiểu rõ cơ chế hình thành ô nhiễm và tương quan nghịch/thuận của các biến, bổ sung một insight khoa học và thực tế cho dashboard.")
Story.append(Spacer(1, 6))

add_heading3("🎯 Mục tiêu 4: Tương quan nội bộ giữa các chất ô nhiễm")
add_para("<b>Số liệu dùng:</b> CO, NO2, SO2, PM2.5")
add_para("<b>Lý do chọn:</b> Tại TP.HCM, CO và NO2 chủ yếu sinh ra từ khói xe cộ. So sánh sự đồng biến giữa chúng giúp kiểm chứng nguồn phát thải chính.")
add_para("<b>Giá trị mang lại:</b> Cung cấp góc nhìn định lượng về nguyên nhân cốt lõi gây ô nhiễm (vd: giao thông so với công nghiệp).")
Story.append(Spacer(1, 6))

add_heading3("🎯 Mục tiêu 5: Xây dựng mô hình dự báo mức độ bụi mịn PM2.5")
add_para("<b>Số liệu dùng:</b> Tất cả các biến khí tượng và chất ô nhiễm (Feature), PM2.5 (Target)")
add_para("<b>Lý do chọn:</b> PM2.5 là chỉ báo sức khỏe quan trọng nhất. Nếu có thể dự báo mức PM2.5 trong vài giờ tiếp theo, nó sẽ là một tính năng cực kỳ giá trị.")
add_para("<b>Giá trị mang lại:</b> Người dùng nhận được cảnh báo sớm về ô nhiễm không khí. Tính năng này nâng tầm đồ án thành một sản phẩm có tính ứng dụng cao.")

doc.build(Story)
print("PDF generated successfully.")
