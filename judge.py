import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env
load_dotenv()

def evaluate_reports(company_name: str, report_alpha: str, report_beta: str) -> str:
    """
    Evaluates the quantitative (Alpha) and qualitative (Beta) reports using an LLM-as-Judge.
    Selects the best report or merges them based on a rubric: Accuracy, Grounding, and Insight.
    """
    print(f"[*] Starting Judge evaluation for {company_name}...")
    
    # 1. Initialize Groq model for reasoning
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3  # Lower temperature for more consistent "Judging"
    )
    
    # 2. Construct Prompt with Rubric
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert LLM-as-Judge and Chief Editor for a Finance News Brief. Your job is to review two researcher reports and compile a final, authoritative briefing."),
        ("user", """
You are tasked with evaluating and merging two research reports for the company: {company_name}.

Report Alpha (Quantitative):
{report_alpha}

Report Beta (Qualitative):
{report_beta}

Evaluate the reports based on the following rubric:
1. Accuracy: Do the claims seem plausible and reflect the provided reports accurately?
2. Grounding (CRITICAL): Every single claim or data point MUST be backed by an inline URL citation (e.g., [1], [2]). Any claim without a clear citation in the source reports MUST be discarded or flagged.
3. Insight: Does the report provide a clear, holistic view of the company's financial and market standing?
4. Situation Weighting: Explicitly weigh which agent's data is more critical for the company's current 'situation' in your Final Summary (e.g., if the company has high debt, prioritize Alpha; if there's a leadership change, prioritize Beta).

Your tasks:
1. Review both reports against the rubric.
2. Merge the strongest grounded insights from both into a single cohesive Final Briefing. Pay special attention to Situation Weighting.
3. Your Final Briefing MUST maintain strict inline citations for every fact. Drop any ungrounded claims.

Format your Final Briefing as a set of bold-titled insights. Each insight must follow this format:
**[Short Bold Title]:** [1-2 sentence explanation with inline citation]

Start with a brief "Situation Weighting" paragraph explaining which agent was prioritized and why, then provide the merged insights.
""")
    ])
    
    # 3. Generate reasoning/summary
    print(f"[*] Generating Final Briefing via Groq...")
    chain = prompt | llm
    try:
        response = chain.invoke({
            "company_name": company_name,
            "report_alpha": report_alpha,
            "report_beta": report_beta
        })
        return response.content
    except Exception as e:
        print(f"[!] Error during Groq reasoning: {e}")
        return f"Error: Failed to generate Final Briefing for {company_name} due to Groq reasoning error: {e}"

if __name__ == "__main__":
    # Example usage
    company = "NVIDIA"
    alpha = "Revenue grew by 20% [1]."
    beta = "CEO says 'We are doing great' [2]."
    print(f"=== Judge Agent ===")
    summary = evaluate_reports(company, alpha, beta)
    print("\n=== Final Report ===")
    print(summary)
