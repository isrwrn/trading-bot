import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. SYSTEM CONFIG
# ==========================================
st.set_page_config(page_title="TOOLNOVA | Quant Terminal", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. ULTRA-CRISP DARK UI CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600&family=Noto+Serif+Thai:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap');

    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    [data-testid="stAppViewContainer"], .stApp { background-color: #05080F !important; }
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    html, body, p, div, span {
        font-family: 'Noto Sans Thai', sans-serif;
        color: #94A3B8;
    }

    .crisp-card {
        background-color: #0B101A;
        border: 1px solid #1E293B;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: none; 
        transition: border 0.2s ease;
    }
    .crisp-card:hover { border: 1px solid #3B82F6; }
    
    .accent-blue { border-top: 2px solid #00F0FF; }
    .accent-purple { border-top: 2px solid #9D4EDD; }
    .accent-red { border-top: 2px solid #FF3366; }
    .accent-yellow { border-top: 2px solid #F59E0B; }

    .data-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #64748B;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .data-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.2;
    }
    .data-value-small {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .data-sub { font-size: 0.85rem; margin-top: 6px; font-weight: 500; }
    
    .text-cyan { color: #00F0FF; }
    .text-green { color: #10B981; }
    .text-red { color: #EF4444; }
    .text-purple { color: #9D4EDD; }
    .text-yellow { color: #F59E0B; }
    
    .ai-content {
        font-family: 'Noto Serif Thai', serif;
        font-size: 1rem;
        line-height: 1.7;
        color: #F8FAFC;
    }

    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stNumberInput > div > div > input {
        background-color: #05080F !important;
        border: 1px solid #1E293B !important;
        color: #00F0FF !important;
        border-radius: 4px !important;
        padding: 8px 12px !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border: 1px solid #00F0FF !important;
    }
    
    .stButton > button {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
        padding: 12px !important;
        font-weight: 600 !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton > button:hover {
        background-color: #00F0FF !important;
        color: #000000 !important;
        border: 1px solid #00F0FF !important;
    }

    label[data-testid="stWidgetLabel"] { display: none; }
    div[data-testid="stSidebar"] {
        background-color: #080C14 !important;
        border-right: 1px solid #1E293B !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CORE LOGIC & QUANT CALCULATIONS
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
        v = data['Volume'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Volume']

        ema200 = c.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = c.diff()
        rsi = (100 - (100 / (1 + ((delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean())))).iloc[-1]
        atr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
        
        # ป้องกันกรณีกราฟสั้นเกินไปจนคำนวณ Volume เฉลี่ยไม่ได้
        avg_vol = v.rolling(20).mean().iloc[-1] if len(v) >= 20 else v.mean()
        rvol = v.iloc[-1] / avg_vol if avg_vol > 0 else 1.0
        
        last = c.iloc[-1]
        
        # คำนวณ Confidence Score (0-100)
        score = 50
        if last > ema200: score += 20
        if 40 <= rsi <= 60: score += 10
        elif rsi < 30: score += 20
        if rvol > 1.2: score += 10
        
        return {
            "ticker": ticker, "price": float(last), "ema200": float(ema200),
            "rsi": float(rsi), "atr": float(atr), "rvol": float(rvol), "score": int(min(score, 99)),
            "sl": float(last - (1.5 * atr)), "tp": float(last + (3.0 * atr))
        }
    except Exception as e: 
        return None

def analyze_with_ai(data, prompt_text, api_key, risk_data):
    genai.configure(api_key=api_key)
    sys_prompt = f"""
    คุณคือ AI วิเคราะห์การลงทุนระดับองค์กร 
    ข้อมูลตลาด: {data['ticker']}, ราคา {data['price']:.2f}, EMA200 {data['ema200']:.2f}, RSI {data['rsi']:.1f}, Confidence {data['score']}%
    ข้อมูล Risk Management: ทุน {risk_data['capital']}, เสี่ยงได้ {risk_data['risk_amount']}, แนะนำเข้าซื้อ {risk_data['position_size']} หน่วย
    
    ตอบคำถามผู้ใช้ด้วยความเฉียบขาด กระชับ ใช้ภาษาไทย
    เน้นคำตอบเป็น Bullet และทำตัวหนาในตัวเลข/แอคชั่นสำคัญเสมอ
    คำถาม: {prompt_text}
    """
    try:
        model = genai.GenerativeModel("gemini-3.8-flash") 
        return model.generate_content(sys_prompt).text
    except Exception as e: return f"⚠️ **เกิดข้อผิดพลาด:** {str(e)}"

# ==========================================
# 4. SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #FFFFFF; font-family: Space Grotesk;'>TOOLNOVA</h2>", unsafe_allow_html=True)
    st.markdown("<div class='data-label'>SYSTEM CONTROL</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 20px; color: #64748B; font-size: 0.75rem; font-weight: 600;'>API KEY (GEMINI)</div>", unsafe_allow_html=True)
    api_key = st.text_input("API KEY", type="password", placeholder="Enter API Key...")
    
    st.markdown("<div style='margin-top: 20px; color: #64748B; font-size: 0.75rem; font-weight: 600;'>TARGET ASSET</div>", unsafe_allow_html=True)
    ticker = st.selectbox("TICKER", ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "AAPL", "DELTA.BK", "PTT.BK"])
    
    st.markdown("---")
    st.markdown("<div class='data-label'>RISK PARAMETERS</div>", unsafe_allow_html=True)
    st.markdown("<div style='color: #64748B; font-size: 0.75rem; font-weight: 600;'>PORTFOLIO CAPITAL ($/฿)</div>", unsafe_allow_html=True)
    capital = st.number_input("CAPITAL", min_value=100, value=10000, step=1000)
    
    st.markdown("<div style='margin-top: 10px; color: #64748B; font-size: 0.75rem; font-weight: 600;'>RISK PER TRADE (%)</div>", unsafe_allow_html=True)
    risk_pct = st.number_input("RISK", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
    
    st.write("")
    if st.button("RUN DIAGNOSTIC"):
        with st.spinner("SCANNING DATA & CALCULATING RISK..."):
            st.session_state.market_data = scan_market(ticker)
            st.session_state.ai_response = None

# ==========================================
# 5. MAIN DASHBOARD LAYOUT
# ==========================================
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 25px;">
    <div>
        <div class="data-label">AI AGENT WORKFLOWS</div>
        <div style="font-size: 1.6rem; color: #FFF; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">Autonomous Execution System</div>
    </div>
    <div style="text-align: right;">
        <div class="data-label">SYSTEM TIME</div>
        <div style="color: #00F0FF; font-family: 'Space Grotesk'; font-size: 1.1rem;">{datetime.now().strftime('%H:%M:%S UTC')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# เช็กความพร้อมของข้อมูลว่ามีคีย์ครบถ้วนหรือไม่ ป้องกัน KeyError
if st.session_state.market_data and isinstance(st.session_state.market_data, dict) and 'score' in st.session_state.market_data:
    d = st.session_state.market_data
    is_bullish = d['price'] > d['ema200']
    
    # คำนวณ Position Sizing (Risk Management)
    risk_amount = capital * (risk_pct / 100)
    stop_distance = abs(d['price'] - d['sl'])
    position_size = risk_amount / stop_distance if stop_distance > 0 else 0
    total_position_value = position_size * d['price']
    
    risk_data = {
        "capital": capital,
        "risk_amount": risk_amount,
        "position_size": position_size
    }
    
    # ------------------------------------------
    # แถวที่ 1: MARKET METRICS 
    # ------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="crisp-card accent-blue">
            <div class="data-label">ASSET PRICE ({d['ticker']})</div>
            <div class="data-value">{d['price']:,.2f}</div>
            <div class="data-sub {'text-green' if is_bullish else 'text-red'}">■ TREND: {'BULLISH' if is_bullish else 'BEARISH'}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="crisp-card">
            <div class="data-label">SYSTEM CONFIDENCE</div>
            <div class="data-value">{d['score']}%</div>
            <div class="data-sub text-cyan">■ RVOL: {d['rvol']:.2f}x</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="crisp-card accent-red">
            <div class="data-label">STOP LOSS (SL)</div>
            <div class="data-value">{d['sl']:,.2f}</div>
            <div class="data-sub text-red">1.5 ATR Distance</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="crisp-card accent-purple">
            <div class="data-label">TAKE PROFIT (TP)</div>
            <div class="data-value">{d['tp']:,.2f}</div>
            <div class="data-sub text-purple">3.0 ATR Distance</div>
        </div>
        """, unsafe_allow_html=True)

    # ------------------------------------------
    # แถวที่ 2: RISK MANAGEMENT & AI EXECUTION
    # ------------------------------------------
    col_risk, col_ai = st.columns([1, 2])
    
    with col_risk:
        st.markdown(f"""
        <div class="crisp-card accent-yellow" style="height: 100%; min-height: 350px;">
            <div class="data-label" style="margin-bottom: 20px;">CAPITAL & RISK SIZING</div>
            
            <div style="margin-bottom: 20px;">
                <div class="data-label">CAPITAL AT RISK ({risk_pct}%)</div>
                <div class="data-value-small text-yellow">{risk_amount:,.2f}</div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div class="data-label">RECOMMENDED POSITION SIZE</div>
                <div class="data-value-small text-cyan">{position_size:,.4f} <span style="font-size:1rem;">Units</span></div>
            </div>
            
            <div style="margin-bottom: 20px; border-top: 1px solid #1E293B; padding-top: 15px;">
                <div class="data-label">TOTAL POSITION VALUE</div>
                <div class="data-value-small">{total_position_value:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_ai:
        st.markdown("""
        <div class="crisp-card" style="height: 100%; min-height: 350px;">
            <div class="data-label" style="margin-bottom: 15px;">AI INSIGHTX EXECUTION MODULE</div>
        """, unsafe_allow_html=True)
        
        user_q = st.text_input("QUERY", placeholder="สั่งการ AI... (เช่น สรุปความคุ้มค่าของ Risk:Reward ให้หน่อย)")
        if st.button("EXECUTE TASK"):
            if not api_key: st.error("Missing API Key in the sidebar.")
            else:
                with st.spinner("Processing Logic..."):
                    st.session_state.ai_response = analyze_with_ai(d, user_q, api_key, risk_data)
        
        if st.session_state.ai_response:
            st.markdown(f"""
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px dashed #334155;">
                <div class="data-label" style="color: #00F0FF; margin-bottom: 10px;">ANALYSIS OUTPUT</div>
                <div class="ai-content">{st.session_state.ai_response}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # เคลียร์ค่า state ที่พังทิ้งอัตโนมัติหากพบข้อผิดพลาด
    st.session_state.market_data = None
    st.markdown("""
    <div class="crisp-card" style="text-align: center; padding: 120px 20px;">
        <div style="font-size: 3rem; margin-bottom: 20px; color: #334155;">🛡️</div>
        <div class="data-value" style="color: #64748B;">SYSTEM IDLE</div>
        <div style="color: #475569; margin-top: 10px; font-weight: 500;">Please configure API and click 'RUN DIAGNOSTIC' from the sidebar.</div>
    </div>
    """, unsafe_allow_html=True)
