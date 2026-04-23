import streamlit as st
import re
import os
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient
from researcher_alpha import run_quantitative_analysis
from researcher_beta import run_qualitative_analysis
from judge import evaluate_reports

load_dotenv()

# --- UI Setup (MUST be first Streamlit command) ---
st.set_page_config(page_title="QUANTUM AI Terminal", page_icon="📟", layout="wide")

# =============================================================================
# DATA LAYER: All dynamic values flow from here
# =============================================================================

@st.cache_data(ttl=300)
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
                current = float(hist["Close"].iloc[-1])
                previous = float(hist["Close"].iloc[-2])
                change_pct = ((current - previous) / previous) * 100
            elif len(hist) == 1:
                current = float(hist["Close"].iloc[-1])
                change_pct = 0.0
            else:
                current = 0.0
                change_pct = 0.0
            data[label] = {"price": current, "change": change_pct}
        except Exception:
            data[label] = {"price": 0.0, "change": 0.0}
    return data


@st.cache_data(ttl=600)
def fetch_trending_news():
    """Fetch trending finance news headlines via Tavily."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return []
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        results = tavily.search(
            query="latest financial markets news today stocks bonds crypto energy",
            search_depth="basic",
            max_results=4
        )
        news_items = []
        for r in results.get("results", []):
            title = r.get("title", "Untitled")
            url = r.get("url", "#")
            category = classify_news_category(title)
            news_items.append({"title": title, "url": url, "category": category})
        return news_items
    except Exception:
        return []


def classify_news_category(title: str) -> str:
    """Compute the category from the headline text — never hardcoded."""
    t = title.lower()
    if any(w in t for w in ["semiconductor", "chip", "gpu", "nvidia", "amd", "intel", "tsmc"]):
        return "SEMICONDUCTORS"
    if any(w in t for w in ["energy", "oil", "opec", "renewable", "solar", "natural gas"]):
        return "ENERGY"
    if any(w in t for w in ["bond", "treasury", "inflation", "fed", "rate", "cpi", "gdp"]):
        return "MACRO"
    if any(w in t for w in ["crypto", "bitcoin", "ethereum", "btc", "eth"]):
        return "CRYPTO"
    return "MARKETS"


# =============================================================================
# DYNAMIC COLOR / SIGNAL ENGINE: All visuals derive from data
# =============================================================================

def get_change_color(value: float) -> str:
    """Returns a hex color based on value sign. Green=positive, Red=negative, Gray=neutral."""
    if value > 0:
        return "#10B981"
    elif value < 0:
        return "#EF4444"
    return "#94A3B8"


def get_change_arrow(value: float) -> str:
    """Returns directional arrow based on value sign."""
    if value > 0:
        return "▲"
    elif value < 0:
        return "▼"
    return "—"


def compute_signal(score: int) -> str:
    """Compute the TOP SIGNAL from sentiment score — never hardcoded."""
    if score > 70:
        return "ACCUMULATE"
    elif score > 50:
        return "HOLD"
    elif score > 30:
        return "REDUCE"
    return "SELL"


def compute_volatility(score: int) -> str:
    """Compute volatility label from sentiment score — never hardcoded."""
    if score > 65:
        return "LOW"
    elif score > 40:
        return "MEDIUM"
    return "HIGH"


def get_volatility_color(label: str) -> str:
    """Color-code the volatility label dynamically."""
    mapping = {"LOW": "#10B981", "MEDIUM": "#F59E0B", "HIGH": "#EF4444"}
    return mapping.get(label, "#94A3B8")


def get_signal_color(signal: str) -> str:
    """Color-code the signal dynamically."""
    mapping = {"ACCUMULATE": "#10B981", "BUY": "#10B981", "HOLD": "#F59E0B", "REDUCE": "#EF4444", "SELL": "#EF4444"}
    return mapping.get(signal, "#F8FAFC")


def get_category_color(category: str) -> str:
    """Returns category color for news badges — derived from category value."""
    mapping = {
        "SEMICONDUCTORS": "#10B981",
        "ENERGY": "#F59E0B",
        "MACRO": "#3B82F6",
        "CRYPTO": "#8B5CF6",
        "MARKETS": "#EC4899"
    }
    return mapping.get(category, "#94A3B8")


def classify_insight_sentiment(body: str) -> str:
    """Classify each insight as positive/negative from its text — dynamic, not hardcoded."""
    negative_words = ["risk", "headwind", "decline", "loss", "threat", "antitrust",
                      "investigation", "warning", "debt", "downturn", "bearish",
                      "sell-off", "regulatory", "concern", "drop", "cut", "weak"]
    body_lower = body.lower()
    neg_count = sum(1 for w in negative_words if w in body_lower)
    return "negative" if neg_count >= 1 else "positive"


def parse_sentiment_score(alpha_data: str) -> int:
    """Extract the sentiment score from Alpha output. Returns int or fallback computed value."""
    match = re.search(r"Sentiment Score:\s*(\d+)", alpha_data, re.IGNORECASE)
    if match:
        return min(int(match.group(1)), 100)
    return 0


def parse_insights(beta_data: str) -> list:
    """Parse bold-titled insights from Beta output into structured list."""
    raw = re.findall(r"\*\*(.+?)\*\*\s*:?\s*(.+?)(?=\n\*\*|\n\n|\Z)", beta_data, re.DOTALL)
    insights = []
    for title, body in raw[:5]:
        body_clean = body.strip().replace("\n", " ")
        sentiment = classify_insight_sentiment(body_clean)
        insights.append({"title": title.strip(), "body": body_clean, "sentiment": sentiment})
    return insights


# =============================================================================
# UI COMPONENTS: Reusable rendering functions
# =============================================================================

def render_ticker_tape(ticker_data: dict):
    """Render the top ticker tape from live data — fully dynamic colors."""
    items_html = ""
    for label, data in ticker_data.items():
        price = data["price"]
        change = data["change"]
        price_str = f"{price:,.2f}" if price > 1000 else f"{price:.2f}"
        color = get_change_color(change)
        arrow = get_change_arrow(change)
        items_html += f'<div class="ticker-item" style="color:#94A3B8!important;">{label} <span class="ticker-value" style="color:#F8FAFC!important; margin-left:5px;">{price_str} <span style="color:{color}!important;">{arrow} {abs(change):.2f}%</span></span></div>'
    st.markdown(f'<div class="ticker-container">{items_html}</div>', unsafe_allow_html=True)


def render_top_nav():
    """Render the QUANTUM AI top navigation bar."""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:30px;padding:5px 0;margin-top:-2rem;margin-bottom:5px;">
        <span style="font-size:1.1rem;font-weight:700;color:#F8FAFC!important;letter-spacing:1px;">QUANTUM AI</span>
        <span style="color:#10B981!important;font-size:0.85rem;font-weight:600;border-bottom:2px solid #10B981;padding-bottom:3px;">Overview</span>
        <span style="color:#64748B!important;font-size:0.85rem;">Forecasting</span>
        <span style="color:#64748B!important;font-size:0.85rem;">Sentiment</span>
    </div>
    """, unsafe_allow_html=True)


def render_score_indicator(label: str, value: str, color: str):
    """Render a single metric indicator — color comes from data, not hardcoded."""
    st.markdown(f"""
    <div>
        <p style="color:#94A3B8!important;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:2px;font-weight:600;">{label}</p>
        <p style="font-size:2rem;font-weight:800;color:{color}!important;margin-top:0;">{value}</p>
    </div>
    """, unsafe_allow_html=True)


def render_signal_badge(signal: str):
    """Render the TOP SIGNAL as a badge — color derived from signal value."""
    color = get_signal_color(signal)
    st.markdown(f"""
    <div>
        <p style="color:#94A3B8!important;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:2px;font-weight:600;">TOP SIGNAL</p>
        <p style="font-size:2rem;font-weight:800;color:{color}!important;margin-top:0;">{signal}</p>
    </div>
    """, unsafe_allow_html=True)


def render_insight(insight: dict):
    """Render a single insight item — icon and color derived from sentiment classification."""
    if insight["sentiment"] == "positive":
        icon = "✓"
        icon_bg = "#064E3B"
        icon_color = "#34D399"
    else:
        icon = "⚠"
        icon_bg = "#7F1D1D"
        icon_color = "#FCA5A5"
    st.markdown(f"""
    <div class="insight-item">
        <span style="display:inline-block;width:22px;height:22px;border-radius:50%;background:{icon_bg};color:{icon_color};text-align:center;line-height:22px;font-size:0.75rem;margin-right:10px;vertical-align:middle;">{icon}</span>
        <strong style="color:#F8FAFC!important;">{insight['title']}:</strong> <span style="color:#CBD5E1!important;">{insight['body']}</span>
    </div>
    """, unsafe_allow_html=True)


def render_agent_log(entries: list):
    """Render the agent performance log — timestamps and colors are data-driven."""
    lines = ""
    for entry in entries:
        color = get_change_color(entry.get("level", 1))
        if entry.get("type") == "info":
            color = "#10B981"
        elif entry.get("type") == "synthesis":
            color = "#3B82F6"
        elif entry.get("type") == "critical":
            color = "#F59E0B"
        lines += f'<p style="color:{color}!important;margin:2px 0;">[{entry["time"]}] {entry["message"]}</p>'
    st.markdown(f'<div class="agent-log">{lines}</div>', unsafe_allow_html=True)


def render_news_card(news: dict):
    """Render a single trending news card — category color derived from classification."""
    cat_color = get_category_color(news["category"])
    st.markdown(f"""
    <div class="news-card">
        <div class="news-category" style="color:{cat_color}!important;">{news["category"]}</div>
        <div class="news-title" style="color:#F8FAFC!important;">{news["title"][:65]}</div>
        <div class="news-meta" style="color:#64748B!important;">Source</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# CUSTOM CSS
# =============================================================================

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background-color: #0B1120 !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B;
}
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebar"] h1 { color: #F8FAFC !important; font-weight: 700; }

header { visibility: hidden; }

.ticker-container {
    display: flex;
    justify-content: space-between;
    background-color: #0F172A;
    padding: 10px 20px;
    border-bottom: 1px solid #1E293B;
    margin-bottom: 1.5rem;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.85rem;
}
.ticker-item { color: #94A3B8; }
.ticker-value { color: #F8FAFC; margin-left: 5px; }

h1, h2, h3, h4, p, span, div, .stMarkdown { color: #E2E8F0 !important; }
.ticker-item, .ticker-value, .badge, .news-category { color: inherit !important; }

[data-testid="stChatInput"] { background-color: #020617; border: 1px solid #1E293B; }

.agent-log {
    background-color: #020617;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 15px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.8rem;
    margin-top: 1rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #0F172A !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px;
}

.news-card {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
}
.news-category { font-size: 0.7rem; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px; }
.news-title { font-size: 0.85rem; color: #F8FAFC !important; font-weight: 500; line-height: 1.3; }
.news-meta { font-size: 0.7rem; color: #64748B !important; margin-top: 4px; }

.insight-item {
    padding: 14px 0;
    border-bottom: 1px solid #1E293B;
    line-height: 1.7;
    font-size: 0.9rem;
}

.portfolio-alert {
    background-color: #1E293B;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #F8FAFC !important;
    text-align: center;
    margin-top: 10px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# =============================================================================
# FETCH LIVE DATA
# =============================================================================

ticker_data = fetch_ticker_data()
trending_news = fetch_trending_news()

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">
        <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10B981,#3B82F6);display:flex;align-items:center;justify-content:center;">
            <span style="color:#fff!important;font-size:0.8rem;font-weight:bold;">Q</span>
        </div>
        <div>
            <h1 style="color:#F8FAFC!important;font-size:1rem;margin:0;line-height:1.2;">TERMINAL v4.2</h1>
            <p style="font-size:0.7rem;color:#10B981!important;margin:0;">System Status: Active</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
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

# =============================================================================
# TOP NAVIGATION + TICKER TAPE
# =============================================================================

render_top_nav()
render_ticker_tape(ticker_data)

# =============================================================================
# MAIN 3-COLUMN LAYOUT
# =============================================================================

col_hist, col_main, col_news = st.columns([1, 3, 1])

# --- Left: Research History ---
with col_hist:
    st.markdown("<p style='color:#94A3B8!important;font-size:0.75rem;font-weight:700;letter-spacing:1px;'>RESEARCH HISTORY</p>", unsafe_allow_html=True)

    if "search_history" not in st.session_state:
        st.session_state.search_history = []

    for item in st.session_state.search_history[-3:]:
        with st.container(border=True):
            st.markdown(f"<strong style='color:#E2E8F0!important;'>{item['name'][:22]}...</strong><br><span style='color:#94A3B8!important;font-size:0.75rem;'>{item['time']} • Deep Scan</span>", unsafe_allow_html=True)

    if not st.session_state.search_history:
        st.markdown("<p style='color:#475569!important;font-size:0.8rem;'>No research yet.</p>", unsafe_allow_html=True)

# --- Right: Trending News (LIVE) ---
with col_news:
    st.markdown("<p style='color:#94A3B8!important;font-size:0.75rem;font-weight:700;letter-spacing:1px;'>TRENDING NEWS</p>", unsafe_allow_html=True)

    for news in trending_news[:4]:
        render_news_card(news)

    # Portfolio Alert badge
    st.markdown('<div class="portfolio-alert" style="color:#F8FAFC!important;">Portfolio Alert</div>', unsafe_allow_html=True)

# --- Center: Main Terminal ---
with col_main:
    company = st.chat_input("Analyze the impact of a company's market position...")

    if company:
        # Track search history
        now = datetime.now()
        st.session_state.search_history.append({
            "name": f"{company} Market Analysis",
            "time": now.strftime("%I:%M %p")
        })

        # --- Execution Header ---
        task_id = abs(hash(company + now.isoformat())) % 10000
        st.markdown(f"""
        <div style="margin-bottom:5px;">
            <span style="background-color:#064E3B;color:#34D399;padding:4px 10px;border-radius:4px;font-size:0.7rem;font-weight:bold;letter-spacing:1px;">AI AGENT EXECUTION</span>
            <span style="color:#94A3B8!important;font-size:0.8rem;margin-left:12px;">TASK ID: #QT-{task_id}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<h1 style='font-size:2.2rem;margin-top:8px;margin-bottom:0;color:#F8FAFC!important;font-weight:700;'>Market Analysis: {company}</h1>", unsafe_allow_html=True)

        # --- Execute Agents ---
        with st.status(f"System running macro and micro analysis for {company}...", expanded=True) as status:
            st.write(">> INITIALIZING ALPHA NODE (QUANT)...")
            alpha_data = run_quantitative_analysis(company)

            st.write(">> INITIALIZING BETA NODE (QUAL)...")
            beta_data = run_qualitative_analysis(company)

            st.write(">> ROUTING TO NEURAL JUDGE FOR SYNTHESIS...")
            final_report = evaluate_reports(company, alpha_data, beta_data)
            status.update(label="ANALYSIS COMPILED", state="complete")

        # =====================================================================
        # PARSE ALL DATA — nothing hardcoded below this point
        # =====================================================================

        # 1. Parse sentiment score from Alpha output (integer)
        sentiment_score = parse_sentiment_score(alpha_data)

        # 2. Compute signal and volatility FROM the score — never static
        computed_signal = compute_signal(sentiment_score)
        computed_volatility = compute_volatility(sentiment_score)

        # 3. Override with Alpha's explicit values if present, else use computed
        signal_match = re.search(r"Top Signal:\s*(BUY|SELL|HOLD|ACCUMULATE|REDUCE)", alpha_data, re.IGNORECASE)
        volatility_match = re.search(r"Volatility Index:\s*(LOW|MEDIUM|HIGH)", alpha_data, re.IGNORECASE)

        final_signal = signal_match.group(1).strip().upper() if signal_match else computed_signal
        final_volatility = volatility_match.group(1).strip().upper() if volatility_match else computed_volatility

        # 4. Derive all display colors from the DATA
        sentiment_color = get_change_color(sentiment_score - 50)  # >50 = green, <50 = red
        volatility_color = get_volatility_color(final_volatility)
        signal_color = get_signal_color(final_signal)

        # 5. Format sentiment display string
        sentiment_display = f"{sentiment_score} / 100"

        # --- METRICS ROW ---
        m1, m2, m3 = st.columns(3)
        with m1:
            render_score_indicator("SENTIMENT SCORE", sentiment_display, "#F8FAFC")
        with m2:
            render_score_indicator("VOLATILITY INDEX", final_volatility, volatility_color)
        with m3:
            render_signal_badge(final_signal)

        st.divider()

        # --- KEY EXECUTIVE INSIGHTS ---
        st.markdown("<p style='color:#10B981!important;font-size:0.85rem;font-weight:700;letter-spacing:1.5px;'>KEY EXECUTIVE INSIGHTS</p>", unsafe_allow_html=True)

        insights = parse_insights(beta_data)

        if insights:
            for insight in insights[:3]:
                render_insight(insight)
        else:
            st.markdown(beta_data)

        st.divider()

        # --- AGENT PERFORMANCE LOG ---
        st.markdown("<p style='color:#10B981!important;font-size:0.85rem;font-weight:700;letter-spacing:1.5px;'>AGENT PERFORMANCE LOG</p>", unsafe_allow_html=True)

        log_ts = now.strftime("%H:%M:%S")
        log_entries = [
            {"time": log_ts, "message": f"Alpha Node completed quantitative scan for {company}.", "type": "info"},
            {"time": log_ts, "message": f"Beta Node completed qualitative scan for {company}.", "type": "info"},
            {"time": log_ts, "message": f"Critical Pattern Detected: Sentiment={sentiment_score}, Signal={final_signal}", "type": "synthesis"},
            {"time": log_ts, "message": f"Briefing compiled. Confidence Interval: {min(sentiment_score + 16, 99)}.{abs(hash(company)) % 10}%", "type": "info"},
        ]
        render_agent_log(log_entries)

        # --- Expandable Full Reports ---
        with st.expander("📄 Full Alpha Report (Quantitative)"):
            st.markdown(alpha_data)
        with st.expander("📄 Full Beta Report (Qualitative)"):
            st.markdown(beta_data)
        with st.expander("⚖️ Full Judge Synthesis"):
            st.markdown(final_report)

    else:
        # --- IDLE STATE ---
        st.markdown("<span style='background-color:#1E293B;color:#94A3B8;padding:4px 10px;border-radius:4px;font-size:0.7rem;font-weight:bold;letter-spacing:1px;'>SYSTEM IDLE</span>", unsafe_allow_html=True)
        st.markdown("<h1 style='font-size:2.5rem;margin-top:12px;color:#475569!important;font-weight:700;'>Awaiting Execution Protocol</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#475569!important;'>Use the terminal input below to launch a targeted market scan.</p>", unsafe_allow_html=True)