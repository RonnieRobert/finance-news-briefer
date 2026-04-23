import streamlit as st
import re
from researcher_alpha import run_quantitative_analysis
from researcher_beta import run_qualitative_analysis
from judge import evaluate_reports

# --- UI Setup ---
st.set_page_config(page_title="Finance News Briefer", page_icon="📈", layout="wide")
st.title("🚀 Finance News Briefer")
st.markdown("Enter a company name to get a multi-agent verified report.")

# --- Input ---
company = st.text_input("Enter Company Name (e.g., Reliance Industries):")

if st.button("Generate Briefing"):
    if company:
        with st.status(f"Analyzing {company}...", expanded=True) as status:
            # 1. Run Researchers
            st.write("📊 Researching Market Sentiment (Beta Agent)...")
            beta_data = run_qualitative_analysis(company)

            st.write("🔍 Researching Quant data (Alpha Agent)...")
            alpha_data = run_quantitative_analysis(company)
            
            # 2. Run Judge
            st.write("⚖️ Finalizing report (LLM-as-Judge)...")
            final_report = evaluate_reports(company, alpha_data, beta_data)
            
            status.update(label="Analysis Complete!", state="complete")

        # --- Data Parsing ---
        # Regex patterns to extract URLs and metrics
        logo_match = re.search(r"!\[Logo\]\((.*?)\)", beta_data, re.IGNORECASE)
        ceo_match = re.search(r"!\[CEO\]\((.*?)\)", beta_data, re.IGNORECASE)
        
        revenue_match = re.search(r"Revenue:\s*(.*)", alpha_data, re.IGNORECASE)
        stock_match = re.search(r"Stock Price Change:\s*(.*)", alpha_data, re.IGNORECASE)

        logo_url = logo_match.group(1).strip() if logo_match else None
        ceo_url = ceo_match.group(1).strip() if ceo_match else None
        revenue_val = revenue_match.group(1).strip() if revenue_match else "N/A"
        stock_val = stock_match.group(1).strip() if stock_match else "N/A"

        # --- Display Results ---
        st.divider()
        
        # Display Visuals and Metrics at the top
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if logo_url:
                try:
                    st.image(logo_url, caption="Company Logo", use_container_width=True)
                except Exception:
                    st.write("*(Logo image unavailable)*")
        with col2:
            if ceo_url:
                try:
                    st.image(ceo_url, caption="CEO", use_container_width=True)
                except Exception:
                    st.write("*(CEO image unavailable)*")
        with col3:
            st.metric(label="Revenue", value=revenue_val)
        with col4:
            st.metric(label="Stock Price Change", value=stock_val)
            
        st.divider()

        # Display Sections in Order: Beta, Alpha, Judge
        st.subheader("Qualitative Insights")
        st.markdown(beta_data)
        
        st.divider()
        st.subheader("Quantitative Analysis")
        st.markdown(alpha_data)
        
        st.divider()
        st.subheader(f"Final Executive Briefing")
        st.markdown(final_report)
    else:
        st.warning("Please enter a company name first.")