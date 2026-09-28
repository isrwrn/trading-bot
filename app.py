import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. SETUP & SYSTEM CONFIG
# ==========================================
st.set_page_config(page_title="NEXUS AI Terminal", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. FUTURISTIC GLASSMORPHISM CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600&family=Inter:wght@300;500&display=swap');

    /* พื้นหลังหลัก (Deep Space Gradient) */
    .stApp {
        background: radial-gradient(circle at top right, #111827 0%, #05070a 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* หัวข้อและฟอนต์ตัวเลขแบบ Sci-Fi */
    h1, h2, h3, h4, .stMetric [data-testid="stMetricValue"] {
        font-family: 'Chakra Petch', sans-serif !important;
        color: #00f3ff !important;
        text-shadow: 0 0 10px rgba(0, 243, 255, 0.4);
    }

    /* กล่องข้อความ (Inputs) ให้ดูเป็น Terminal */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: rgba(16, 24, 39, 0.7) !important;
        border: 1px solid rgba(0, 243, 255, 0.3) !important;
        color: #00f3ff !important;
        border-radius: 8px !important;
        font-family: 'Chakra Petch', sans-serif;
    }

    /* ปุ่มกดหลัก (Neon Hologram Button) */
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 243, 255, 0.1), rgba(185, 0, 255, 0.1)) !important;
        border: 1px solid #00f3ff !important;
        color: #00f3ff !important;
        border-radius: 12px !important;
        box-shadow: 0 0 15px rgba(0, 243, 255, 0.2) !important;
        transition: all 0.3s ease !important;
        font-family: 'Chakra Petch', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 1px;
    }
    
    /* เอฟเฟกต์ตอนเอาเมาส์ชี้ปุ่ม */
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 243, 255, 0.3), rgba(185, 0, 255, 0.3)) !important;
        box-shadow: 0 0 25px rgba(185, 0, 255, 0.5) !important;
        border-color: #b900ff !important;
        color: #ffffff !important;
        transform: translateY(-2px);
    }

    /* แต่งกล่อง Metric (การ์ดตัวเลข) ให้เป็น Glassmorphism */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        border-left: 4px solid #00f3ff !important;
        transition: transform 0.3s ease, border-left-color 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-left: 4px solid #b900ff !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }

    /* จัดระเบียบ Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(10, 15, 25, 0.8) !important;
        backdrop-filter: blur(15px) !important;
        border-right: 1px solid rgba(0, 243, 255, 0.1) !important;
    }
    hr {
        border-color: rgba(0, 243, 255, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. STATE MANAGEMENT (ให้ข้อมูลเชื่อมกัน)
# ==========================================
if 'active_asset' not in st.session_state:
    st.session_state.active_asset = None
if 'market_data' not in st.session_state:
    st.session_state.market_data = None

# ==========================================
# 4. QUANT ENGINE & AI FUNCTION
# ==========================================
@st.cache_data(ttl=120, show_spinner=False)
def scan_market(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or len(data) < 50: return None
        
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
    except:
        return None

def analyze_with_ai(data, user_prompt):
    sys_prompt = f"""
    คุณคือ NEXUS AI (ระบบที่ปรึกษา Quant Trading ประสบการณ์ 25 ปี)
    วิเคราะห์ข้อมูลนี้และตอบกลับเป็นภาษาไทยแบบดุดัน ชัดเจน สไตล์หุ่นยนต์นักวิเคราะห์:
    สินทรัพย์: {data['ticker']} | ราคา: {data['price']:.2f}
    แนวโน้ม (EMA200): {data['ema200']:.2f} | โมเมนตัม (RSI): {data['rsi']:.2f}
    เป้าหมาย R:R 1:2 -> จุดตัดขาดทุน: {data['sl']:.2f} | จุดทำกำไร: {data['tp']:.2f}
    
    คำสั่งผู้ใช้: "{user_prompt}"
    
    รูปแบบการตอบ:
    [🔴/🟢 STATUS] : BUY / SELL / WAIT
    [📊 ANALYSIS] : (เหตุผลสั้นๆ จากตัวเลข)
    [⚡ ACTION] : (สิ่งที่ต้องทำทันที)
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(sys_prompt).text
    except Exception as e:
        return f"⚠️ SYSTEM ERROR: {str(e)}"

# ==========================================
# 5. SIDEBAR (SYSTEM CONTROLS)
# ==========================================
with st.sidebar:
    st.markdown("## ⚙️ NEXUS KERNEL")
    GEMINI_API_KEY = st.text_input("AUTHORIZATION KEY (GEMINI)", type="password", placeholder="Enter API Key...")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    st.caption("🔒 การเชื่อมต่อเข้ารหัสลับ End-to-End")
    
    st.markdown("---")
    st.markdown("### 📡 RADAR TARGETS")
    st.caption("เลือกเป้าหมายเพื่อซิงค์ข้อมูลกับแผงควบคุมหลัก")
    
    # ระบบเชื่อมโยงข้อมูล (Interactive Sidebar)
    category = st.radio("ASSET CLASS", ["🪙 Crypto", "🇺🇸 US Stocks", "🇹🇭 TH Stocks"], horizontal=True)
    
    if "Crypto" in category:
        selected_ticker = st.selectbox("SYMBOL", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"])
    elif "US" in category:
        selected_ticker = st.selectbox("SYMBOL", ["NVDA", "AAPL", "TSLA", "MSFT"])
    else:
        selected_ticker = st.selectbox("SYMBOL", ["DELTA.BK", "PTT.BK", "CPALL.BK", "KBANK.BK"])

    if st.button("🚀 SYNC DATA", use_container_width=True):
        with st.spinner("SYNCING WITH MAINFRAME..."):
            st.session_state.active_asset = selected_ticker
            st.session_state.market_data = scan_market(selected_ticker)

# ==========================================
# 6. MAIN DASHBOARD (HUD)
# ==========================================
# Header Area
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"<h1>NEXUS // INTELLIGENCE TERMINAL</h1>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align: right; color: #00f3ff; font-family: Chakra Petch;'>{datetime.now().strftime('%Y-%m-%d | %H:%M:%S UTC')}</div>", unsafe_allow_html=True)

st.markdown("---")

# Data Visualization Area
if st.session_state.market_data:
    d = st.session_state.market_data
    
    st.markdown(f"### 📍 ACTIVE TARGET: `{d['ticker']}`")
    
    # แถวแรก: ข้อมูลหลัก
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CURRENT PRICE", f"{d['price']:,.2f}")
    
    trend_color = "normal" if d['price'] > d['ema200'] else "inverse"
    m2.metric("TREND (EMA200)", "BULLISH" if d['price'] > d['ema200'] else "BEARISH", 
              f"{d['price'] - d['ema200']:,.2f}", delta_color=trend_color)
    
    m3.metric("RSI MOMENTUM", f"{d['rsi']:.1f}")
    m4.metric("VOLATILITY (ATR)", f"{d['atr']:.2f}")

    st.write("") # Spacer

    # แถวสอง: ระบบความเสี่ยง
    r1, r2, r3 = st.columns([1, 1, 2])
    r1.metric("🛑 STOP LOSS", f"{d['sl']:,.2f}")
    r2.metric("🎯 TAKE PROFIT", f"{d['tp']:,.2f}")
    
    with r3:
        st.markdown("#### 🧠 AI COMMAND MODULE")
        user_command = st.text_input("", placeholder="พิมพ์คำสั่งให้ AI วิเคราะห์ (เช่น: สภาพตลาดตอนนี้เสี่ยงไหม?)", label_visibility="collapsed")
        
        if st.button("⚡ EXECUTE NEURAL ANALYSIS", use_container_width=True):
            if not GEMINI_API_KEY:
                st.error("ACCESS DENIED: กรุณาใส่ API KEY ที่เมนูด้านซ้าย")
            else:
                with st.spinner("AI IS ANALYZING THE PATTERNS..."):
                    result = analyze_with_ai(d, user_command)
                    st.success("ANALYSIS COMPLETE.")
                    st.markdown(f"<div style='background: rgba(0,243,255,0.05); border-left: 3px solid #b900ff; padding: 15px; border-radius: 5px; font-family: Inter;'>{result}</div>", unsafe_allow_html=True)

else:
    # หน้าจอสแตนด์บาย กรณีที่ยังไม่ได้กดปุ่ม SYNC
    st.info("📡 SYSTEM STANDBY: กรุณาเลือกสินทรัพย์และกดปุ่ม 'SYNC DATA' ที่เมนูด้านซ้ายเพื่อเริ่มต้น")
    
    # กราฟิกจำลอง (Placeholder) ให้ดูเหมือนหน้าจอพร้อมทำงาน
    st.markdown("""
    <div style="opacity: 0.3; text-align: center; padding-top: 50px;">
        <h2 style="color: #00f3ff;">AWAITING TARGET ACQUISITION...</h2>
        <p>Connect API Key > Select Asset > Sync Data</p>
    </div>
    """, unsafe_allow_html=True)
