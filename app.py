import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai

# ==========================================
# [ลำดับที่ 8, 10] กำหนดเลย์เอาต์พื้นฐาน
# ==========================================
st.set_page_config(page_title="VETERAN // COMMAND CENTER", layout="wide", page_icon="🛰️")

# ==========================================
# [ลำดับที่ 1-7] ระบบ Custom CSS Theme Engine สไตล์ Sci-Fi
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap');
    
    /* พื้นหลังและฟอนต์หลัก */
    html, body, [class*="css"] {
        font-family: 'Share Tech Mono', monospace !important;
        background-color: #0a0a0a !important;
        color: #00FF41 !important; /* สีเขียว Cyberpunk */
    }
    
    /* หัวข้อและ Tab */
    h1, h2, h3, .stTabs [data-baseweb="tab-list"] {
        font-family: 'Orbitron', sans-serif !important;
        color: #00FFFF !important; /* สีฟ้า Neon */
        text-shadow: 0 0 10px #00FFFF;
    }
    
    /* กล่องข้อความและตัวเลือก */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        color: #00FF41 !important;
        background-color: #111 !important;
        border: 1px solid #00FF41 !important;
        border-radius: 0px !important; /* กล่องเหลี่ยมล้ำอนาคต */
    }
    
    /* ปุ่มกด Sci-Fi Action */
    .stButton > button {
        background-color: transparent !important;
        color: #FF003C !important;
        border: 1px solid #FF003C !important;
        box-shadow: 0 0 8px #FF003C !important;
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 0px !important;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #FF003C !important;
        color: #fff !important;
        box-shadow: 0 0 20px #FF003C !important;
    }
    
    /* กรอบ Metric Data (HUD) */
    div[data-testid="stMetricValue"] {
        color: #00FFFF !important;
        font-size: 28px !important;
        text-shadow: 0 0 5px #00FFFF;
    }
    div[data-testid="stMetricLabel"] {
        color: #888 !important;
        font-family: 'Orbitron', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [ลำดับที่ 21] ระบบรักษาความปลอดภัย API Key
# ==========================================
st.sidebar.markdown("### 🔐 SYSTEM OVERRIDE")
st.sidebar.caption("SECURE CONNECTION INITIALIZED.")
GEMINI_API_KEY = st.sidebar.text_input("ENTER GEMINI API KEY", type="password")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# [ลำดับที่ 26, 28] Smart Data Caching ลดการดึงข้อมูลซ้ำ
# ==========================================
@st.cache_data(ttl=300) # แคชข้อมูลไว้ 5 นาที (300 วินาที) ไม่ต้องโหลดใหม่ทุกครั้งที่กดปุ่ม
def fetch_and_calc(ticker: str):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or len(data) < 50:
            return None
        
        close = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
        high = data['High'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['High']
        low = data['Low'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Low']

        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]

        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        last_price = close.iloc[-1]
        return {
            "ticker": ticker,
            "price": float(last_price),
            "ema200": float(ema200),
            "rsi": float(rsi),
            "atr": float(atr),
            "sl": float(last_price - (1.5 * atr)),
            "tp": float(last_price + (3.0 * atr))
        }
    except Exception as e:
        return None

def ask_veteran(market_data: dict, user_intent: str):
    prompt = f"""
    คุณคือหัวหน้านักกลยุทธ์การลงทุนอาวุโส (Senior Quant Trader) ประสบการณ์ 25 ปีในวอลล์สตรีท
    จงประเมินข้อมูลอย่างดุดัน ไร้อารมณ์ และปฏิเสธความเสี่ยง หากเงื่อนไขไม่ 100% ให้สั่ง NO TRADE

    [DATA UPLINK]: {market_data['ticker']}
    - CURRENT PRICE: {market_data['price']:.2f}
    - EMA(200) TREND: {market_data['ema200']:.2f}
    - RSI(14) MOMENTUM: {market_data['rsi']:.2f}
    - ATR VOLATILITY: {market_data['atr']:.2f}
    - AUTO STOP-LOSS: {market_data['sl']:.2f}
    - AUTO TAKE-PROFIT: {market_data['tp']:.2f}

    [USER COMMAND]: "{user_intent}"

    จงตอบกลับด้วยรูปแบบรายงานทางการทหาร:
    1. DECISION: [BUY / SELL / HOLD / NO TRADE]
    2. TACTICAL ANALYSIS: (เหตุผลเชิง Quant และจิตวิทยา)
    3. ACTION PLAN: (สิ่งที่ต้องทำทันที)
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # ใช้ 1.5 flash รุ่นมาตรฐาน
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ **SYSTEM ERROR [AI API]:** `{str(e)}`"

# ==========================================
# โครงสร้างหน้า Dashboard
# ==========================================
st.title("🛰️ VETERAN // COMMAND CENTER")
st.markdown("---")

# แบ่งหน้าด้วยระบบ Tab
tab1, tab2, tab3 = st.tabs(["[01. MISSION CONTROL]", "[02. DEEP QUANT LAB]", "[03. SYSTEM LOGS]"])

with tab1:
    col1, col2 = st.columns([1, 2.5])
    
    with col1:
        st.markdown("### 🎯 TARGET LOCK")
        category = st.selectbox("SELECT SECTOR", ["CRYPTO", "US_STOCKS", "TH_STOCKS"])
        if category == "CRYPTO":
            ticker = st.selectbox("SELECT ASSET", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"])
        elif category == "US_STOCKS":
            ticker = st.selectbox("SELECT ASSET", ["NVDA", "AAPL", "TSLA", "MSFT"])
        else:
            ticker = st.selectbox("SELECT ASSET", ["DELTA.BK", "PTT.BK", "CPALL.BK", "KBANK.BK"])

        if st.button("INITIATE SCAN 🔄"):
            with st.spinner("SCANNING MARKET DATA..."):
                # [ลำดับที่ 27] ดึงข้อมูลและเก็บใน Session State
                st.session_state.data = fetch_and_calc(ticker)

    with col2:
        st.markdown("### 🧠 AI ADVISOR TERMINAL")
        if "data" in st.session_state and st.session_state.data:
            d = st.session_state.data
            
            # [ลำดับที่ 3, 4] Sci-Fi HUD Data Cards
            c1, c2, c3 = st.columns(3)
            c1.metric("ASSET TARGET", d['ticker'])
            c2.metric("CURRENT PRICE", f"{d['price']:,.2f}")
            
            trend = "BULLISH 🟢" if d['price'] > d['ema200'] else "BEARISH 🔴"
            c3.metric("TREND (EMA200)", trend)
            
            c4, c5, c6 = st.columns(3)
            c4.metric("RSI (14)", f"{d['rsi']:.1f}")
            c5.metric("STOP LOSS", f"{d['sl']:,.2f}")
            c6.metric("TAKE PROFIT", f"{d['tp']:,.2f}")
            
            st.markdown("---")
            user_query = st.text_input("TRANSMIT COMMAND:", value="Requesting tactical assessment on current price action.")
            
            if st.button("⚡ EXECUTE AI DIRECTIVE"):
                if not GEMINI_API_KEY:
                    st.error("ACCESS DENIED: API KEY REQUIRED. PLEASE ENTER KEY IN THE SIDEBAR.")
                else:
                    with st.spinner("QUANT ENGINE PROCESSING..."):
                        advice = ask_veteran(d, user_query)
                        st.info(advice)
        else:
            st.warning("SYSTEM STANDBY. AWAITING TARGET SCAN.")

with tab2:
    st.markdown("### 🔬 DEEP QUANT LAB (UPCOMING)")
    st.caption("ระบบอินดิเคเตอร์เชิงลึก (RVOL, Multi-Timeframe) จะถูกติดตั้งที่นี่ในเฟสถัดไป")

with tab3:
    st.markdown("### 🗄️ DATABASE & LOGS (UPCOMING)")
    st.caption("ระบบบันทึกประวัติการเทรดและสถิติเข้า Google Sheets จะปรากฏในแท็บนี้")
