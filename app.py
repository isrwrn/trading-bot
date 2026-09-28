import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. SYSTEM CONFIG & PAGE SETUP
# ==========================================
st.set_page_config(page_title="AI Trading Assistant", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. ULTIMATE GLASSMORPHISM & FUTURISTIC CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Space+Grotesk:wght@500;700&display=swap');

    /* เปลี่ยนพื้นหลังแบบภาพเรฟ (Deep Navy/Black Gradient) */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #151b2b 0%, #05080f 100%) !important;
        background-attachment: fixed;
        color: #e2e8f0;
        font-family: 'Outfit', sans-serif;
    }

    /* ซ่อน Header/Footer ดั้งเดิมของ Streamlit ให้ดูเป็น App จริงๆ */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* -----------------------------------
       ออกแบบการ์ด (Glass Cards)
       ----------------------------------- */
    .glass-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.4));
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px -10px rgba(0, 240, 255, 0.15);
        border: 1px solid rgba(0, 240, 255, 0.2);
    }

    /* -----------------------------------
       Typography & Colors (เน้นสีตามจุดสำคัญ)
       ----------------------------------- */
    .title-text {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .subtitle-text {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 20px;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .highlight-blue { color: #00f0ff; text-shadow: 0 0 15px rgba(0,240,255,0.4); }
    .highlight-purple { color: #b900ff; text-shadow: 0 0 15px rgba(185,0,255,0.4); }
    .highlight-green { color: #10b981; }
    .highlight-red { color: #ef4444; }

    /* -----------------------------------
       ปรับแต่ง UI ของ Streamlit (Input & Button)
       ----------------------------------- */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #fff !important;
        border-radius: 16px !important;
        padding: 12px 16px !important;
        font-family: 'Outfit', sans-serif !important;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed) !important;
        border: none !important;
        color: white !important;
        border-radius: 16px !important;
        padding: 12px 24px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4) !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.6) !important;
        transform: scale(1.02);
    }
    
    /* ซ่อน Label ของ input บางตัวเพื่อความสะอาด */
    label[data-testid="stWidgetLabel"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CORE LOGIC (เชื่อมโยงข้อมูล)
# ==========================================
if 'market_data' not in st.session_state:
    st.session_state.market_data = None
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = None

@st.cache_data(ttl=60, show_spinner=False)
def scan_market(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty: return None
        c = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
        h = data['High'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['High']
        l = data['Low'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Low']

        ema200 = c.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = c.diff()
        rsi = (100 - (100 / (1 + ((delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean())))).iloc[-1]
        atr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
        last = c.iloc[-1]
        return {
            "ticker": ticker, "price": float(last), "ema200": float(ema200),
            "rsi": float(rsi), "atr": float(atr), 
            "sl": float(last - (1.5 * atr)), "tp": float(last + (3.0 * atr))
        }
    except: return None

def analyze_with_ai(data, prompt_text, api_key):
    genai.configure(api_key=api_key)
    sys_prompt = f"""
    คุณคือผู้ช่วย AI วิเคราะห์การเทรดอัจฉริยะ (อ้างอิงข้อมูล: {data['ticker']}, ราคา {data['price']:.2f}, EMA {data['ema200']:.2f}, RSI {data['rsi']:.1f})
    ตอบคำถามผู้ใช้ด้วยภาษาไทยที่ทันสมัย เข้าใจง่าย จัดรูปแบบให้อ่านง่าย มีการใช้ Bullet points
    คำถาม: {prompt_text}
    """
    try:
        model = genai.GenerativeModel("gemini-3.8-flash")
        return model.generate_content(sys_prompt).text
    except Exception as e: return f"⚠️ ตรวจพบข้อผิดพลาด: {str(e)}"

# ==========================================
# 4. UI/UX LAYOUT (ประกอบร่างหน้าจอ)
# ==========================================
# --- Header ---
st.markdown("<div class='title-text'>สวัสดี, ยินดีต้อนรับกลับสู่ระบบ</div>", unsafe_allow_html=True)
st.markdown(f"<div class='subtitle-text'>AI ASSISTANT TERMINAL • {datetime.now().strftime('%A, %d %B %Y')}</div>", unsafe_allow_html=True)

# --- แบ่ง 3 คอลัมน์หลัก ---
col_left, col_mid, col_right = st.columns([1.2, 2, 1.2], gap="large")

# ==========================================
# COLUMN 1: แผงควบคุมและตั้งค่า (Left Panel)
# ==========================================
with col_left:
    st.markdown("""
    <div class="glass-card">
        <div class="metric-label" style="color: #00f0ff;">⚙️ SYSTEM SETUP</div>
        <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px;">เชื่อมต่อฐานข้อมูล AI</div>
    </div>
    """, unsafe_allow_html=True)
    # ใช้ Widget ปกติ แต่อยู่ใต้ Card ด้านบน
    api_key = st.text_input("API KEY", type="password", placeholder="วาง Gemini API Key ที่นี่...")
    
    st.markdown("""
    <div class="glass-card" style="margin-top: 20px;">
        <div class="metric-label" style="color: #b900ff;">🎯 TARGET LOCK</div>
        <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px;">เลือกสินทรัพย์ที่ต้องการวิเคราะห์</div>
    </div>
    """, unsafe_allow_html=True)
    
    ticker = st.selectbox("TICKER", ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "AAPL", "DELTA.BK", "PTT.BK"])
    
    if st.button("🚀 SYNC DATA (ดึงข้อมูล)"):
        with st.spinner("เชื่อมต่อสัญญาณดาวเทียม..."):
            st.session_state.market_data = scan_market(ticker)
            st.session_state.ai_response = None # เคลียร์คำตอบเก่า

# ==========================================
# COLUMN 2: AI Assistant & Chat (Center Panel)
# ==========================================
with col_mid:
    # สร้างกรอบ AI Avatar จำลองด้วย CSS กราฟิกแสงวงแหวน
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 40px 20px; background: linear-gradient(180deg, rgba(15,23,42,0.8), rgba(9,9,11,0.9));">
        <div style="width: 120px; height: 120px; border-radius: 50%; margin: 0 auto 20px; 
                    background: radial-gradient(circle, rgba(0,240,255,0.2) 0%, rgba(124,58,237,0.1) 100%);
                    box-shadow: 0 0 40px rgba(0, 240, 255, 0.4), inset 0 0 20px rgba(185, 0, 255, 0.5);
                    display: flex; align-items: center; justify-content: center; border: 2px solid rgba(0,240,255,0.3);">
            <span style="font-size: 3rem;">🤖</span>
        </div>
        <div class="metric-label">AI QUANT ASSISTANT</div>
        <div style="color: #fff; font-size: 1.2rem; font-weight: 300; margin-top: 10px;">
            "ฉันพร้อมประมวลผลกลยุทธ์ให้คุณแล้ววันนี้"
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ช่องแชทโต้ตอบ
    st.markdown("<div class='metric-label' style='margin-top: 20px;'>คำสั่งประมวลผล (COMMAND)</div>", unsafe_allow_html=True)
    user_q = st.text_input("CHAT", placeholder="พิมพ์คำถาม... (เช่น ควรเข้าซื้อราคานี้หรือไม่?)")
    
    if st.button("✨ ANALYZE (วิเคราะห์ทันที)"):
        if not api_key:
            st.error("กรุณาใส่ API Key ด้านซ้ายมือระบบก่อนครับ")
        elif not st.session_state.market_data:
            st.error("กรุณากดปุ่ม SYNC DATA เพื่อดึงข้อมูลตลาดก่อนครับ")
        else:
            with st.spinner("AI กำลังคำนวณความน่าจะเป็น..."):
                st.session_state.ai_response = analyze_with_ai(st.session_state.market_data, user_q, api_key)

    # พื้นที่แสดงคำตอบของ AI
    if st.session_state.ai_response:
        st.markdown(f"""
        <div class="glass-card" style="margin-top: 20px; border-left: 4px solid #b900ff;">
            <div class="metric-label" style="color: #b900ff; margin-bottom: 15px;">📊 AI INSIGHTS (ผลการประเมิน)</div>
            <div style="font-size: 1rem; line-height: 1.6; color: #f1f5f9;">
                {st.session_state.ai_response}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# COLUMN 3: Data Dashboard (Right Panel)
# ==========================================
with col_right:
    if st.session_state.market_data:
        d = st.session_state.market_data
        trend_class = "highlight-green" if d['price'] > d['ema200'] else "highlight-red"
        trend_text = "BULLISH (ขาขึ้น)" if d['price'] > d['ema200'] else "BEARISH (ขาลง)"
        
        # กล่องราคา (เน้นสีฟ้า)
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">💰 ราคาปัจจุบัน ({d['ticker']})</div>
            <div class="metric-value highlight-blue">{d['price']:,.2f}</div>
            <div style="font-size: 0.9rem; margin-top: 5px; color: #94a3b8;">
                สถานะแนวโน้ม: <span class="{trend_class}">{trend_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # กล่อง RSI & โมเมนตัม
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">⚡ โมเมนตัมตลาด (RSI)</div>
            <div class="metric-value">{d['rsi']:.1f}</div>
            <div style="font-size: 0.85rem; margin-top: 8px; color: #64748b;">
                *ตํ่ากว่า 30 = โอกาสซื้อ / สูงกว่า 70 = ระวังแรงขาย
            </div>
        </div>
        """, unsafe_allow_html=True)

        # กล่องระบบป้องกันความเสี่ยง (เน้นสีม่วง/แดง)
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label" style="color: #b900ff;">🛡️ โซนความปลอดภัย (R:R 1:2)</div>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>
                    <div style="font-size: 0.8rem; color: #ef4444;">จุดตัดขาดทุน (SL)</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #fff;">{d['sl']:,.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.8rem; color: #10b981;">เป้าหมายทำกำไร (TP)</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #fff;">{d['tp']:,.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Placeholder ตอนยังไม่โหลดข้อมูล
        st.markdown("""
        <div class="glass-card" style="opacity: 0.5; text-align: center; padding: 60px 20px;">
            <div style="font-size: 2rem; margin-bottom: 15px;">📡</div>
            <div class="metric-label">NO DATA SIGNAL</div>
            <div style="font-size: 0.9rem; color: #64748b;">รอการเชื่อมต่อจากผู้ใช้งาน...</div>
        </div>
        """, unsafe_allow_html=True)
