import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. SYSTEM CONFIG & PAGE SETUP
# ==========================================
st.set_page_config(page_title="NEXUS | AI Trading Dashboard", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. TYPOGRAPHY & INTERACTIVE CSS
# ==========================================
st.markdown("""
<style>
    /* นำเข้าฟอนต์: Sans-serif (หัวข้อ), Serif (เนื้อหา), และ Space Grotesk (ตัวเลข) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@500;700&family=Noto+Serif+Thai:wght@400;600;700&family=Space+Grotesk:wght@600;700&display=swap');

    /* เนื้อหาทั่วไป (Body) ใช้ฟอนต์ Serif (มีหัว) */
    html, body, [class*="css"], p, div, span, input {
        font-family: 'Noto Serif Thai', serif !important;
        background: radial-gradient(circle at 50% 0%, #0d111a 0%, #030508 100%) !important;
        background-attachment: fixed;
        color: #e2e8f0;
    }

    /* หัวข้อและปุ่ม (Headings) ใช้ฟอนต์ Sans-serif (ไม่มีหัว) */
    h1, h2, h3, h4, h5, h6, .sans-heading, label, .stButton > button {
        font-family: 'Noto Sans Thai', sans-serif !important;
    }

    /* ซ่อนแถบ Default ของ Streamlit */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* -----------------------------------
       Interactive Glass Cards
       ----------------------------------- */
    .glass-card {
        background: linear-gradient(145deg, rgba(20, 30, 48, 0.75), rgba(10, 15, 25, 0.6));
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out, border 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-4px) scale(1.01);
        box-shadow: 0 15px 40px -10px rgba(0, 240, 255, 0.2);
        border: 1px solid rgba(0, 240, 255, 0.4);
    }

    /* -----------------------------------
       Typography & Highlight Colors
       ----------------------------------- */
    .title-text {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }
    
    .metric-label {
        font-family: 'Noto Sans Thai', sans-serif !important;
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 700; /* เน้นตัวหนาที่หัวข้อสำคัญ */
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    
    .metric-value {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 2.6rem;
        font-weight: 700; /* เน้นตัวเลขหนาพิเศษ */
    }
    
    /* สีเด่นชัดในจุดสำคัญ */
    .color-cyan { color: #00f0ff; text-shadow: 0 0 12px rgba(0,240,255,0.5); }
    .color-purple { color: #b900ff; text-shadow: 0 0 12px rgba(185,0,255,0.5); }
    .color-green { color: #10b981; text-shadow: 0 0 10px rgba(16,185,129,0.4); }
    .color-red { color: #ef4444; text-shadow: 0 0 10px rgba(239,68,68,0.4); }
    .color-white-bold { color: #ffffff; font-weight: 700; }

    /* -----------------------------------
       UI Elements (Inputs & Buttons)
       ----------------------------------- */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: rgba(10, 15, 25, 0.8) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
        font-weight: 600 !important;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #2563eb, #7c3aed) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 12px 20px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.2s ease !important;
        width: 100%;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6) !important;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5) !important;
        transform: scale(1.03); /* ปรับให้ปุ่มเด้งรับนิ้วแบบ Interactive */
    }
    
    /* ซ่อน Label พื้นฐานของ Streamlit */
    label[data-testid="stWidgetLabel"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CORE LOGIC (STATE MANAGEMENT & DATA)
# ==========================================
if 'market_data' not in st.session_state: st.session_state.market_data = None
if 'ai_response' not in st.session_state: st.session_state.ai_response = None

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
    ตอบคำถามผู้ใช้ด้วยภาษาไทย 
    กฎสำคัญ: จงใช้เครื่องหมาย **เน้นข้อความหนา** ในจุดที่เป็นตัวเลข, ราคา, และแอคชั่นสำคัญเสมอ เพื่อให้อ่านกวาดสายตาได้รวดเร็ว
    คำถาม: {prompt_text}
    """
    try:
        model = genai.GenerativeModel("gemini-3.8-flash")
        return model.generate_content(sys_prompt).text
    except Exception as e: return f"⚠️ **เกิดข้อผิดพลาด:** {str(e)}"

# ==========================================
# 4. UI/UX DASHBOARD LAYOUT
# ==========================================
st.markdown("<div class='title-text sans-heading'>ศูนย์ควบคุมกลยุทธ์การลงทุน (NEXUS AI)</div>", unsafe_allow_html=True)
st.markdown(f"<div style='color: #64748b; margin-bottom: 25px; font-weight: 600;'>อัปเดตข้อมูลล่าสุด: <b>{datetime.now().strftime('%d %B %Y | %H:%M')}</b></div>", unsafe_allow_html=True)

# แยกระบบเป็น 3 คอลัมน์ (เหมือนหน้าปัด Dashboard เครื่องบิน)
col_setup, col_ai, col_data = st.columns([1.2, 2.2, 1.2], gap="large")

# ------------------------------------------
# [COLUMN 1] SYSTEM SETUP & TARGET
# ------------------------------------------
with col_setup:
    st.markdown("""
    <div class="glass-card">
        <div class="metric-label color-cyan">⚙️ การเชื่อมต่อ API (GEMINI)</div>
        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 8px;">*จำเป็นต้องใส่รหัสเพื่อใช้งานระบบ AI</div>
    </div>
    """, unsafe_allow_html=True)
    api_key = st.text_input("API KEY", type="password", placeholder="วางรหัส API Key...")
    
    st.markdown("""
    <div class="glass-card" style="margin-top: 15px;">
        <div class="metric-label color-purple">🎯 ล็อกเป้าหมายสินทรัพย์</div>
        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 8px;">เลือกหุ้น หรือ คริปโต ที่ต้องการสแกน</div>
    </div>
    """, unsafe_allow_html=True)
    ticker = st.selectbox("TICKER", ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "AAPL", "DELTA.BK", "PTT.BK"])
    
    st.write("") # Spacer
    if st.button("🚀 ประมวลผลข้อมูล (SYNC)"):
        with st.spinner("กำลังดึงข้อมูลจากตลาดโลก..."):
            st.session_state.market_data = scan_market(ticker)
            st.session_state.ai_response = None

# ------------------------------------------
# [COLUMN 2] AI COMMAND CENTER
# ------------------------------------------
with col_ai:
    # กราฟิก AI Avatar สไตล์ Sci-Fi Dashboard
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 30px 20px; border-top: 3px solid #00f0ff;">
        <div style="width: 100px; height: 100px; border-radius: 50%; margin: 0 auto 15px; 
                    background: radial-gradient(circle, rgba(0,240,255,0.15) 0%, rgba(37,99,235,0.1) 100%);
                    box-shadow: 0 0 30px rgba(0, 240, 255, 0.3), inset 0 0 15px rgba(124, 58, 237, 0.4);
                    display: flex; align-items: center; justify-content: center; border: 1px solid rgba(0,240,255,0.5);">
            <span style="font-size: 2.5rem;">🤖</span>
        </div>
        <div class="metric-label color-white-bold" style="font-size: 1.1rem;">AI QUANT ASSISTANT</div>
        <div style="color: #cbd5e1; font-size: 1.05rem; margin-top: 5px;">
            "รอรับคำสั่งประเมินความเสี่ยงและจังหวะตลาด"
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='metric-label' style='margin-top: 15px;'>ส่งคำสั่งวิเคราะห์ (COMMAND INPUT)</div>", unsafe_allow_html=True)
    user_q = st.text_input("CHAT", placeholder="พิมพ์คำถาม... (เช่น จุดนี้เข้าซื้อได้หรือยัง? ตั้ง Stop loss ตรงไหน?)")
    
    if st.button("✨ ให้ AI วิเคราะห์กลยุทธ์"):
        if not api_key:
            st.error("⚠️ ขัดข้อง: กรุณาใส่ API Key ด้านซ้ายมือก่อนครับ")
        elif not st.session_state.market_data:
            st.error("⚠️ ขัดข้อง: กรุณากดปุ่มประมวลผลข้อมูลสินทรัพย์ก่อนครับ")
        else:
            with st.spinner("AI กำลังวิเคราะห์ตัวเลขสถิติ..."):
                st.session_state.ai_response = analyze_with_ai(st.session_state.market_data, user_q, api_key)

    # กรอบแสดงผลลัพธ์ของ AI
    if st.session_state.ai_response:
        st.markdown(f"""
        <div class="glass-card" style="margin-top: 20px; border-left: 4px solid #b900ff; background: rgba(185,0,255,0.05);">
            <div class="metric-label color-purple" style="font-size: 1.1rem; margin-bottom: 15px;">📊 สรุปกลยุทธ์จาก AI (ACTION PLAN)</div>
            <div style="font-size: 1.1rem; line-height: 1.7; color: #f8fafc;">
                {st.session_state.ai_response}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# [COLUMN 3] LIVE MARKET METRICS
# ------------------------------------------
with col_data:
    if st.session_state.market_data:
        d = st.session_state.market_data
        is_bullish = d['price'] > d['ema200']
        trend_class = "color-green" if is_bullish else "color-red"
        trend_text = "ขาขึ้น (BULLISH)" if is_bullish else "ขาลง (BEARISH)"
        
        # 1. การ์ดราคาปัจจุบัน
        st.markdown(f"""
        <div class="glass-card" style="border-right: 3px solid #00f0ff;">
            <div class="metric-label sans-heading">💰 ราคาปัจจุบัน <span class="color-white-bold">({d['ticker']})</span></div>
            <div class="metric-value color-cyan">{d['price']:,.2f}</div>
            <div style="font-size: 0.95rem; margin-top: 8px; font-weight: 600;">
                ทิศทางหลัก: <span class="{trend_class}">{trend_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. การ์ดโมเมนตัม
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label sans-heading">⚡ แรงเหวี่ยงตลาด (RSI)</div>
            <div class="metric-value color-white-bold">{d['rsi']:.1f}</div>
        </div>
        """, unsafe_allow_html=True)

        # 3. การ์ดความเสี่ยง (SL/TP)
        st.markdown(f"""
        <div class="glass-card" style="border-bottom: 3px solid #b900ff;">
            <div class="metric-label color-purple sans-heading" style="margin-bottom: 10px;">🛡️ ระยะป้องกันความเสี่ยง (1:2)</div>
            
            <div style="margin-bottom: 8px;">
                <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">จุดตัดขาดทุน (SL)</span><br/>
                <span class="metric-value color-red" style="font-size: 2rem;">{d['sl']:,.2f}</span>
            </div>
            
            <div>
                <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">เป้าทำกำไร (TP)</span><br/>
                <span class="metric-value color-green" style="font-size: 2rem;">{d['tp']:,.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # กรอบแสตนด์บายเมื่อยังไม่มีข้อมูล
        st.markdown("""
        <div class="glass-card" style="opacity: 0.4; text-align: center; padding: 80px 20px;">
            <div style="font-size: 2.5rem; margin-bottom: 15px;">📊</div>
            <div class="metric-label sans-heading">WAITING FOR SYNC...</div>
            <div style="font-size: 0.95rem;">โปรดส่งคำสั่งอัปเดตข้อมูลจากแผงด้านซ้าย</div>
        </div>
        """, unsafe_allow_html=True)
