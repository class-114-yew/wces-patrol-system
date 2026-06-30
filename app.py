import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import smtplib
from email.message import EmailMessage  
import os
import ast  
import time
import io  
import pandas as pd 
import base64

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ==========================================
# 0. 網頁基本設定與手機版 UI/UX 優化 (CSS 注入)
# ==========================================
st.set_page_config(page_title="文昌國小 線上巡堂系統", layout="wide", initial_sidebar_state="collapsed")

def inject_mobile_css():
    st.markdown("""
    <style>
    html, body, [class*="css"], p, div, span, label { font-size: 16px !important; }
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        min-height: 48px !important; min-width: 48px !important; padding: 10px 24px !important;
        border-radius: 8px !important; font-size: 16px !important;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
        min-height: 48px !important; font-size: 16px !important;
    }
    .stRadio label, .stCheckbox label { min-height: 48px !important; display: flex !important; align-items: center !important; }
    
    /* 表格化排版的輔助 CSS */
    .form-row-label { display: flex; align-items: center; min-height: 48px; font-weight: bold; background-color: #F0F2F6; padding-left: 10px; border-radius: 5px; }
    
    @media (max-width: 768px) {
        .block-container { padding-left: 16px !important; padding-right: 16px !important; padding-top: 1rem !important; padding-bottom: 2rem !important; }
        body, html { overflow-x: hidden !important; max-width: 100vw !important; }
        .stDataFrame, div[data-testid="stTable"], .stDataEditor { overflow-x: auto !important; display: block !important; width: 100% !important; }
    }
    </style>
    """, unsafe_allow_html=True)
inject_mobile_css()

# ==========================================
# 全域中文字型註冊機制
# ==========================================
@st.cache_resource
def setup_chinese_font():
    font_name = "CustomChinese"
    if font_name in pdfmetrics.getRegisteredFontNames(): return font_name
    font_paths = [
        "NotoSansTC-Regular.ttf", "C:\\Windows\\Fonts\\msjh.ttc", "C:\\Windows\\Fonts\\msjh.ttf", 
        "C:\\Windows\\Fonts\\mingliu.ttc", "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
            except: continue
    st.error("⚠️ 找不到支援中文的字型檔！請放入 NotoSansTC-Regular.ttf。")
    return "Helvetica"

CHINESE_FONT = setup_chinese_font()

# ==========================================
# 1. 初始化 Firebase 連線
# ==========================================
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

GMAIL_USER = "yew@wces.tc.edu.tw"      
GMAIL_PASSWORD = "msye vyun ygqy wwij"      

ADMIN_USER = "admin"
ADMIN_PASSWORD = "wces1234"

# ==========================================
# 2. 登入系統 (Login Gateway) - 🌟 載入 WebP 底圖與完全透明登入框
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.is_admin = False
    st.session_state.user_info = None

if not st.session_state.logged_in:
    # 修改為讀取 bg.webp 轉為 Base64
    bg_path = "bg.webp"
    bg_base64 = ""
    
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as img_file:
            bg_base64 = base64.b64encode(img_file.read()).decode('utf-8')
    else:
        st.error("⚠️ 找不到 'bg.webp'，請確認圖片是否與 app.py 放在同一個資料夾！")

    if bg_base64:
        st.markdown(f"""
        <style>
        /* 1. 整個網頁的底色：柔和的專業淺灰 */
        .stApp {{
            background-color: #E9ECEF !important;
        }}
        /* 隱藏預設頂部裝飾 */
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        
        /* 2. 確保主要內容區塊在背景圖之上 */
        .block-container {{
            position: relative;
            z-index: 10; 
        }}
        
        /* 3. 登入對話框：完全透明 */
        div[data-testid="stForm"] {{
            background-color: transparent !important; /* 背景透明 */
            backdrop-filter: none !important;         /* 移除毛玻璃模糊 */
            -webkit-backdrop-filter: none !important; /* 移除毛玻璃模糊(Safari) */
            border: none !important;                  /* 移除邊框 */
            box-shadow: none !important;              /* 移除陰影 */
            padding: 35px 30px;
        }}
        
        /* 調整輸入框與按鈕，確保在透明底上依然清晰 */
        .stTextInput input {{ 
            background-color: rgba(255, 255, 255, 0.85) !important; 
            color: #1A365D !important;
            border: 1px solid rgba(255, 255, 255, 0.9) !important;
            font-weight: bold;
        }}
        .stTextInput input:focus {{
            background-color: rgba(255, 255, 255, 1) !important;
        }}
        .stFormSubmitButton > button {{
            background-color: rgba(26, 54, 93, 0.85) !important;
            color: white !important;
            border: none;
            font-weight: bold;
        }}
        </style>
        
        <div style="
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            display: flex; align-items: center; justify-content: center;
            z-index: 0;
            pointer-events: none;
        ">
            <img src="data:image/webp;base64,{bg_base64}" style="
                max-width: 80vw;
                max-height: 80vh;
                object-fit: contain; /* 保證不裁切，完整呈現 */
                border-radius: 24px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            "/>
        </div>
        """, unsafe_allow_html=True)

    # 往下推對齊畫布內部，標題加上光暈以防和圖片融在一起
    st.markdown('<div style="height: 12vh;"></div>', unsafe_allow_html=True)
    # st.markdown('<h1 style="text-align: center; color: #1A365D; text-shadow: 0px 0px 15px rgba(255,255,255,0.9), 2px 2px 4px rgba(255,255,255,0.7); margin-bottom: 40px; font-weight: 900; letter-spacing: 2px;">🏫 文昌國小 線上巡堂系統</h1>', unsafe_allow_html=True)
    
    # 左右不對稱排版：登入框置於右側，左側留白給底圖
    col_left, col_form, col_right = st.columns([5.5, 3.5, 1])
    with col_form:
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #1A365D; text-shadow: 1px 1px 3px rgba(255,255,255,0.6); margin-bottom: 20px;'>🔐 系統登入</h3>", unsafe_allow_html=True)
            u_input = st.text_input("帳號 (Username)")
            p_input = st.text_input("密碼 (Password)", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_login = st.form_submit_button("登入系統", use_container_width=True)
            
            if submit_login:
                u_input_clean = u_input.strip()
                p_input_clean = p_input.strip()
                
                if u_input_clean == ADMIN_USER and p_input_clean == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = True
                    st.session_state.user_info = {"name": "系統管理員", "title": "管理員", "username": u_input_clean}
                    st.rerun()
                else:
                    auth_success = False
                    user_data = None
                    if os.path.exists("teacher.csv"):
                        df = pd.read_csv("teacher.csv", dtype=str).fillna("")
                        df['username'] = df['username'].str.strip()
                        df['password'] = df['password'].str.strip()
                        match = df[(df['username'] == u_input_clean) & (df['password'] == p_input_clean)]
                        if not match.empty:
                            auth_success = True
                            row = match.iloc[0]
                            user_data = {"name": str(row['name']), "username": str(row['username']), "email": str(row['email'])}
                    else: 
                        st.error("找不到 teacher.csv。")
                        
                    if auth_success:
                        ins_doc = db.collection("inspectors").document(u_input_clean).get()
                        if ins_doc.exists:
                            title = ins_doc.to_dict().get("title", "巡堂教職員")
                            user_data["title"] = title
                            st.session_state.logged_in = True
                            st.session_state.is_admin = False
                            st.session_state.user_info = user_data
                            st.success(f"登入成功！")
                            time.sleep(1)
                            st.rerun()
                        else: 
                            st.error("🛑 您尚未被賦予「巡堂權限」。")
                    elif submit_login: 
                        st.error("❌ 帳號或密碼錯誤！")
    st.stop()

# ==========================================
# 3. 側邊欄與頁籤 (登入後的介面)
# ==========================================
st.title("🏫 校園線上巡堂與通知系統")
with st.sidebar:
    st.header(f"👤 您好，{st.session_state.user_info['name']}")
    st.caption(f"目前身分：{st.session_state.user_info['title']}")
    st.markdown("---")
    if st.button("🚪 登出系統"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.user_info = None
        st.rerun()

tabs_list = ["📝 班級巡堂登錄", "🏢 公共區域巡檢", "📋 當日彙整與發送", "🖨️ 每週報表陳核"]
if st.session_state.is_admin: tabs_list.append("⚙️ 管理者設定")

tabs = st.tabs(tabs_list)
tab1, tab_public, tab2, tab3 = tabs[0], tabs[1], tabs[2], tabs[3]
if st.session_state.is_admin: tab4 = tabs[4]

# ==========================================
# 快取輔助與 PDF 產生函式
# ==========================================
@st.cache_data(ttl=600)
def get_all_classes():
    docs = db.collection("schedules").stream()
    return [doc.id for doc in docs]
all_classes = get_all_classes()

def get_all_teachers():
    docs = db.collection("teachers").stream()
    teachers = []
    for doc in docs:
        d = doc.to_dict()
        real_username = d.get("username", "").strip()
        teachers.append({"username": real_username if real_username else doc.id, "name": doc.id, "email": d.get("email", "")})
    return teachers

def get_active_inspectors():
    docs = db.collection("inspectors").stream()
    inspectors = []
    for doc in docs:
        d = doc.to_dict()
        inspectors.append({"name": d.get("name"), "title": d.get("title"), "email": d.get("email"), "display": f"{d.get('title')} ({d.get('name')})"})
    return inspectors

def generate_class_pdf(data, output_filename):
    doc = SimpleDocTemplate(output_filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName=CHINESE_FONT, fontSize=20, leading=26, alignment=1, textColor=colors.HexColor('#1A365D'))
    text_style = ParagraphStyle('Text', fontName=CHINESE_FONT, fontSize=11, leading=16)
    header_style = ParagraphStyle('Header', fontName=CHINESE_FONT, fontSize=11, leading=16, textColor=colors.white, alignment=1)
    center_text = ParagraphStyle('CenterText', fontName=CHINESE_FONT, fontSize=11, leading=16, alignment=1)

    story.append(Table([[Paragraph("🏫 文昌國小巡堂紀錄表", title_style)]], colWidths=[510]))
    story.append(Spacer(1, 15))
    
    info_data = [
        [Paragraph("<b>巡堂日期</b>", center_text), Paragraph(f"{data['date']} ({data['weekday']})", text_style), Paragraph("<b>巡堂節次</b>", center_text), Paragraph(data.get('period', ''), text_style)],
        [Paragraph("<b>巡堂人員</b>", center_text), Paragraph(data['inspector'], text_style), Paragraph("<b>班級名稱</b>", center_text), Paragraph(data.get('class_name', ''), text_style)],
        [Paragraph("<b>任課教師</b>", center_text), Paragraph(data.get('teacher', ''), text_style), Paragraph("<b>授課科目</b>", center_text), Paragraph(data.get('subject', ''), text_style)]
    ]
    info_table = Table(info_data, colWidths=[90, 165, 90, 165])
    info_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EDF2F7')), ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#EDF2F7')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 8)]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    eval_data = [
        [Paragraph("<b>觀察項目</b>", header_style), Paragraph("<b>巡堂觀察</b>", header_style)],
        [Paragraph("是否依據課表上課", text_style), Paragraph(data['evaluation'].get('是否依據課表上課', '無'), center_text)],
        [Paragraph("學生學習專注度", text_style), Paragraph(data['evaluation'].get('學生專注', '無'), center_text)],
        [Paragraph("班級常規秩序", text_style), Paragraph(data['evaluation'].get('班級秩序', '無'), center_text)]
    ]
    
    for item, status in data.get('hardware', {}).items(): 
        eval_data.append([Paragraph(item, text_style), Paragraph(status, center_text)])
        
    eval_table = Table(eval_data, colWidths=[255, 255])
    eval_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#2B6CB0')), 
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey), 
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
        ('BOTTOMPADDING', (0,0), (-1,-1), 6), 
        ('TOPPADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(eval_table)
    story.append(Spacer(1, 15))
    
    notes_val = data.get('notes', '')
    if isinstance(notes_val, dict): notes_val = notes_val.get('班級紀錄', '')
    notes_data = [[Paragraph("<b>備註或建議事項</b>", center_text), Paragraph(notes_val if notes_val else "無特別記錄事項。", text_style)]]
    notes_table = Table(notes_data, colWidths=[120, 390])
    notes_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EDF2F7')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10), ('TOPPADDING', (0,0), (-1,-1), 10)]))
    story.append(notes_table)
    
    story.append(Spacer(1, 40))
    inspector_text = f"巡堂人員：{data['inspector']}"
    story.append(Table([[Paragraph(inspector_text, text_style), Paragraph("處室主管：____________", text_style), Paragraph("校長：____________", text_style)]], colWidths=[200, 155, 155]))
    doc.build(story)

def generate_public_pdf(data, output_filename):
    doc = SimpleDocTemplate(output_filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName=CHINESE_FONT, fontSize=20, leading=26, alignment=1, textColor=colors.HexColor('#276749'))
    text_style = ParagraphStyle('Text', fontName=CHINESE_FONT, fontSize=11, leading=16)
    center_text = ParagraphStyle('CenterText', fontName=CHINESE_FONT, fontSize=11, leading=16, alignment=1)

    story.append(Table([[Paragraph("🏢 文昌國小 公共區域巡檢表", title_style)]], colWidths=[510]))
    story.append(Spacer(1, 15))
    
    info_data = [
        [Paragraph("<b>巡檢日期</b>", center_text), Paragraph(f"{data['date']} ({data['weekday']})", text_style)],
        [Paragraph("<b>巡檢人員</b>", center_text), Paragraph(data['inspector'], text_style)]
    ]
    info_table = Table(info_data, colWidths=[120, 390])
    info_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F0FFF4')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 8)]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    notes_val = data.get('notes', '')
    notes_data = [[Paragraph("<b>巡檢狀況與具體事實描述</b>", center_text)], [Paragraph(notes_val if notes_val else "無特別記錄事項。", text_style)]]
    notes_table = Table(notes_data, colWidths=[510])
    notes_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#C6F6D5')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10), ('TOPPADDING', (0,0), (-1,-1), 10)]))
    story.append(notes_table)
    
    story.append(Spacer(1, 40))
    inspector_text = f"巡檢人員：{data['inspector']}"
    story.append(Table([[Paragraph(inspector_text, text_style), Paragraph("處室主管：____________", text_style), Paragraph("校長：____________", text_style)]], colWidths=[200, 155, 155]))
    doc.build(story)

def generate_weekly_summary_pdf(final_list, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=CHINESE_FONT, fontSize=20, alignment=1, spaceAfter=15)
    cell_style = ParagraphStyle('CellStyle', fontName=CHINESE_FONT, fontSize=10, leading=13)
    header_style = ParagraphStyle('HeaderStyle', fontName=CHINESE_FONT, fontSize=10, leading=13, textColor=colors.whitesmoke)
    
    story.append(Paragraph(f" 文昌國小 週巡堂/巡檢彙整陳核報表 ({start_date} ~ {end_date})", title_style))
    story.append(Spacer(1, 10))
    
    headers = ["日期", "類別/節次", "地點/班級", "任課老師", "依據課表", "秩序評分", "備註狀況說明", "巡堂人"]
    table_data = [[Paragraph(h, header_style) for h in headers]]
    for row in final_list:
        table_data.append([
            Paragraph(str(row["日期"]), cell_style), Paragraph(str(row["類別_節次"]), cell_style),
            Paragraph(str(row["地點_班級"]), cell_style), Paragraph(str(row["任課老師"]), cell_style),
            Paragraph(str(row["依據課表"]), cell_style), Paragraph(str(row["秩序評分"]), cell_style),
            Paragraph(str(row["備註說明"]), cell_style), Paragraph(str(row["巡堂人"]), cell_style)
        ])
    col_widths = [65, 60, 60, 60, 60, 60, 355, 62]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 1), (-1, 0), colors.HexColor('#1E3D59')), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F7FA')]), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==========================================
# 分頁一：班級巡堂登錄 
# ==========================================
with tab1:
    st.header("🔍 班級巡堂登錄")
    
    with st.container(border=True):
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a: 
            if st.session_state.is_admin:
                inspector_options = get_active_inspectors()
                inspector_name = st.selectbox("巡堂人員", inspector_options, format_func=lambda x: x["display"], key="c_insp")["display"] if inspector_options else "未指派"
            else:
                inspector_name = f"{st.session_state.user_info['title']} ({st.session_state.user_info['name']})"
                st.text_input("巡堂人員", value=inspector_name, disabled=True, key="c_insp_d")
        with col_b: 
            inspect_date = st.date_input("巡堂日期", datetime.now(), key="c_date")
        with col_c: 
            weekdays_map = {0: "週一", 1: "週二", 2: "週三", 3: "週四", 4: "週五", 5: "週末", 6: "週末"}
            auto_weekday = weekdays_map[inspect_date.weekday()]
            st.text_input("巡堂星期", value=auto_weekday, disabled=True, key="c_week")
            weekday_opt = auto_weekday
            if auto_weekday == "週末": st.warning("⚠️ 選擇了週末")
        with col_d: 
            period_opt = st.selectbox("巡堂節次", [f"第{i}節" for i in range(1, 8)], key="c_period")

        selected_class = st.selectbox("選擇巡堂班級", ["請選擇..."] + all_classes, key="c_class")
        current_teacher, current_subject = "未知", "自主學習/無"
        
        if selected_class != "請選擇...":
            doc_ref = db.collection("schedules").document(selected_class).get()
            if doc_ref.exists:
                period_data = doc_ref.to_dict().get(weekday_opt, {}).get(period_opt, {})
                current_subject = period_data.get("subject", "空堂")
                current_teacher = period_data.get("teacher", "")
                st.info(f"📋 系統自動帶入課表： **{current_subject}** (任課教師：**{current_teacher}**)")

    if selected_class != "請選擇...":
        with st.form("inspection_submit_form", border=True):
            st.markdown("### 📊 教學與秩序觀察")
            
            col_l1, col_r1 = st.columns([1, 3])
            col_l1.markdown('<div class="form-row-label">是否依據課表上課</div>', unsafe_allow_html=True)
            teach_status = col_r1.radio("是否依據課表上課", ["是", "否"], horizontal=True, label_visibility="collapsed")
            
            col_l2, col_r2 = st.columns([1, 3])
            col_l2.markdown('<div class="form-row-label">學生學習專注度</div>', unsafe_allow_html=True)
            s_focus = col_r2.radio("學生學習專注度", ["優", "良", "可", "待改進"], horizontal=True, label_visibility="collapsed")
            
            col_l3, col_r3 = st.columns([1, 3])
            col_l3.markdown('<div class="form-row-label">班級常規秩序</div>', unsafe_allow_html=True)
            class_order = col_r2.radio("班級常規秩序", ["優", "良", "可", "待改進"], horizontal=True, label_visibility="collapsed")
            
            st.markdown("---")
            st.markdown("### 🛠️ 硬體與環境")
            
            col_l4, col_r4 = st.columns([1, 3])
            col_l4.markdown('<div class="form-row-label">教室設備是否正常</div>', unsafe_allow_html=True)
            hw_equip = col_r4.radio("教室設備是否正常", ["是", "否"], horizontal=True, label_visibility="collapsed")
            
            col_l5, col_r5 = st.columns([1, 3])
            col_l5.markdown('<div class="form-row-label">環境整潔</div>', unsafe_allow_html=True)
            hw_env = col_r5.radio("環境整潔", ["是", "否"], horizontal=True, label_visibility="collapsed")
            
            st.markdown("---")
            st.markdown("### 📝 備註與預設通知單位")
            notes_class = st.text_area("具體事實描述或需行政協助事件", placeholder="若有待改進事項或需處室會辦，請於此說明...")
            
            st.caption("預設會辦單位 (發送時可再做修改)：")
            oc1, oc2, oc3, oc4 = st.columns(4)
            with oc1: o_ju = st.checkbox("教務處", key="c_o1")
            with oc2: o_xue = st.checkbox("學務處", key="c_o2")
            with oc3: o_zong = st.checkbox("總務處", key="c_o3")
            with oc4: o_fu = st.checkbox("輔導室", key="c_o4")
            
            submit_btn = st.form_submit_button("💾 暫存此班級紀錄", use_container_width=True)
            
            if submit_btn:
                offices = []
                if o_ju: offices.append("教務處")
                if o_xue: offices.append("學務處")
                if o_zong: offices.append("總務處")
                if o_fu: offices.append("輔導室")
                
                record_data = {
                    "record_type": "class", 
                    "date": str(inspect_date), "weekday": weekday_opt, "period": period_opt,
                    "inspector": inspector_name, "class_name": selected_class,
                    "teacher": current_teacher, "subject": current_subject,
                    "evaluation": {"是否依據課表上課": teach_status, "學生專注": s_focus, "班級秩序": class_order},
                    "hardware": {"教室設備是否正常": hw_equip, "環境整潔": hw_env}, 
                    "notes": notes_class, "offices": offices,
                    "status": "pending", "timestamp": datetime.now()
                }
                db.collection("records").add(record_data)
                st.success(f"🎉 {selected_class} 紀錄已暫存！")

# ==========================================
# 分頁二：公共區域巡檢
# ==========================================
with tab_public:
    st.header("🏢 公共區域巡檢")
    
    with st.container(border=True):
        col_pa, col_pb, col_pc = st.columns(3)
        with col_pa: 
            if st.session_state.is_admin:
                inspector_options = get_active_inspectors()
                inspector_name_pub = st.selectbox("巡檢人員", inspector_options, format_func=lambda x: x["display"], key="p_insp")["display"] if inspector_options else "未指派人員"
            else:
                inspector_name_pub = f"{st.session_state.user_info['title']} ({st.session_state.user_info['name']})"
                st.text_input("巡檢人員", value=inspector_name_pub, disabled=True, key="p_insp_d")
        with col_pb: 
            inspect_date_pub = st.date_input("巡檢日期", datetime.now(), key="p_date")
        with col_pc: 
            auto_weekday_pub = weekdays_map[inspect_date_pub.weekday()]
            st.text_input("巡檢星期", value=auto_weekday_pub, disabled=True, key="p_week")
            weekday_opt_pub = auto_weekday_pub
            
    with st.form("public_submit_form", border=True):
        notes_public = st.text_area("📝 巡檢狀況與具體事實描述", placeholder="請填寫巡檢區域地點，以及設備損壞、環境髒亂或其他需處理之偶發事件...")
        
        st.caption("預設會辦單位通知：")
        po1, po2, po3, po4 = st.columns(4)
        with po1: p_ju = st.checkbox("教務處", key="p_o1")
        with po2: p_xue = st.checkbox("學務處", key="p_o2")
        with po3: p_zong = st.checkbox("總務處", value=True, key="p_o3")
        with po4: p_fu = st.checkbox("輔導室", key="p_o4")
        
        pub_submit_btn = st.form_submit_button("💾 暫存此公共區域紀錄", use_container_width=True)
        if pub_submit_btn:
            if not notes_public.strip(): 
                st.error("請輸入巡檢狀況與具體事實描述！")
            else:
                offices_pub = []
                if p_ju: offices_pub.append("教務處")
                if p_xue: offices_pub.append("學務處")
                if p_zong: offices_pub.append("總務處")
                if p_fu: offices_pub.append("輔導室")
                db.collection("records").add({
                    "record_type": "public",
                    "date": str(inspect_date_pub), "weekday": weekday_opt_pub,
                    "inspector": inspector_name_pub,
                    "notes": notes_public, "offices": offices_pub,
                    "status": "pending", "timestamp": datetime.now()
                })
                st.success(f"🎉 公共區域巡檢紀錄已暫存！")


# ==========================================
# 分頁三：當日彙整與發送
# ==========================================
with tab2:
    st.header("當日巡堂紀錄彙整與審核")
    view_date = st.date_input("選擇欲檢視彙整的日期", datetime.now(), key="summary_date")
    
    records_ref = db.collection("records").where("date", "==", str(view_date)).where("status", "==", "pending").stream()
    all_pending_records = []
    class_list = []
    public_list = []
    
    for r in records_ref:
        d = r.to_dict()
        d["id"] = r.id
        all_pending_records.append(d)
        rtype = d.get("record_type", "class")
        offices = d.get("offices", [])
        
        d["會辦教務處"] = "教務處" in offices
        d["會辦學務處"] = "學務處" in offices
        d["會辦總務處"] = "總務處" in offices
        d["會辦輔導室"] = "輔導室" in offices
        
        if rtype == "class":
            d["寄給老師"] = True
            class_list.append(d)
        else:
            public_list.append(d)
            
    if not class_list and not public_list:
        st.info("該日期目前沒有暫存的待處理紀錄。")
    else:
        with st.expander("✏️ 點此編輯 / 修改暫存紀錄內容", expanded=False):
            edit_target = st.selectbox(
                "請選擇要修改的紀錄", 
                all_pending_records, 
                format_func=lambda x: f"【{x.get('record_type')=='class' and '班級' or '公共'}】 {x.get('class_name', '公共區域')} - {x.get('period', '全天')}"
            )
            
            if edit_target:
                with st.form("edit_record_form"):
                    st.caption("修改下方資料後，點擊儲存即可覆蓋原暫存紀錄。")
                    is_class = (edit_target.get("record_type") == "class")
                    
                    if is_class:
                        eval_data = edit_target.get("evaluation", {})
                        if isinstance(eval_data, str): eval_data = ast.literal_eval(eval_data)
                        hw_data = edit_target.get("hardware", {})
                        if isinstance(hw_data, str): hw_data = ast.literal_eval(hw_data)
                        
                        e_teach = st.radio("是否依據課表上課", ["是", "否"], index=0 if eval_data.get("是否依據課表上課") == "是" else 1, horizontal=True)
                        e_focus = st.radio("學生學習專注度", ["優", "良", "可", "待改進"], index=["優", "良", "可", "待改進"].index(eval_data.get("學生專注", "優")), horizontal=True)
                        e_order = st.radio("班級常規秩序", ["優", "良", "可", "待改進"], index=["優", "良", "可", "待改進"].index(eval_data.get("班級秩序", "優")), horizontal=True)
                        
                        hc1, hc2 = st.columns(2)
                        with hc1: e_hw_eq = st.radio("教室設備是否正常", ["是", "否"], index=0 if hw_data.get("教室設備是否正常") == "是" else 1, horizontal=True)
                        with hc2: e_hw_env = st.radio("環境整潔", ["是", "否"], index=0 if hw_data.get("環境整潔") == "是" else 1, horizontal=True)
                    
                    e_notes = st.text_area("備註事項", value=edit_target.get("notes", ""))
                    
                    save_edit_btn = st.form_submit_button("儲存修改")
                    if save_edit_btn:
                        update_payload = {"notes": e_notes}
                        if is_class:
                            update_payload["evaluation"] = {"是否依據課表上課": e_teach, "學生專注": e_focus, "班級秩序": e_order}
                            update_payload["hardware"] = {"教室設備是否正常": e_hw_eq, "環境整潔": e_hw_env}
                        
                        db.collection("records").document(edit_target["id"]).update(update_payload)
                        st.success("紀錄已成功更新！畫面即將重新載入。")
                        time.sleep(1)
                        st.rerun()

        st.markdown("---")
        edited_class_df, edited_pub_df = [], []
        
        if class_list:
            st.subheader("📚 針對【巡堂班級】的紀錄 (可選擇發送給授課老師及會辦處室)")
            edited_class_df = st.data_editor(
                class_list, 
                column_config={
                    "id": None, "status": None, "timestamp": None, "evaluation": None, "hardware": None, "offices": None, "notes": None, "record_type": None,
                    "寄給老師": st.column_config.CheckboxColumn("寄給老師", default=True),
                    "會辦教務處": st.column_config.CheckboxColumn("會辦教務處"),
                    "會辦學務處": st.column_config.CheckboxColumn("會辦學務處"),
                    "會辦總務處": st.column_config.CheckboxColumn("會辦總務處"),
                    "會辦輔導室": st.column_config.CheckboxColumn("會辦輔導室")
                }, 
                num_rows="dynamic", key="edit_class"
            )
            
        if public_list:
            st.subheader("🏢 針對【公共區域】的巡檢 (僅寄發給會辦處室)")
            edited_pub_df = st.data_editor(
                public_list, 
                column_config={
                    "id": None, "status": None, "timestamp": None, "offices": None, "notes": None, "record_type": None,
                    "會辦教務處": st.column_config.CheckboxColumn("會辦教務處"),
                    "會辦學務處": st.column_config.CheckboxColumn("會辦學務處"),
                    "會辦總務處": st.column_config.CheckboxColumn("會辦總務處"),
                    "會辦輔導室": st.column_config.CheckboxColumn("會辦輔導室")
                }, 
                num_rows="dynamic", key="edit_pub"
            )
        
        if st.button("🚀 確認發送 PDF 報告並陳核", use_container_width=True):
            st.info("正在生成 PDF 報表並啟動 Gmail 發送，請稍候...")
            
            email_setting_doc = db.collection("settings").document("email_template").get()
            if email_setting_doc.exists:
                email_data = email_setting_doc.to_dict()
                e_subject_tmpl = email_data.get("subject", "【巡堂紀錄通知】{date} {period} - {class_info}")
                e_body_tmpl = email_data.get("body", "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂，詳細紀錄請參閱 PDF 附件檔。\n\n系統自動發出，謝謝您的配合。")
            else:
                e_subject_tmpl = "【巡堂紀錄通知】{date} {period} - {class_info}"
                e_body_tmpl = "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂，詳細紀錄請參閱 PDF 附件檔。\n\n系統自動發出，謝謝您的配合。"

            office_emails = {}
            for doc in db.collection("inspectors").stream():
                ins_data = doc.to_dict()
                title, email = ins_data.get("title", ""), ins_data.get("email", "")
                if "教務" in title: office_emails["教務處"] = email
                elif "學務" in title: office_emails["學務處"] = email
                elif "總務" in title: office_emails["總務處"] = email
                elif "輔導" in title: office_emails["輔導室"] = email
            
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(GMAIL_USER, GMAIL_PASSWORD)
                
                # 發送班級
                for row in edited_class_df:
                    if isinstance(row.get("evaluation"), str): row["evaluation"] = ast.literal_eval(row["evaluation"])
                    if isinstance(row.get("hardware"), str): row["hardware"] = ast.literal_eval(row["hardware"])
                    doc_id, t_name, class_info = row["id"], row["teacher"], row["class_name"]
                    
                    pdf_filename = f"Inspection_{row['date']}_{class_info}.pdf"
                    generate_class_pdf(row, output_filename=pdf_filename) 
                    
                    pdf_data = None
                    if os.path.exists(pdf_filename):
                        with open(pdf_filename, "rb") as f: pdf_data = f.read()
                    
                    t_doc = db.collection("teachers").document(t_name).get()
                    t_email = t_doc.to_dict().get("email", "") if t_doc.exists else ""
                    
                    if row.get("寄給老師", True) and t_email:
                        msg = EmailMessage()
                        custom_subject = e_subject_tmpl.replace("{date}", row['date']).replace("{period}", row['period']).replace("{class_info}", class_info).replace("{t_name}", t_name)
                        custom_body = e_body_tmpl.replace("{date}", row['date']).replace("{period}", row['period']).replace("{class_info}", class_info).replace("{t_name}", t_name)
                        
                        msg['Subject'] = custom_subject
                        msg['From'], msg['To'] = GMAIL_USER, t_email
                        msg.set_content(custom_body)
                        if pdf_data: msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                        server.send_message(msg)
                    
                    target_offices = [o for o, k in zip(["教務處", "學務處", "總務處", "輔導室"], ["會辦教務處", "會辦學務處", "會辦總務處", "會辦輔導室"]) if row.get(k, False)]
                    for office in target_offices:
                        o_email = office_emails.get(office)
                        if o_email:
                            msg_office = EmailMessage()
                            msg_office['Subject'] = f"【巡堂行政會辦追蹤】({office}) - {class_info}"
                            msg_office['From'], msg_office['To'] = GMAIL_USER, o_email
                            msg_office.set_content(f"行政夥伴好：\n\n檢附 {row['date']} {row['period']} 班級巡堂報告，請貴單位協助後續追蹤。詳情見 PDF。\n\n【備註摘要】：\n{row.get('notes', '')}")
                            if pdf_data: msg_office.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                            server.send_message(msg_office)
                    
                    if os.path.exists(pdf_filename): os.remove(pdf_filename)
                    db.collection("records").document(doc_id).update({"status": "approved"})
                
                # 發送公共區域
                for row in edited_pub_df:
                    doc_id = row["id"]
                    pdf_filename = f"PublicArea_{row['date']}.pdf"
                    generate_public_pdf(row, output_filename=pdf_filename) 
                    
                    pdf_data = None
                    if os.path.exists(pdf_filename):
                        with open(pdf_filename, "rb") as f: pdf_data = f.read()
                    
                    target_offices = [o for o, k in zip(["教務處", "學務處", "總務處", "輔導室"], ["會辦教務處", "會辦學務處", "會辦總務處", "會辦輔導室"]) if row.get(k, False)]
                    for office in target_offices:
                        o_email = office_emails.get(office)
                        if o_email:
                            msg_office = EmailMessage()
                            msg_office['Subject'] = f"【公共區域巡檢會辦】({office})"
                            msg_office['From'], msg_office['To'] = GMAIL_USER, o_email
                            msg_office.set_content(f"行政夥伴好：\n\n檢附 {row['date']} 於公共區域之巡檢報告，請貴單位協助後續追蹤。詳情見 PDF。\n\n【備註摘要】：\n{row.get('notes', '')}")
                            if pdf_data: msg_office.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                            server.send_message(msg_office)
                    
                    if os.path.exists(pdf_filename): os.remove(pdf_filename)
                    db.collection("records").document(doc_id).update({"status": "approved"})
                    
                server.quit()
                st.success("🎉 今日巡堂/巡檢紀錄處理完畢！")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"發送失敗。錯誤訊息: {e}")

# ==========================================
# 分頁四：每週報表陳核
# ==========================================
with tab3:
    st.header("週巡堂與巡檢彙整紀錄")
    col_s, col_e = st.columns(2)
    with col_s: start_date = st.date_input("開始日期", datetime.now(), key="weekly_start")
    with col_e: end_date = st.date_input("結束日期", datetime.now(), key="weekly_end")
        
    if "w_data" not in st.session_state: st.session_state.w_data = None
    if "w_pdf" not in st.session_state: st.session_state.w_pdf = None
    if "w_filename" not in st.session_state: st.session_state.w_filename = ""

    if st.button("🔍 產生週彙整報表"):
        with st.spinner("資料調閱與 PDF 生成中..."):
            w_records = db.collection("records").where("date", ">=", str(start_date)).where("date", "<=", str(end_date)).stream()
            final_list = []
            for r in w_records:
                rd = r.to_dict()
                if rd.get("status") != "approved": continue
                
                rtype = rd.get("record_type", "class")
                if rtype == "class":
                    eval_data = rd.get("evaluation", {})
                    if isinstance(eval_data, str): eval_data = ast.literal_eval(eval_data)
                    final_list.append({
                        "日期": rd.get("date", ""), "類別_節次": rd.get("period", ""), "地點_班級": rd.get("class_name", ""),
                        "任課老師": rd.get("teacher", ""), "依據課表": eval_data.get("是否依據課表上課", ""),
                        "秩序評分": eval_data.get("班級秩序", ""), "備註說明": rd.get("notes", ""), "巡堂人": rd.get("inspector", "")
                    })
                else:
                    final_list.append({
                        "日期": rd.get("date", ""), "類別_節次": "公共區域", "地點_班級": "公共區域",
                        "任課老師": "-", "依據課表": "-", "秩序評分": "-",
                        "備註說明": rd.get("notes", ""), "巡堂人": rd.get("inspector", "")
                    })
                
            if final_list:
                st.session_state.w_data = final_list
                st.session_state.w_filename = f"Weekly_Report_{start_date}_to_{end_date}.pdf"
                st.session_state.w_pdf = generate_weekly_summary_pdf(final_list, start_date, end_date)
            else:
                st.session_state.w_data, st.session_state.w_pdf = None, None
                st.info("該日期區間內無已核定的紀錄。")

    if st.session_state.w_data is not None:
        st.dataframe(st.session_state.w_data, use_container_width=True)
        st.download_button(label="📥 下載週彙整 PDF 報表", data=st.session_state.w_pdf, file_name=st.session_state.w_filename, mime="application/pdf")

# ==========================================
# ⚙️ 分頁五：管理者設定 (僅管理員可見)
# ==========================================
if st.session_state.is_admin:
    with tab4:
        st.header("⚙️ 學校行政權限與教師資料維護")
        
        st.subheader("✉️ 巡堂紀錄發送 Email 範本設定")
        email_setting_doc = db.collection("settings").document("email_template").get()
        if email_setting_doc.exists:
            email_data = email_setting_doc.to_dict()
            default_subject = email_data.get("subject", "【巡堂紀錄通知】{date} {period} - {class_info}")
            default_body = email_data.get("body", "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂，詳細紀錄請參閱 PDF 附件檔。\n\n系統自動發出，謝謝您的配合。")
        else:
            default_subject = "【巡堂紀錄通知】{date} {period} - {class_info}"
            default_body = "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂，詳細紀錄請參閱 PDF 附件檔。\n\n系統自動發出，謝謝您的配合。"

        with st.form("email_template_form"):
            st.info("💡 **可用變數標籤** (請連同大括號複製使用)：\n`{t_name}` (老師姓名)、`{date}` (巡堂日期)、`{period}` (巡堂節次)、`{class_info}` (班級名稱)")
            custom_subject = st.text_input("信件主旨範本", value=default_subject)
            custom_body = st.text_area("信件內容範本", value=default_body, height=150)
            submit_template = st.form_submit_button("💾 儲存 Email 範本")
            
            if submit_template:
                db.collection("settings").document("email_template").set({
                    "subject": custom_subject,
                    "body": custom_body
                })
                st.success("🎉 Email 寄送範本已成功更新！下次寄出信件將套用此設定。")

        st.markdown("---")
        
        st.subheader("🛠️ 教師基本資料維護 (修改密碼 / Email)")
        if os.path.exists("teacher.csv"):
            df_teachers = pd.read_csv("teacher.csv", dtype=str).fillna("")
            search_term = st.text_input("🔍 搜尋帳號 (username) 或 姓名 (name)")
            
            if search_term:
                match_df = df_teachers[(df_teachers['username'].str.contains(search_term, case=False, na=False)) | (df_teachers['name'].str.contains(search_term, case=False, na=False))]
                if not match_df.empty:
                    selected_t_edit = st.selectbox("選擇要修改的教師", match_df.to_dict('records'), format_func=lambda x: f"{x['name']} ({x['username']})")
                    col_p, col_e = st.columns(2)
                    with col_p: new_pw = st.text_input("設定新密碼", value=selected_t_edit['password'])
                    with col_e: new_email = st.text_input("設定新 Email", value=selected_t_edit['email'])
                    if st.button("💾 儲存修改"):
                        df_teachers.loc[df_teachers['username'] == selected_t_edit['username'], 'password'] = new_pw
                        df_teachers.loc[df_teachers['username'] == selected_t_edit['username'], 'email'] = new_email
                        df_teachers.to_csv("teacher.csv", index=False)
                        db.collection("teachers").document(selected_t_edit['name']).update({"email": new_email})
                        st.success(f"🎉 已成功更新 {selected_t_edit['name']} 的密碼與 Email 資料！")
                else: st.warning("找不到符合條件的教師。")
        else: st.error("找不到 teacher.csv 檔案。")
            
        st.markdown("---")
        all_teachers = get_all_teachers()
        if all_teachers:
            st.subheader("➕ 賦予新職務與巡堂權限")
            col1, col2, col3 = st.columns(3)
            with col1: selected_t = st.selectbox("選擇教職員", all_teachers, format_func=lambda x: f"{x['name']} ({x['username']})")
            with col2: assigned_title = st.selectbox("賦予行政職務", ["教務主任", "學務主任", "總務主任", "輔導主任", "校長", "教學組長", "生教組長", "研發組長", "巡堂教職員"])
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("確認指派權限"):
                    inspector_id = str(selected_t["username"]).strip()
                    if inspector_id:
                        db.collection("inspectors").document(inspector_id).set({
                            "username": inspector_id, "name": selected_t["name"], "email": selected_t["email"], "title": assigned_title, "updated_at": datetime.now()
                        })
                        st.success(f"🎉 成功指派 **{selected_t['name']}** 擔任 **{assigned_title}**！")
                        time.sleep(1)
                        st.rerun()
                
        st.markdown("---")
        st.subheader("📋 目前已授權巡堂人員與職務清單")
        current_inspectors_docs = db.collection("inspectors").stream()
        inspector_list_for_show = [d.to_dict() | {"doc_id": d.id} for d in current_inspectors_docs]
            
        if inspector_list_for_show:
            for ins in inspector_list_for_show:
                icol1, icol2, icol3, icol4 = st.columns([2, 2, 3, 1])
                with icol1: st.markdown(f"**姓名**：{ins.get('name', '未知')}")
                with icol2: st.markdown(f"**職務**：{ins.get('title', '未知')}")
                with icol3: st.markdown(f"**聯絡信箱**：{ins.get('email', '未知')}")
                with icol4:
                    if st.button("移除", key=f"del_{ins['doc_id']}"):
                        db.collection("inspectors").document(ins['doc_id']).delete()
                        st.rerun()