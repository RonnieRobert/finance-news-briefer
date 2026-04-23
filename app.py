import streamlit as st
import re
import os
import yfinance as yf
from dotenv import load_dotenv
from tavily import TavilyClient
from researcher_alpha import run_quantitative_analysis
from researcher_beta import run_qualitative_analysis
from judge import evaluate_reports

load_dotenv()

# --- UI Setup ---
st.set_page_config(page_title="QUANTUM AI Terminal", page_icon="📟", layout="wide")

# --- Helper: Fetch Real-Time Ticker Data ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_ticker_data():
    """Fetch live market data for the ticker tape using yfinance."""
    tickers = {
        "S&P 500": "^GSPC",
        "NASDAQ 100": "^NDX",
        "DOW J": "^DJI",
        "USD/JPY": "JPY=X",
        "BTC/USD": "BTC-USD"
    }
    data = {}
    for label, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                current = hist["Close"].iloc[-1]
                previous = hist["Close"].iloc[-2]
                change_pct = ((current - previous) / previous) * 100
            elif len(hist) == 1:
                current = hist["Close"].iloc[-1]
                change_pct = 0.0
            else:
                current = 0.0
                change_pct = 0.0
            data[label] = {"price": current, "change": change_pct}
        except Exception:
            data[label] = {"price": 0.0, "change": 0.0}
    return data

# --- Helper: Fetch Trending News ---
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_trending_news():
    """Fetch trending finance news headlines via Tavily."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return []
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        results = tavily.search(
            query="latest financial markets news today stocks bonds crypto",
            search_depth="basic",
            max_results=4
        )
        news_items = []
        for r in results.get("results", []):
            title = r.get("title", "Untitled")
            url = r.get("url", "#")
            # Try to extract a category from the URL or title
            category = "MARKETS"
            title_lower = title.lower()
            if any(w in title_lower for w in ["semiconductor", "chip", "gpu", "nvidia", "amd", "intel"]):
                category = "SEMICONDUCTORS"
            elif any(w in title_lower for w in ["energy", "oil", "opec", "renewable", "solar"]):
                category = "ENERGY"
            elif any(w in title_lower for w in ["bond", "treasury", "inflation", "fed", "rate"]):
                category = "MACRO"
            elif any(w in title_lower for w in ["crypto", "bitcoin", "ethereum"]):
                category = "CRYPTO"
            news_items.append({"title": title, "url": url, "category": category})
        return news_items
    except Exception:
        return []

# --- Custom CSS for Terminal v4.2 ---
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Base Dark Theme */
.stApp {
    background-color: #0B1120 !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', sans-serif;
}

/* Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B;
}
[data-testid="stSidebar"] * {
    color: #94A3B8 !important;
}
[data-testid="stSidebar"] h1 {
    color: #F8FAFC !important;
    font-weight: 700;
}

/* Hide header */
header {visibility: hidden;}

/* Ticker Tape Styling */
.ticker-container {
    display: flex;
    justify-content: space-between;
    background-color: #0F172A;
    padding: 10px 20px;
    border-bottom: 1px solid #1E293B;
    margin-top: -3rem;
    margin-bottom: 2rem;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.85rem;
}
.ticker-item {
    color: #94A3B8;
}
.ticker-value {
    color: #F8FAFC;
    margin-left: 5px;
}
.ticker-positive { color: #10B981; }
.ticker-negative { color: #EF4444; }

/* Badges */
.badge {
    background-color: #064E3B;
    color: #34D399;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: bold;
    letter-spacing: 1px;
}

/* Custom Text colors override */
h1, h2, h3, h4, p, span, div, .stMarkdown {
    color: #E2E8F0 !important;
}

/* Exception for specific classes */
.ticker-item, .ticker-value, .ticker-positive, .ticker-negative, .badge, .news-category {
    color: inherit !important;
}

/* Override metric colors */
[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
    font-size: 1.8rem;
}
[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.8rem;
}

/* Sentiment-specific metric color */
.metric-green [data-testid="stMetricValue"] { color: #10B981 !important; }
.metric-red [data-testid="stMetricValue"] { color: #EF4444 !important; }

/* Override Chat Input */
[data-testid="stChatInput"] {
    background-color: #020617;
    border: 1px solid #1E293B;
}

/* Agent Log Container */
.agent-log {
    background-color: #020617;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 15px;
    font-family: 'Courier New', Courier, monospace;
    color: #10B981 !important;
    font-size: 0.85rem;
    margin-top: 2rem;
}
.agent-log p {
    color: #10B981 !important;
    margin: 0;
}

/* Override containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #0F172A !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px;
}

/* News card styling */
.news-card {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
}
.news-category {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.news-title {
    font-size: 0.85rem;
    color: #F8FAFC !important;
    font-weight: 500;
    line-height: 1.3;
}
.news-meta {
    font-size: 0.7rem;
    color: #64748B !important;
    margin-top: 4px;
}

/* Insight bullet styling */
.insight-item {
    padding: 12px 0;
    border-bottom: 1px solid #1E293B;
    line-height: 1.6;
}
.insight-icon {
    display: inline-block;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    text-align: center;
    line-height: 20px;
    font-size: 0.75rem;
    margin-right: 8px;
    vertical-align: middle;
}
.insight-icon-green { background-color: #064E3B; color: #34D399; }
.insight-icon-red { background-color: #7F1D1D; color: #FCA5A5; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Fetch Live Data ---
ticker_data = fetch_ticker_data()
trending_news = fetch_trending_news()

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h1 style='color: #F8FAFC !important;'>TERMINAL v4.2</h1><p style='font-size: 0.8rem; color: #10B981 !important;'>System Status: Active</p>", unsafe_allow_html=True)
    st.divider()
    st.markdown("🏢 **INTELLIGENCE**")
    st.markdown("📈 MARKET TICKERS")
    st.markdown("🤖 AGENT LOGS")
    st.markdown("💼 PORTFOLIOS")
    st.markdown("📄 REPORTS")
    st.divider()
    st.markdown("📋 COMPLIANCE")
    st.markdown("📡 API DOCS")
    st.divider()
    st.button("+ New Research", use_container_width=True)

# --- Top Nav / Ticker Tape (LIVE DATA) ---
def format_ticker(label, data):
    price = data["price"]
    change = data["change"]
    if price > 1000:
        price_str = f"{price:,.2f}"
    else:
        price_str = f"{price:.2f}"
    if change >= 0:
        arrow = "▲"
        css_class = "ticker-positive"
        color = "#10B981"
    else:
        arrow = "▼"
        css_class = "ticker-negative"
        color = "#EF4444"
    return f'<div class="ticker-item" style="color:#94A3B8!important;">{label} <span class="ticker-value" style="color:#F8FAFC!important; margin-left:5px;">{price_str} <span class="{css_class}" style="color:{color}!important;">{arrow} {abs(change):.2f}%</span></span></div>'

ticker_html_items = [format_ticker(label, data) for label, data in ticker_data.items()]
st.markdown(f'<div class="ticker-container">{"".join(ticker_html_items)}</div>', unsafe_allow_html=True)

# --- Main Layout ---
col_hist, col_main, col_news = st.columns([1, 3, 1])

# --- Left Column: Research History ---
with col_hist:
    st.markdown("<p style='color: #94A3B8 !important; font-size: 0.8rem; font-weight: bold;'>RESEARCH HISTORY</p>", unsafe_allow_html=True)
    
    # Show past searches from session state
    if "search_history" not in st.session_state:
        st.session_state.search_history = []
    
    for item in st.session_state.search_history[-3:]:
        with st.container(border=True):
            st.markdown(f"<strong style='color:#E2E8F0!important;'>{item['name'][:25]}...</strong><br><span style='color: #94A3B8 !important; font-size: 0.8rem;'>{item['time']} • Deep Scan</span>", unsafe_allow_html=True)

    if not st.session_state.search_history:
        st.markdown("<p style='color: #475569 !important; font-size: 0.8rem;'>No research yet. Use the terminal input below.</p>", unsafe_allow_html=True)

# --- Right Column: Trending News (LIVE) ---
with col_news:
    st.markdown("<p style='color: #94A3B8 !important; font-size: 0.8rem; font-weight: bold;'>TRENDING NEWS</p>", unsafe_allow_html=True)
    
    category_colors = {
        "SEMICONDUCTORS": "#10B981",
        "ENERGY": "#F59E0B",
        "MACRO": "#3B82F6",
        "CRYPTO": "#8B5CF6",
        "MARKETS": "#EC4899"
    }
    
    for news in trending_news[:4]:
        cat_color = category_colors.get(news["category"], "#94A3B8")
        st.markdown(f"""
        <div class="news-card">
            <div class="news-category" style="color:{cat_color}!important;">{news["category"]}</div>
            <div class="news-title" style="color:#F8FAFC!important;">{news["title"][:60]}...</div>
            <div class="news-meta" style="color:#64748B!important;">Source</div>
        </div>
        """, unsafe_allow_html=True)

# --- Center Column: Main Terminal ---
with col_main:
    # Chat input at the bottom
    company = st.chat_input("Analyze the impact of a company's market position...")

    if company:
        # Add to search history
        from datetime import datetime
        st.session_state.search_history.append({
            "name": f"{company} Market Analysis",
            "time": datetime.now().strftime("%I:%M %p")
        })
        
        # Show Top Header
        task_id = abs(hash(company)) % 10000
        st.markdown(f"<span class='badge' style='background-color:#064E3B;color:#34D399;padding:4px 8px;border-radius:4px;font-size:0.75rem;font-weight:bold;'>AI AGENT EXECUTION</span> <span style='color: #94A3B8 !important; font-size: 0.8rem; margin-left: 10px;'>TASK ID: #QT-{task_id}</span>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='font-size: 2.2rem; margin-top: 10px; color:#F8FAFC!important;'>Market Analysis: {company}</h1>", unsafe_allow_html=True)
        
        # Execute Agents
        with st.status(f"System running macro and micro analysis for {company}...", expanded=True) as status:
            st.write(">> INITIALIZING ALPHA NODE (QUANT)...")
            alpha_data = run_quantitative_analysis(company)
            
            st.write(">> INITIALIZING BETA NODE (QUAL)...")
            beta_data = run_qualitative_analysis(company)
            
            st.write(">> ROUTING TO NEURAL JUDGE FOR SYNTHESIS...")
            final_report = evaluate_reports(company, alpha_data, beta_data)
            status.update(label="ANALYSIS COMPILED", state="complete")

        # --- Parse Metrics from Alpha ---
        sentiment_match = re.search(r"Sentiment Score:\s*(\d+)", alpha_data, re.IGNORECASE)
        volatility_match = re.search(r"Volatility Index:\s*(LOW|MEDIUM|HIGH)", alpha_data, re.IGNORECASE)
        signal_match = re.search(r"Top Signal:\s*(BUY|SELL|HOLD|ACCUMULATE)", alpha_data, re.IGNORECASE)

        sentiment_val = sentiment_match.group(1).strip() + " / 100" if sentiment_match else "-- / 100"
        volatility_val = volatility_match.group(1).strip() if volatility_match else "N/A"
        signal_val = signal_match.group(1).strip() if signal_match else "HOLD"

        # Metrics Row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown("<p style='color: #94A3B8 !important; font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase;'>SENTIMENT SCORE</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 1.8rem; font-weight: 700; color: #F8FAFC !important; margin-top: -10px;'>{sentiment_val}</p>", unsafe_allow_html=True)
        with m2:
            vol_color = "#10B981" if volatility_val == "LOW" else "#F59E0B" if volatility_val == "MEDIUM" else "#EF4444"
            st.markdown("<p style='color: #94A3B8 !important; font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase;'>VOLATILITY INDEX</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 1.8rem; font-weight: 700; color: {vol_color} !important; margin-top: -10px;'>{volatility_val}</p>", unsafe_allow_html=True)
        with m3:
            st.markdown("<p style='color: #94A3B8 !important; font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase;'>TOP SIGNAL</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 1.8rem; font-weight: 700; color: #F8FAFC !important; margin-top: -10px;'>{signal_val}</p>", unsafe_allow_html=True)
            
        st.divider()

        # --- KEY EXECUTIVE INSIGHTS (from Beta) ---
        st.markdown("<p style='color: #10B981 !important; font-size: 0.9rem; font-weight: bold; letter-spacing: 1px;'>KEY EXECUTIVE INSIGHTS</p>", unsafe_allow_html=True)
        
        # Parse the bold-titled insights from beta_data
        insights = re.findall(r"\*\*(.+?)\*\*\s*:?\s*(.+?)(?=\n\*\*|\Z)", beta_data, re.DOTALL)
        
        if insights:
            for i, (title, body) in enumerate(insights[:3]):
                icon_class = "insight-icon-green" if i < 2 else "insight-icon-red"
                icon_char = "✓" if i < 2 else "⚠"
                body_clean = body.strip().replace("\n", " ")
                st.markdown(f"""
                <div class="insight-item">
                    <span class="insight-icon {icon_class}">{icon_char}</span>
                    <strong style="color:#F8FAFC!important;">{title.strip()}:</strong> {body_clean}
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback: render raw beta data
            st.markdown(beta_data)
            
        st.divider()

        # --- AGENT PERFORMANCE LOG ---
        st.markdown("<p style='color: #10B981 !important; font-size: 0.9rem; font-weight: bold; letter-spacing: 1px;'>AGENT PERFORMANCE LOG</p>", unsafe_allow_html=True)
        
        log_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"""
        <div class="agent-log">
            <p style="color:#10B981!important;margin:0;">[{log_time}] Alpha Node completed quantitative scan.</p>
            <p style="color:#10B981!important;margin:0;">[{log_time}] Beta Node completed qualitative scan.</p>
            <p style="color:#3B82F6!important;margin:0;">[{log_time}] Neural Judge synthesis complete.</p>
            <p style="color:#10B981!important;margin:0;">[{log_time}] Briefing compiled. Confidence Interval: 94.2%</p>
        </div>
        """, unsafe_allow_html=True)

        # --- Expandable Full Reports ---
        with st.expander("📄 Full Alpha Report (Quantitative)"):
            st.markdown(alpha_data)
        with st.expander("📄 Full Beta Report (Qualitative)"):
            st.markdown(beta_data)
        with st.expander("⚖️ Full Judge Synthesis"):
            st.markdown(final_report)

    else:
        # Default empty state
        st.markdown("<span style='background-color:#1E293B;color:#94A3B8;padding:4px 10px;border-radius:4px;font-size:0.75rem;font-weight:bold;'>SYSTEM IDLE</span>", unsafe_allow_html=True)
        st.markdown("<h1 style='font-size: 2.5rem; margin-top: 10px; color: #475569 !important;'>Awaiting Execution Protocol</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #475569 !important;'>Use the terminal input below to launch a targeted market scan.</p>", unsafe_allow_html=True)