import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai

st.set_page_config(page_title="Veteran Precision Advisor", layout="wide")

GEMINI_API_KEY = st.sidebar.text_input("Enter Gemini API Key", type="password")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def fetch_and_calc(ticker: str):
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

def ask_veteran(market_data: dict, user_intent: str):
    prompt = f"""
    คุณคือหัวหน้านักกลยุทธ์การลงทุนอาวุโส (Senior Quant Trader) ประสบการณ์ 25 ปีในวอลล์สตรีทและตลาดเกิดใหม่
    บุคลิกของคุณ: เฉียบคม ดุดัน มีวินัยสูง ไม่ยอมรับความเสี่ยงโง่เขลา ถ้าสัญญาณไม่สมบูรณ์แบบ 100% คุณจะปฏิเสธการเทรดทันที

    ข้อมูลตลาดจริงปัจจุบันของ {market_data['ticker']}:
    - ราคาล่าสุด: {market_data['price']:.2f}
    - เส้น EMA 200 วัน (แนวโน้มใหญ่): {market_data['ema200']:.2f}
    - RSI (14): {market_data['rsi']:.2f}
    - ความผันผวน ATR: {market_data['atr']:.2f}
    - คำนวณ SL (1.5 ATR): {market_data['sl']:.2f}
    - คำนวณ TP (3.0 ATR): {market_data['tp']:.2f} (R:R 1:2)

    คำถามหรือคำสั่งของเทรดเดอร์: "{user_intent}"

    จงตอบในฐานะที่ปรึกษาอาวุโส:
    1. คำตัดสินเด็ดขาด: [BUY / SELL / WAIT (ห้ามเข้า)]
    2. เหตุผลเชิงตัวเลขและจิตวิทยาตลาด (อ้างอิงข้อมูลข้างต้นเท่านั้น ห้ามเดา)
    3. แผน Action ที่ต้องทำทันที พร้อมจุดเสี่ยงที่ต้องระวัง
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

st.title("🏛️ Veteran Precision Advisor (25 Years Exp.)")
st.caption("ระบบวิเคราะห์และสั่งการเทรดระดับสถาบัน: หุ้นไทย | หุ้นนอก | คริปโต")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📌 เลือกสินทรัพย์")
    category = st.selectbox("ตลาด", ["คริปโต (Crypto)", "หุ้นนอก (US)", "หุ้นไทย (SET)"])
    if category == "คริปโต (Crypto)":
        ticker = st.selectbox("เหรียญ", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"])
    elif category == "หุ้นนอก (US)":
        ticker = st.selectbox("หุ้น", ["NVDA", "AAPL", "TSLA", "MSFT"])
    else:
        ticker = st.selectbox("หุ้นไทย", ["DELTA.BK", "PTT.BK", "CPALL.BK", "KBANK.BK"])

    if st.button("🔄 โหลดข้อมูลตลาดจริง"):
        with st.spinner("คำนวณข้อมูลระดับ Quant..."):
            st.session_state.data = fetch_and_calc(ticker)

with col2:
    st.subheader("💡 คำปรึกษา & ประเมินการสั่งงาน")
    if "data" in st.session_state and st.session_state.data:
        d = st.session_state.data
        st.markdown(f"**สินทรัพย์:** `{d['ticker']}` | **ราคา:** `{d['price']:,.2f}` | **RSI:** `{d['rsi']:.1f}` | **EMA200:** `{d['ema200']:,.2f}`")
        st.markdown(f"**เป้าหมาย R:R 1:2:** Stop Loss: `{d['sl']:,.2f}` | Take Profit: `{d['tp']:,.2f}`")

        user_query = st.text_input("สั่งการหรือถามที่ปรึกษา:", value="จังหวะนี้ควรเปิดสถานะหรือไม่?")
        if st.button("⚡ ขอคำแนะนำเด็ดขาด"):
            if not GEMINI_API_KEY:
                st.error("กรุณากรอก Gemini API Key ในแถบด้านซ้ายก่อนใช้งาน")
            else:
                with st.spinner("ที่ปรึกษาอาวุโสกำลังประเมินความเสี่ยง..."):
                    advice = ask_veteran(d, user_query)
                    st.markdown("---")
                    st.markdown(advice)
    else:
        st.info("กรุณากดปุ่มโหลดข้อมูลตลาดเพื่อเริ่มต้นวิเคราะห์")
