import os
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env
load_dotenv()

def run_qualitative_analysis(company_name: str) -> str:
    """
    Runs a qualitative analysis for a given company.
    Focuses on market sentiment, CEO quotes, and competitive landscape.
    Returns KEY EXECUTIVE INSIGHTS as bold titled bullet points.
    """
    print(f"[*] Starting qualitative research for {company_name}...")
    
    # 1. Initialize Tavily Client for searching
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    tavily = TavilyClient(api_key=tavily_api_key)
    
    # 2. Perform the search
    query = f"{company_name} latest news market sentiment, CEO quotes, competitive landscape, regulatory risks"
    print(f"[*] Searching Tavily for query: '{query}'")
    try:
        search_result = tavily.search(query=query, search_depth="advanced", max_results=5)
    except Exception as e:
        print(f"[!] Error during Tavily search: {e}")
        return f"Error: Failed to retrieve qualitative data for {company_name} due to Tavily search error: {e}"
    
    # Extract context and URLs for citations
    context = ""
    for idx, result in enumerate(search_result.get("results", [])):
        context += f"Source [{idx+1}]: {result['url']}\n"
        context += f"Content: {result['content']}\n\n"

    # 3. Initialize Groq model for reasoning
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.5
    )
    
    # 4. Construct Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Qualitative Analyst. Your job is to analyze the market sentiment and qualitative data provided and extract key executive-level insights."),
        ("user", """
Please analyze the following information for {company_name}. 

Your output MUST be formatted as exactly 3 KEY EXECUTIVE INSIGHTS. Each insight must follow this exact format:

**[Short Bold Title]:** [1-2 sentence explanation of the insight with inline citation]

Example format:
**Semiconductor Surge:** AI infrastructure spending remains resilient despite macro concerns. Major cloud providers are increasing capital expenditure guidance for 2024 by 15%. [1]

**Interest Rate Lag:** The market has priced in "Higher for Longer," focusing now on corporate earnings growth as the primary valuation driver. [2]

**Regulatory Headwinds:** Antitrust investigations in EU and US pose mid-term risks for dominant software platforms, though immediate financial impact is projected as minimal. [3]

You MUST produce exactly 3 insights, each on its own line, each starting with a bold title followed by a colon.
Use the Source numbers (e.g., [1], [2]) provided in the context for inline citations.

Context Information:
{context}

KEY EXECUTIVE INSIGHTS:
""")
    ])
    
    # 5. Generate reasoning/summary
    print(f"[*] Generating reasoning via Groq...")
    chain = prompt | llm
    try:
        response = chain.invoke({
            "company_name": company_name,
            "context": context
        })
        return response.content
    except Exception as e:
        print(f"[!] Error during Groq reasoning: {e}")
        return f"Error: Failed to generate qualitative summary for {company_name} due to Groq reasoning error: {e}"

if __name__ == "__main__":
    # Example usage
    company = "NVIDIA"
    print(f"=== Qualitative Analyst Agent ===")
    summary = run_qualitative_analysis(company)
    print("\n=== Final Report ===")
    print(summary)
