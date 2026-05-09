"""
Recall@40 regression test — verifies every gold assessment from the 10
public sample conversation traces (C1-C10) appears in the top-40 candidates
returned by the retrieval stage.

Gold names are the EXACT catalog names (verified via URL slugs from sample
conversation files C1.md–C10.md).

Run:
    python test_recall.py
"""
import sys
sys.path.insert(0, '.')
from agent import _retrieve

# Gold sets: exact catalog names from the final locked-in turn of each trace.
# (C6: DSI was proposed in turn 1 but user chose the 8.0 bundle — final list = 2 items)
# (C10: OPQ32r was user-dropped — final list = 2 items)
TRACES = {
    "C1_CXO": {
        "query": "CXO director senior leadership 15 years experience selection benchmark",
        "gold": [
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ Universal Competency Report 2.0",
            "OPQ Leadership Report",
        ],
    },
    "C2_Rust": {
        "query": "senior rust engineer high performance networking infrastructure systems programming linux",
        "gold": [
            "Smart Interview Live Coding",
            "Linux Programming (General)",
            "Networking and Implementation (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C3_ContactCentre": {
        "query": "entry level contact centre agents inbound calls customer service english US spoken language",
        "gold": [
            "SVAR - Spoken English (US) (New)",
            "Contact Center Call Simulation (New)",
            "Entry Level Customer Serv-Retail & Contact Center",
            "Customer Service Phone Simulation",
        ],
    },
    "C4_GradFinance": {
        "query": "graduate financial analysts final year students numerical reasoning finance knowledge",
        "gold": [
            "SHL Verify Interactive - Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C5_Sales": {
        "query": "sales organization restructuring talent audit reskill business development account executive",
        "gold": [
            "Global Skills Assessment",
            "Global Skills Development Report",
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ],
    },
    "C6_PlantOperator": {
        "query": "plant operators chemical facility safety compliance reliability procedure industrial manufacturing",
        "gold": [
            "Manufac. & Indust. - Safety & Dependability 8.0",
            "Workplace Health and Safety (New)",
        ],
    },
    "C7_Healthcare": {
        "query": "bilingual healthcare admin staff patient records HIPAA compliance spanish medical terminology word",
        "gold": [
            "HIPAA (Security)",
            "Medical Terminology (New)",
            "Microsoft Word 365 - Essentials (New)",
            "Dependability and Safety Instrument (DSI)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C8_Admin": {
        "query": "admin assistants excel word daily office administrative screening",
        "gold": [
            "Microsoft Excel 365 (New)",
            "Microsoft Word 365 (New)",
            "MS Excel (New)",
            "MS Word (New)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    "C9_Java": {
        "query": "senior full stack engineer java spring sql aws docker backend microservices",
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
        "query": "graduate management trainee scheme cognitive personality situational judgement recent graduates",
        "gold": [
            "SHL Verify Interactive G+",
            "Graduate Scenarios",
        ],
    },
}


def run():
    import numpy as np
    import agent as _agent

    # Force catalog load
    _agent._load_catalog()

    total_hits = 0
    total_gold = 0
    all_perfect = True

    for trace_id, trace in TRACES.items():
        candidates = _retrieve(trace["query"], top_n=40)
        candidate_names = {c["name"].lower() for c in candidates}

        hits = sum(1 for g in trace["gold"] if g.lower() in candidate_names)
        gold_count = len(trace["gold"])
        recall = hits / gold_count
        total_hits += hits
        total_gold += gold_count

        status = "PERFECT" if recall == 1.0 else f"MISS {gold_count - hits}"
        if recall < 1.0:
            all_perfect = False
        print(f"{trace_id}: {hits}/{gold_count} = {recall:.2f}  [{status}]")

        if recall < 1.0:
            from sklearn.metrics.pairwise import cosine_similarity
            cat = _agent._catalog
            q_vec = _agent._tfidf_vec.transform([trace["query"]])
            sims = cosine_similarity(q_vec, _agent._tfidf_matrix).flatten()
            sorted_idx = np.argsort(sims)[::-1]

            for g in trace["gold"]:
                if g.lower() not in candidate_names:
                    rank = next(
                        (r + 1 for r, i in enumerate(sorted_idx)
                         if cat[i]["name"].lower() == g.lower()),
                        -1,
                    )
                    print(f"  MISSING (natural rank {rank}): {g}")

    mean_recall = total_hits / total_gold
    print(f"\nMean Recall@40: {mean_recall:.4f}  {'ALL PERFECT' if all_perfect else 'NEEDS FIXING'}")
    return mean_recall


if __name__ == "__main__":
    score = run()
    sys.exit(0 if score == 1.0 else 1)
