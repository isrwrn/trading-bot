import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai

# ==========================================
# 1. ตั้งค่าหน้าเว็บให้เต็มจอและสะอาดตา
# ==========================================
st.set_page_config(page_title="Veteran Quant Advisor", layout="wide", page_icon="🏛️")

# ==========================================
# 2. Premium UX/UI CSS (Smooth & Clean)
# ==========================================
st.markdown("""
<style>
    /* นำเข้าฟอนต์ Inter ที่เน้นความสะอาดตาและอ่านง่าย */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* ปรับแต่งกล่อง Metric (ตัวเลข) ให้เป็น Card ขอบมนสบายตา */
    div[data-testid="metric-container"] {
        background-color: #1a1c24 !important; /* สีพื้นหลัง Card โทนพรีเมียม */
        border: 1px solid #2b2d36 !important;
        padding: 15px 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px); /* เอฟเฟกต์ยกตัวเมื่อเอาเมาส์ชี้ */
        border: 1px solid #3d404d !important;
    }
    
    /* ปรับแต่งปุ่มกด (Psychological Action) */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        background-color: #262730 !important;
        transition: all 0.2s ease-in-out !important;
        padding: 10px 24px !important;
    }
    .stButton > button:hover {
        background-color: #3b3c46 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        transform: scale(1.02); /* ขยายเล็กน้อยดึงดูดการกด */
    }
    
    /* ปุ่ม Primary Action (ขอคำแนะนำ) เน้นสีให้แตกต่าง */
    div:nth-child(2) > div > button {
        background-color: #0068c9 !important; /* สีน้ำเงิน Trust & Security */
        color: white !important;
    }
    div:nth-child(2) > div > button:hover {
        background-color: #0052a3 !important;
    }
    
    /* ปรับแต่ง Input Fields ให้ขอบมน */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        border-radius: 8px !important;
    }
    
    /* เส้นคั่นบางๆ สบายตา */
    hr {
        border-color: #2b2d36 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. จัดการ Data & API แบบซ่อนรูปและมีประสิทธิภาพ
# ==========================================
st.sidebar.markdown("### ⚙️ Settings")
GEMINI_API_KEY = st.sidebar.text_input("Gemini API Key", type="password", placeholder="Enter your key here...")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
st.sidebar.caption("Your API key is masked and secured locally.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_and_calc(ticker: str):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or len(data) < 50: return None
        
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
            "ticker": ticker, "price": float(last_price), "ema200": float(ema200),
            "rsi": float(rsi), "atr": float(atr), 
            "sl": float(last_price - (1.5 * atr)), "tp": float(last_price + (3.0 * atr))
        }
    except:
        return None

def ask_veteran(market_data: dict, user_intent: str):
    prompt = f"""
    You are a Senior Quant Trader (25 yrs experience). Be precise, professional, and strictly manage risk.
    Asset: {market_data['ticker']} | Price: {market_data['price']:.2f}
    EMA200: {market_data['ema200']:.2f} | RSI: {market_data['rsi']:.2f} | ATR: {market_data['atr']:.2f}
    SL: {market_data['sl']:.2f} | TP: {market_data['tp']:.2f}
    
    User request: "{user_intent}"
    
    Answer in Thai with a professional tone:
    1. Verdict: (Buy / Sell / Wait)
    2. Quantitative Analysis: (Briefly explain based on numbers)
    3. Next Action: (Clear, actionable step)
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(prompt).text
    except Exception as e:
        return f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {str(e)}"

# ==========================================
# 4. ออกแบบโครงสร้างหน้าจอ (Information Architecture)
# ==========================================
st.title("🏛️ Veteran Precision Advisor")
st.markdown("ระบบผู้ช่วยวิเคราะห์และจัดการความเสี่ยงเชิงปริมาณ (Quantitative Analysis)")
st.markdown("---")

# แบ่งสัดส่วนหน้าจอแบบ 30% : 70% ให้จุดสนใจอยู่ที่ผลวิเคราะห์
col_input, col_dashboard = st.columns([1, 2.5])

with col_input:
    st.subheader("1. Asset Selection")
    category = st.selectbox("Market", ["Crypto", "US Stocks", "Thai Stocks (SET)"])
    if category == "Crypto":
        ticker = st.selectbox("Symbol", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"])
    elif category == "US Stocks":
        ticker = st.selectbox("Symbol", ["NVDA", "AAPL", "TSLA", "MSFT"])
    else:
        ticker = st.selectbox("Symbol", ["DELTA.BK", "PTT.BK", "CPALL.BK", "KBANK.BK"])

    st.write("") # เว้นบรรทัดให้หายใจ
    if st.button("Load Market Data", use_container_width=True):
        with st.spinner("Fetching live data..."):
            st.session_state.data = fetch_and_calc(ticker)

with col_dashboard:
    st.subheader("2. Market Overview")
    if "data" in st.session_state and st.session_state.data:
        d = st.session_state.data
        
        # จัดเรียงตัวเลขสำคัญให้อ่านง่าย (Z-Pattern)
        m1, m2, m3 = st.columns(3)
        m1.metric("Last Price", f"{d['price']:,.2f}")
        trend = "BULLISH" if d['price'] > d['ema200'] else "BEARISH"
        m2.metric("Trend (EMA 200)", trend, delta="Above" if trend == "BULLISH" else "Below", delta_color="normal" if trend == "BULLISH" else "inverse")
        m3.metric("RSI (14)", f"{d['rsi']:.1f}")
        
        st.write("")
        m4, m5, m6 = st.columns(3)
        m4.metric("Volatility (ATR)", f"{d['atr']:.2f}")
        m5.metric("Target Stop Loss", f"{d['sl']:,.2f}")
        m6.metric("Target Take Profit", f"{d['tp']:,.2f}")
        
        st.markdown("---")
        st.subheader("3. Strategic Execution")
        user_query = st.text_input("Your inquiry or strategy:", value="ประเมินความเสี่ยงและจุดเข้าซื้อ ณ ราคาปัจจุบันให้หน่อย")
        
        # ปุ่มที่สองนี้ CSS จะบังคับให้เป็นสีน้ำเงิน (Primary Call to Action)
        if st.button("✨ Get Professional Advice", use_container_width=True):
            if not GEMINI_API_KEY:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                with st.spinner("Analyzing quantitative data..."):
                    advice = ask_veteran(d, user_query)
                    st.success("Analysis Complete")
                    st.markdown(f"> {advice}")
    else:
        # State ว่างเปล่าที่ดูสุภาพ
        st.info("👈 Please select an asset and load market data to begin analysis.")
