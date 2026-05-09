"""
End-to-end Recall@10 test.

Unlike test_recall.py (which tests the retrieval pool), this script simulates
real multi-turn conversations and measures whether gold assessments actually
appear in the LLM's final recommendations — the metric the evaluator scores.

Run:
    python test_recall_e2e.py

Costs ~10 Groq API calls (one full conversation per trace).
"""
import sys
import os
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

import agent as shl_agent

# Eval uses same Gemini primary as production. Set GEMINI_API_KEY in env.
# Groq fallback: GROQ_MODEL defaults to llama-3.3-70b-versatile if Gemini fails.
os.environ.setdefault("GROQ_MODEL", "llama-3.3-70b-versatile")

# Each trace: ordered user turns taken from C1.md–C10.md
# We stop at the last turn where the user confirmed the shortlist.
TRACES = {
    "C1_CXO": {
        "turns": [
            "We need a solution for senior leadership.",
            "The pool consists of CXOs, director-level positions; people with more than 15 years of experience.",
            "Selection — comparing candidates against a leadership benchmark.",
            "Perfect, that's what we need.",
        ],
        "gold": [
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ Universal Competency Report 2.0",
            "OPQ Leadership Report",
        ],
    },
    "C2_Rust": {
        "turns": [
            "I'm hiring a senior Rust engineer for high-performance networking infrastructure. What assessments should I use?",
            "Yes, go ahead. Should I also add a cognitive test for this level?",
            "That works. Thanks.",
        ],
        "gold": [
            "Smart Interview Live Coding",
            "Linux Programming (General)",
            "Networking and Implementation (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C3_ContactCentre": {
        "turns": [
            "We're screening 500 entry-level contact centre agents. Inbound calls, customer service focus. What should we use?",
            "English.",
            "US.",
            "Perfect — new simulation for volume, old solution for finalists. Confirmed.",
        ],
        "gold": [
            "SVAR - Spoken English (US) (New)",
            "Contact Center Call Simulation (New)",
            "Entry Level Customer Serv-Retail & Contact Center",
            "Customer Service Phone Simulation",
        ],
    },
    "C4_GradFinance": {
        "turns": [
            "Hiring graduate financial analysts — final-year students, no work experience. We need numerical reasoning and a finance knowledge test.",
            "Good. Can you also add a situational judgement element — work-context decision making for graduates?",
            "That covers it. Numerical + Graduate Scenarios as first filter, domain tests for shortlisted candidates.",
        ],
        "gold": [
            "SHL Verify Interactive - Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C5_Sales": {
        "turns": [
            "As part of our restructuring and annual talent audit, we need to re-skill our Sales organization. What solutions do you recommend?",
            "What's the difference between OPQ and OPQ MQ Sales Report?",
            "Clear. We'll use OPQ for everyone and add MQ only where we want motivators in the Sales Report; keeping the five solutions as our audit stack.",
        ],
        "gold": [
            "Global Skills Assessment",
            "Global Skills Development Report",
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ],
    },
    "C6_PlantOperator": {
        "turns": [
            "We're hiring plant operators for a chemical facility. Safety is absolute top priority — reliability, procedure compliance, never cutting corners. What do you recommend?",
            "What's the difference between the DSI and the Safety & Dependability 8.0?",
            "We're industrial. The 8.0 bundle is the right fit. Confirmed.",
        ],
        "gold": [
            "Manufac. & Indust. - Safety & Dependability 8.0",
            "Workplace Health and Safety (New)",
        ],
    },
    "C7_Healthcare": {
        "turns": [
            "We're hiring bilingual healthcare admin staff in South Texas — they handle patient records and need to be assessed in Spanish. HIPAA compliance is critical. What assessments work?",
            "They're functionally bilingual — English fluent for written work. Go with the hybrid.",
            "Are we legally required under HIPAA to test all staff who touch patient records? And does this SHL test satisfy that requirement?",
            "Understood. Keep the shortlist as-is.",
        ],
        "gold": [
            "HIPAA (Security)",
            "Medical Terminology (New)",
            "Microsoft Word 365 - Essentials (New)",
            "Dependability and Safety Instrument (DSI)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C8_Admin": {
        "turns": [
            "I need to quickly screen admin assistants for Excel and Word daily.",
            "In that case, I am OK with adding a simulation - we want to capture the capabilities.",
            "That's good.",
        ],
        "gold": [
            "Microsoft Excel 365 (New)",
            "Microsoft Word 365 (New)",
            "MS Excel (New)",
            "MS Word (New)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C9_Java": {
        "turns": [
            'Here\'s the JD for an engineer we need to fill. "Senior Full-Stack Engineer — 5+ years across Core Java, Spring, REST API design, Angular, SQL/relational databases, AWS deployment, and Docker."',
            "Backend-leaning. Day-one priorities are Core Java and Spring; SQL is constant. Angular is occasional.",
            "Senior IC. They lead design on their own services but don't manage other engineers directly.",
            "Add AWS and Docker. Drop REST — the API design signal will already come through in Spring and the live interview.",
            "On Java — they'd be working on existing services, not greenfield. Is the Advanced level the right pick?",
            "Do we really need Verify G+ on top of all the technical tests? Feels redundant.",
            "Keep Verify G+. Locking it in.",
        ],
        "gold": [
            "Core Java (Advanced Level) (New)",
            "Spring (New)",
            "SQL (New)",
            "Amazon Web Services (AWS) Development (New)",
            "Docker (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C10_GradTrainee": {
        "turns": [
            "We run a graduate management trainee scheme. We need a full battery — cognitive, personality, and situational judgement. All recent graduates.",
            "But can you remove the OPQ32r and replace it with something shorter? Candidates complain it takes too long.",
            "Drop the OPQ. Final list: Verify G+ and Graduate Scenarios.",
        ],
        "gold": [
            "SHL Verify Interactive G+",
            "Graduate Scenarios",
        ],
    },
}


import time as _time

# Only needed for Gemini (15 RPM). Groq has no per-minute restriction here.
_TURN_DELAY = float(os.environ.get("TURN_DELAY", "5" if os.environ.get("GEMINI_API_KEY") else "0"))


def simulate(user_turns: list[str]) -> list[str]:
    """Run a full multi-turn conversation and return names from final recommendations."""
    messages: list[dict] = []
    final_recs: list[str] = []

    for i, turn in enumerate(user_turns):
        if i > 0:
            _time.sleep(_TURN_DELAY)  # respect RPM limit
        messages.append({"role": "user", "content": turn})
        capped = messages[-8:]
        result = shl_agent.chat(capped)
        messages.append({"role": "assistant", "content": result["reply"]})
        if result.get("recommendations"):
            final_recs = [r["name"] for r in result["recommendations"]]
        if result.get("end_of_conversation"):
            break

    return final_recs


def run() -> float:
    shl_agent._load_catalog()

    total_hits = 0
    total_gold = 0
    all_perfect = True

    print("Running end-to-end Recall@10 (LLM recommendations)…\n")

    for trace_id, trace in TRACES.items():
        print(f"  {trace_id} … ", end="", flush=True)
        try:
            rec_names_lower = {n.lower() for n in simulate(trace["turns"])}
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        gold = trace["gold"]
        hits = sum(1 for g in gold if g.lower() in rec_names_lower)
        recall = hits / len(gold)
        total_hits += hits
        total_gold += len(gold)

        status = "PERFECT" if recall == 1.0 else f"MISS {len(gold) - hits}"
        if recall < 1.0:
            all_perfect = False
        print(f"{hits}/{len(gold)} = {recall:.2f}  [{status}]")

        if recall < 1.0:
            for g in gold:
                if g.lower() not in rec_names_lower:
                    print(f"    NOT RECOMMENDED: {g}")

    mean_recall = total_hits / total_gold if total_gold else 0.0
    print(f"\nMean Recall@10 (e2e LLM): {mean_recall:.4f}  "
          f"{'ALL PERFECT' if all_perfect else 'NEEDS WORK'}")
    return mean_recall


if __name__ == "__main__":
    score = run()
    sys.exit(0 if score >= 0.8 else 1)
