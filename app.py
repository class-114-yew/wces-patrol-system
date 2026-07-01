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
# 0. 網頁基本設定與 UI 優化
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
    return "Helvetica"

CHINESE_FONT = setup_chinese_font()

# ==========================================
# 1. 初始化 Firebase 連線 (使用 Streamlit Secrets)
# ==========================================
if not firebase_admin._apps:
    firebase_secrets = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secrets)
    firebase_admin.initialize_app(cred)
db = firestore.client()

GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
ADMIN_USER = st.secrets["ADMIN_USER"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# ==========================================
# 2. 登入系統 (Login Gateway)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.is_admin = False
    st.session_state.user_info = None

if not st.session_state.logged_in:
    bg_path = "bg.webp"
    bg_base64 = ""
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as img_file: bg_base64 = base64.b64encode(img_file.read()).decode('utf-8')

    if bg_base64:
        st.markdown(f"""
        <style>
        .stApp {{ background-color: #E9ECEF !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .block-container {{ position: relative; z-index: 10; }}
        div[data-testid="stForm"] {{ background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 35px 30px; }}
        .stTextInput input {{ background-color: rgba(255, 255, 255, 0.85) !important; color: #1A365D !important; border: 1px solid rgba(255, 255, 255, 0.9) !important; font-weight: bold; }}
        </style>
        <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; z-index: 0; pointer-events: none;">
            <img src="data:image/webp;base64,{bg_base64}" style="max-width: 80vw; max-height: 80vh; object-fit: contain; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);"/>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height: 12vh;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="text-align: center; color: #1A365D; text-shadow: 0px 0px 15px rgba(255,255,255,0.9); margin-bottom: 40px; font-weight: 900;">🏫 文昌國小 線上巡堂系統</h1>', unsafe_allow_html=True)
    
    col_left, col_form, col_right = st.columns([5.5, 3.5, 1])
    with col_form:
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #1A365D;'>🔐 系統登入</h3>", unsafe_allow_html=True)
            u_input = st.text_input("帳號 (Username)")
            p_input = st.text_input("密碼 (Password)", type="password")
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
                    teacher_docs = db.collection("teachers").where("username", "==", u_input_clean).where("password", "==", p_input_clean).limit(1).get()
                    if teacher_docs:
                        teacher_data = teacher_docs[0].to_dict()
                        ins_doc = db.collection("inspectors").document(u_input_clean).get()
                        if ins_doc.exists:
                            title = ins_doc.to_dict().get("title", "巡堂教職員")
                            st.session_state.logged_in = True
                            st.session_state.is_admin = False
                            st.session_state.user_info = {
                                "name": teacher_data.get("name", "未知"), 
                                "username": u_input_clean, 
                                "email": teacher_data.get("email", ""),
                                "title": title
                            }
                            st.success(f"登入成功！歡迎 {teacher_data.get('name')}")
                            time.sleep(1); st.rerun()
                        else: st.error("🛑 您尚未被賦予「巡堂權限」，請洽管理員。")
                    else: st.error("❌ 帳號或密碼錯誤！")
    st.stop()

# ==========================================
# 3. 側邊欄與頁籤
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
# ⚡ 核心輔助函式 (完全依賴 Firebase)
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def get_all_classes():
    return [doc.id for doc in db.collection("schedules").stream()]
all_classes = get_all_classes()

@st.cache_data(ttl=60, show_spinner=False)
def get_all_teachers():
    """從 Firebase 取得教師清單，並利用字典確保帳號不重複"""
    docs = db.collection("teachers").stream()
    teachers_dict = {}
    for doc in docs:
        d = doc.to_dict()
        username = d.get("username", doc.id)
        # 用帳號作為 key 來去重
        teachers_dict[username] = {
            "username": username, 
            "name": d.get("name", ""), 
            "password": d.get("password", ""), 
            "homeroom_class": d.get("homeroom_class", ""), 
            "email": d.get("email", "")
        }
    return sorted(list(teachers_dict.values()), key=lambda x: x["username"])

def get_active_inspectors():
    inspectors = []
    for doc in db.collection("inspectors").stream():
        d = doc.to_dict()
        inspectors.append({"name": d.get("name"), "title": d.get("title"), "email": d.get("email"), "display": f"{d.get('title')} ({d.get('name')})"})
    return inspectors

# ----------------- PDF 產生函式區 (保持不變) -----------------
def generate_class_pdf(data, output_filename):
    doc = SimpleDocTemplate(output_filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story, styles = [], getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName=CHINESE_FONT, fontSize=20, leading=26, alignment=1, textColor=colors.HexColor('#1A365D'))
    text_style = ParagraphStyle('Text', fontName=CHINESE_FONT, fontSize=11, leading=16)
    header_style = ParagraphStyle('Header', fontName=CHINESE_FONT, fontSize=11, leading=16, textColor=colors.white, alignment=1)
    center_text = ParagraphStyle('CenterText', fontName=CHINESE_FONT, fontSize=11, leading=16, alignment=1)

    story.append(Table([[Paragraph("🏫 文昌國小巡堂紀錄表", title_style)]], colWidths=[510]))
    story.append(Spacer(1, 15))
    info_table = Table([
        [Paragraph("<b>巡堂日期</b>", center_text), Paragraph(f"{data['date']} ({data['weekday']})", text_style), Paragraph("<b>巡堂節次</b>", center_text), Paragraph(data.get('period', ''), text_style)],
        [Paragraph("<b>巡堂人員</b>", center_text), Paragraph(data['inspector'], text_style), Paragraph("<b>班級名稱</b>", center_text), Paragraph(data.get('class_name', ''), text_style)],
        [Paragraph("<b>任課教師</b>", center_text), Paragraph(data.get('teacher', ''), text_style), Paragraph("<b>授課科目</b>", center_text), Paragraph(data.get('subject', ''), text_style)]
    ], colWidths=[90, 165, 90, 165])
    info_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EDF2F7')), ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#EDF2F7')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 8)]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    eval_data = [[Paragraph("<b>觀察項目</b>", header_style), Paragraph("<b>巡堂觀察</b>", header_style)], [Paragraph("是否依據課表上課", text_style), Paragraph(data['evaluation'].get('是否依據課表上課', '無'), center_text)], [Paragraph("學生學習專注度", text_style), Paragraph(data['evaluation'].get('學生專注', '無'), center_text)], [Paragraph("班級常規秩序", text_style), Paragraph(data['evaluation'].get('班級秩序', '無'), center_text)]]
    for item, status in data.get('hardware', {}).items(): eval_data.append([Paragraph(item, text_style), Paragraph(status, center_text)])
    eval_table = Table(eval_data, colWidths=[255, 255])
    eval_table.setStyle(TableStyle([('BACKGROUND', (0,0), (1,0), colors.HexColor('#2B6CB0')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6)]))
    story.append(eval_table)
    story.append(Spacer(1, 15))
    notes_val = data.get('notes', '')
    if isinstance(notes_val, dict): notes_val = notes_val.get('班級紀錄', '')
    notes_table = Table([[Paragraph("<b>備註或建議事項</b>", center_text), Paragraph(notes_val if notes_val else "無特別記錄事項。", text_style)]], colWidths=[120, 390])
    notes_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EDF2F7')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10), ('TOPPADDING', (0,0), (-1,-1), 10)]))
    story.append(notes_table)
    story.append(Spacer(1, 40))
    story.append(Table([[Paragraph(f"巡堂人員：{data['inspector']}", text_style), Paragraph("處室主管：____________", text_style), Paragraph("校長：____________", text_style)]], colWidths=[200, 155, 155]))
    doc.build(story)

def generate_public_pdf(data, output_filename):
    doc = SimpleDocTemplate(output_filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story, styles = [], getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName=CHINESE_FONT, fontSize=20, leading=26, alignment=1, textColor=colors.HexColor('#276749'))
    text_style = ParagraphStyle('Text', fontName=CHINESE_FONT, fontSize=11, leading=16)
    center_text = ParagraphStyle('CenterText', fontName=CHINESE_FONT, fontSize=11, leading=16, alignment=1)

    story.append(Table([[Paragraph("🏢 文昌國小 公共區域巡檢表", title_style)]], colWidths=[510]))
    story.append(Spacer(1, 15))
    info_table = Table([[Paragraph("<b>巡檢日期</b>", center_text), Paragraph(f"{data['date']} ({data['weekday']})", text_style)], [Paragraph("<b>巡檢人員</b>", center_text), Paragraph(data['inspector'], text_style)]], colWidths=[120, 390])
    info_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F0FFF4')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 8)]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    notes_val = data.get('notes', '')
    notes_table = Table([[Paragraph("<b>巡檢狀況與具體事實描述</b>", center_text)], [Paragraph(notes_val if notes_val else "無特別記錄事項。", text_style)]], colWidths=[510])
    notes_table.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#C6F6D5')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10), ('TOPPADDING', (0,0), (-1,-1), 10)]))
    story.append(notes_table)
    story.append(Spacer(1, 40))
    story.append(Table([[Paragraph(f"巡檢人員：{data['inspector']}", text_style), Paragraph("處室主管：____________", text_style), Paragraph("校長：____________", text_style)]], colWidths=[200, 155, 155]))
    doc.build(story)

def generate_weekly_summary_pdf(final_list, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story, styles = [], getSampleStyleSheet()
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
    t = Table(table_data, colWidths=[65, 60, 60, 60, 60, 60, 355, 62], repeatRows=1)
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
            class_order = col_r3.radio("班級常規秩序", ["優", "良", "可", "待改進"], horizontal=True, label_visibility="collapsed")
            
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
            
            if st.form_submit_button("💾 暫存此班級紀錄", use_container_width=True):
                offices = [o for o, selected in zip(["教務處", "學務處", "總務處", "輔導室"], [o_ju, o_xue, o_zong, o_fu]) if selected]
                db.collection("records").add({
                    "record_type": "class", "date": str(inspect_date), "weekday": weekday_opt, "period": period_opt,
                    "inspector": inspector_name, "class_name": selected_class, "teacher": current_teacher, "subject": current_subject,
                    "evaluation": {"是否依據課表上課": teach_status, "學生專注": s_focus, "班級秩序": class_order},
                    "hardware": {"教室設備是否正常": hw_equip, "環境整潔": hw_env}, "notes": notes_class, "offices": offices,
                    "status": "pending", "timestamp": datetime.now()
                })
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
        with col_pb: inspect_date_pub = st.date_input("巡檢日期", datetime.now(), key="p_date")
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
        
        if st.form_submit_button("💾 暫存此公共區域紀錄", use_container_width=True):
            if not notes_public.strip(): st.error("請輸入巡檢狀況與具體事實描述！")
            else:
                offices_pub = [o for o, selected in zip(["教務處", "學務處", "總務處", "輔導室"], [p_ju, p_xue, p_zong, p_fu]) if selected]
                db.collection("records").add({
                    "record_type": "public", "date": str(inspect_date_pub), "weekday": weekday_opt_pub,
                    "inspector": inspector_name_pub, "notes": notes_public, "offices": offices_pub,
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
    all_pending_records, class_list, public_list = [], [], []
    
    for r in records_ref:
        d = r.to_dict()
        d["id"] = r.id
        all_pending_records.append(d)
        rtype = d.get("record_type", "class")
        offices = d.get("offices", [])
        for office in ["教務處", "學務處", "總務處", "輔導室"]: d[f"會辦{office}"] = office in offices
        
        if rtype == "class":
            d["寄給老師"] = True
            class_list.append(d)
        else: public_list.append(d)
            
    if not class_list and not public_list: st.info("該日期目前沒有暫存的待處理紀錄。")
    else:
        with st.expander("✏️ 點此編輯 / 修改暫存紀錄內容", expanded=False):
            edit_target = st.selectbox("請選擇要修改的紀錄", all_pending_records, format_func=lambda x: f"【{x.get('record_type')=='class' and '班級' or '公共'}】 {x.get('class_name', '公共區域')} - {x.get('period', '全天')}")
            if edit_target:
                with st.form("edit_record_form"):
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
                    if st.form_submit_button("儲存修改"):
                        update_payload = {"notes": e_notes}
                        if is_class:
                            update_payload["evaluation"] = {"是否依據課表上課": e_teach, "學生專注": e_focus, "班級秩序": e_order}
                            update_payload["hardware"] = {"教室設備是否正常": e_hw_eq, "環境整潔": e_hw_env}
                        db.collection("records").document(edit_target["id"]).update(update_payload)
                        st.success("紀錄已成功更新！即將重新載入。")
                        time.sleep(1); st.rerun()

        st.markdown("---")
        edited_class_df, edited_pub_df = [], []
        if class_list:
            st.subheader("📚 針對【巡堂班級】的紀錄")
            edited_class_df = st.data_editor(class_list, column_config={
                "id": None, "status": None, "timestamp": None, "evaluation": None, "hardware": None, "offices": None, "notes": None, "record_type": None,
                "寄給老師": st.column_config.CheckboxColumn("寄給老師", default=True), "會辦教務處": st.column_config.CheckboxColumn("會辦教務處"),
                "會辦學務處": st.column_config.CheckboxColumn("會辦學務處"), "會辦總務處": st.column_config.CheckboxColumn("會辦總務處"), "會辦輔導室": st.column_config.CheckboxColumn("會辦輔導室")
            }, num_rows="dynamic", key="edit_class")
            
        if public_list:
            st.subheader("🏢 針對【公共區域】的巡檢")
            edited_pub_df = st.data_editor(public_list, column_config={
                "id": None, "status": None, "timestamp": None, "offices": None, "notes": None, "record_type": None,
                "會辦教務處": st.column_config.CheckboxColumn("會辦教務處"), "會辦學務處": st.column_config.CheckboxColumn("會辦學務處"),
                "會辦總務處": st.column_config.CheckboxColumn("會辦總務處"), "會辦輔導室": st.column_config.CheckboxColumn("會辦輔導室")
            }, num_rows="dynamic", key="edit_pub")
        
        if st.button("🚀 確認發送 PDF 報告並陳核", use_container_width=True):
            st.info("處理中，請稍候...")
            email_data = db.collection("settings").document("email_template").get().to_dict() or {}
            e_subject_tmpl = email_data.get("subject", "【巡堂紀錄通知】{date} {period} - {class_info}")
            e_body_tmpl = email_data.get("body", "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂...\n\n系統自動發出，謝謝配合。")
            office_emails = {doc.to_dict().get("title", "")[:2]+"處": doc.to_dict().get("email", "") for doc in db.collection("inspectors").stream()}
            
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(GMAIL_USER, GMAIL_PASSWORD)
                
                for row in edited_class_df:
                    if isinstance(row.get("evaluation"), str): row["evaluation"] = ast.literal_eval(row["evaluation"])
                    if isinstance(row.get("hardware"), str): row["hardware"] = ast.literal_eval(row["hardware"])
                    doc_id, t_name, class_info = row["id"], row["teacher"], row["class_name"]
                    pdf_filename = f"Inspection_{row['date']}_{class_info}.pdf"
                    generate_class_pdf(row, output_filename=pdf_filename) 
                    pdf_data = open(pdf_filename, "rb").read() if os.path.exists(pdf_filename) else None
                    
                    t_doc = db.collection("teachers").where("name", "==", t_name).limit(1).get() # 尋找同名老師
                    t_email = t_doc[0].to_dict().get("email", "") if t_doc else ""
                    
                    if row.get("寄給老師", True) and t_email:
                        msg = EmailMessage()
                        msg['Subject'] = e_subject_tmpl.replace("{date}", row['date']).replace("{period}", row['period']).replace("{class_info}", class_info).replace("{t_name}", t_name)
                        msg['From'], msg['To'] = GMAIL_USER, t_email
                        msg.set_content(e_body_tmpl.replace("{date}", row['date']).replace("{period}", row['period']).replace("{class_info}", class_info).replace("{t_name}", t_name))
                        if pdf_data: msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                        server.send_message(msg)
                    
                    for office in ["教務處", "學務處", "總務處", "輔導室"]:
                        if row.get(f"會辦{office}", False) and office_emails.get(office):
                            msg_office = EmailMessage()
                            msg_office['Subject'] = f"【巡堂行政會辦追蹤】({office}) - {class_info}"
                            msg_office['From'], msg_office['To'] = GMAIL_USER, office_emails.get(office)
                            msg_office.set_content(f"行政夥伴好：\n\n檢附 {row['date']} {row['period']} 班級巡堂報告。詳情見 PDF。\n\n備註摘要：\n{row.get('notes', '')}")
                            if pdf_data: msg_office.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                            server.send_message(msg_office)
                    if os.path.exists(pdf_filename): os.remove(pdf_filename)
                    db.collection("records").document(doc_id).update({"status": "approved"})
                
                for row in edited_pub_df:
                    pdf_filename = f"PublicArea_{row['date']}.pdf"
                    generate_public_pdf(row, output_filename=pdf_filename) 
                    pdf_data = open(pdf_filename, "rb").read() if os.path.exists(pdf_filename) else None
                    for office in ["教務處", "學務處", "總務處", "輔導室"]:
                        if row.get(f"會辦{office}", False) and office_emails.get(office):
                            msg_office = EmailMessage()
                            msg_office['Subject'] = f"【公共區域巡檢會辦】({office})"
                            msg_office['From'], msg_office['To'] = GMAIL_USER, office_emails.get(office)
                            msg_office.set_content(f"行政夥伴好：\n\n檢附 {row['date']} 於公共區域之巡檢報告。詳情見 PDF。\n\n備註摘要：\n{row.get('notes', '')}")
                            if pdf_data: msg_office.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
                            server.send_message(msg_office)
                    if os.path.exists(pdf_filename): os.remove(pdf_filename)
                    db.collection("records").document(row["id"]).update({"status": "approved"})
                    
                server.quit()
                st.success("🎉 紀錄發送完畢！")
                time.sleep(2); st.rerun()
            except Exception as e: st.error(f"發送失敗: {e}")

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

    if st.button("🔍 產生週彙整報表"):
        with st.spinner("報表生成中..."):
            w_records = db.collection("records").where("date", ">=", str(start_date)).where("date", "<=", str(end_date)).stream()
            final_list = []
            for r in w_records:
                rd = r.to_dict()
                if rd.get("status") != "approved": continue
                rtype = rd.get("record_type", "class")
                if rtype == "class":
                    eval_data = ast.literal_eval(rd.get("evaluation", "{}")) if isinstance(rd.get("evaluation"), str) else rd.get("evaluation", {})
                    final_list.append({
                        "日期": rd.get("date", ""), "類別_節次": rd.get("period", ""), "地點_班級": rd.get("class_name", ""),
                        "任課老師": rd.get("teacher", ""), "依據課表": eval_data.get("是否依據課表上課", ""),
                        "秩序評分": eval_data.get("班級秩序", ""), "備註說明": rd.get("notes", ""), "巡堂人": rd.get("inspector", "")
                    })
                else:
                    final_list.append({
                        "日期": rd.get("date", ""), "類別_節次": "公共區域", "地點_班級": "公共區域",
                        "任課老師": "-", "依據課表": "-", "秩序評分": "-", "備註說明": rd.get("notes", ""), "巡堂人": rd.get("inspector", "")
                    })
            if final_list:
                st.session_state.w_data = final_list
                st.session_state.w_filename = f"Weekly_Report_{start_date}_to_{end_date}.pdf"
                st.session_state.w_pdf = generate_weekly_summary_pdf(final_list, start_date, end_date)
            else:
                st.session_state.w_data, st.session_state.w_pdf = None, None
                st.info("該日期區間無已核定紀錄。")

    if st.session_state.w_data is not None:
        st.dataframe(st.session_state.w_data, use_container_width=True)
        st.download_button("📥 下載 PDF 報表", data=st.session_state.w_pdf, file_name=st.session_state.w_filename, mime="application/pdf")

# ==========================================
# ⚙️ 分頁五：管理者設定
# ==========================================
if st.session_state.is_admin:
    with tab4:
        st.header("⚙️ 學校行政權限與教師資料維護")
        
        # 信件範本設定
        st.subheader("✉️ Email 範本設定")
        email_data = db.collection("settings").document("email_template").get().to_dict() or {}
        with st.form("email_template_form"):
            st.info("💡 變數標籤：`{t_name}`, `{date}`, `{period}`, `{class_info}`")
            custom_subject = st.text_input("信件主旨範本", value=email_data.get("subject", "【巡堂紀錄通知】{date} {period} - {class_info}"))
            custom_body = st.text_area("信件內容範本", value=email_data.get("body", "{t_name} 老師您好：\n\n主管於 {date} {period} 至您授課的 【{class_info}】 進行巡堂...\n\n謝謝配合。"), height=150)
            if st.form_submit_button("💾 儲存範本"):
                db.collection("settings").document("email_template").set({"subject": custom_subject, "body": custom_body})
                st.success("🎉 更新成功！")

        st.markdown("---")
        
        all_teachers = get_all_teachers()
        
        # ✅ 需求 1: 使用者資料修改，改為搜尋模式
        st.subheader("🛠️ 教師基本資料修改 (搜尋)")
        search_query = st.text_input("🔍 請輸入教師「姓名」或「帳號」進行搜尋：").strip()
        
        if search_query:
            # 根據搜尋字串過濾名單
            filtered_teachers = [t for t in all_teachers if search_query in t['name'] or search_query in t['username']]
            
            if filtered_teachers:
                selected_t_edit = st.selectbox("請選擇要修改的教師", filtered_teachers, format_func=lambda x: f"{x['name']} ({x['username']})")
                
                with st.form("edit_teacher_form"):
                    col_name, col_pw, col_class = st.columns(3)
                    with col_name: new_name = st.text_input("姓名", value=selected_t_edit['name'])
                    with col_pw: new_pw = st.text_input("密碼", value=selected_t_edit['password'])
                    with col_class: new_class = st.text_input("班級", value=selected_t_edit['homeroom_class'])
                    new_email = st.text_input("Email", value=selected_t_edit['email'])
                    
                    if st.form_submit_button("💾 儲存修改"):
                        db.collection("teachers").document(selected_t_edit['username']).update({
                            "name": new_name,
                            "password": new_pw,
                            "homeroom_class": new_class,
                            "email": new_email
                        })
                        get_all_teachers.clear() # 清除快取
                        st.success(f"🎉 已更新 {new_name} 老師的資料！")
                        time.sleep(1); st.rerun()
            else:
                st.warning("找不到符合條件的教師，請重新確認姓名或帳號。")
        else:
            st.info("👆 在上方輸入框打字，即可搜尋並修改教職員資料。")
            
        st.markdown("---")
        
        # ✅ 需求 2: 賦予權限選單，只顯示姓名
        st.subheader("➕ 賦予新職務與巡堂權限")
        col1, col2, col3 = st.columns(3)
        with col1: 
            # 這裡的 format_func 改為只顯示姓名 (x['name'])
            selected_t = st.selectbox("選擇教職員 (指派權限)", all_teachers, format_func=lambda x: x['name'], key="assign_role")
        with col2: 
            assigned_title = st.selectbox("賦予行政職務", ["教務主任", "學務主任", "總務主任", "輔導主任", "校長", "教學組長", "生教組長", "研發組長", "巡堂教職員"])
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("確認指派權限"):
                db.collection("inspectors").document(selected_t['username']).set({
                    "username": selected_t['username'], "name": selected_t["name"], "email": selected_t["email"], "title": assigned_title, "updated_at": datetime.now()
                })
                st.success(f"🎉 成功指派 **{selected_t['name']}** 擔任 **{assigned_title}**！")
                time.sleep(1); st.rerun()
                
        st.markdown("---")
        st.subheader("📋 目前已授權巡堂人員與職務清單")
        for ins in [d.to_dict() | {"doc_id": d.id} for d in db.collection("inspectors").stream()]:
            icol1, icol2, icol3, icol4 = st.columns([2, 2, 3, 1])
            with icol1: st.markdown(f"**姓名**：{ins.get('name', '未知')}")
            with icol2: st.markdown(f"**職務**：{ins.get('title', '未知')}")
            with icol3: st.markdown(f"**信箱**：{ins.get('email', '未知')}")
            with icol4:
                if st.button("移除", key=f"del_{ins['doc_id']}"):
                    db.collection("inspectors").document(ins['doc_id']).delete()
                    st.rerun()