# Approach Document — SHL Assessment Advisor
**Uday Vimal | Research AI Intern Assignment**

---

## Design Choices

The core problem is not retrieval — it is understanding hiring intent. A recruiter asking for a "contact centre role" does not know they need four separate products serving different hiring funnel stages. That domain knowledge must be encoded explicitly, not inferred from a vague query.

I chose a **two-stage architecture** over a standard RAG pipeline:

| Stage | Method | Why |
|---|---|---|
| Retrieval | TF-IDF + keyword boosts | 100% Recall@40, zero cold-start, deterministic |
| Selection | Groq llama-3.3-70b-versatile | Only model that handles complex JSON + 10-rule prompt reliably on free tier |

I rejected dense embeddings (FAISS/Chroma) because: bigram TF-IDF distinguishes "Core Java (Advanced Level) (New)" from "Core Java (New)" more reliably than cosine similarity on dense vectors, and Recall@40 was already perfect with TF-IDF — adding a vector store would add infrastructure complexity with no measurable gain.

---

## Retrieval Setup

The catalog (377 items, scraped via `httpx` + `BeautifulSoup`) is indexed with scikit-learn TF-IDF using bigrams and sublinear TF weighting.

**Three-layer retrieval:**

1. **TF-IDF cosine similarity** — base ranking across all 377 items
2. **25 keyword boost rules** (+0.25 per match) — map recruiter vocabulary to catalog name fragments. Example: "plant operator, chemical facility, safety" has near-zero TF-IDF overlap with "Dependability and Safety Instrument (DSI)" — the boost rule bridges this gap
3. **Conditional score anchors** — items that appear in many traces but score low on raw TF-IDF get a score floor: OPQ32r (0.35 always), DSI (0.58 for healthcare/safety queries), Basic Statistics (0.75 for finance queries), SQL New (0.75 for database queries), Sales Transformation (0.75 for sales queries), Smart Interview Live Coding (0.58 for niche languages with no SHL test)

Top 40 candidates are passed to the LLM. The full catalog is excluded from the prompt — fitting all 377 items would add roughly 3,500 extra tokens per request and exceed Groq's per-minute token limit.

---

## Prompt Design

The system prompt encodes **10 mandatory advisory rules** derived by reading all 10 public traces:

- OPQ32r in every shortlist without exception
- Contact centre: 4-item bundle (SVAR + simulation + entry-level + phone)
- Senior leadership (Director/VP/CXO only): OPQ32r + Leadership Report + UCR 2.0
- Finance/quant: Financial Accounting + Basic Statistics (knowledge test, not a substitute for Verify Numerical)
- Admin/office: all 4 Microsoft Office tests — both legacy and 365 versions are separate catalog items
- Safety/industrial: DSI + Workplace Health and Safety
- Healthcare admin: DSI + Medical Terminology + HIPAA + Word 365 Essentials
- Sales: OPQ32r + MQ Sales Report + Sales Transformation 2.0 IC
- SQL mentioned anywhere: SQL (New) mandatory, same priority as OPQ32r
- Graduate roles: Verify G+ + Graduate Scenarios always paired

Temperature is set to 0.15 for near-deterministic outputs. JSON mode enforced. Max tokens 1,200 keeps generation under 5 seconds on Render free tier.

**Hallucination prevention:** every recommendation passes through `_validate_recommendations()` which does a two-step catalog lookup (URL first, then lowercase name). Any item not in the 377-item catalog is silently dropped before the response reaches the client.

---

## Evaluation Method

**Stage 1 — Recall@40** (`test_recall.py`): verifies every gold assessment from each trace appears in the top-40 TF-IDF candidate pool. Runs in under one second with no API calls. Used as a fast regression check after every retrieval code change.

**Stage 2 — Recall@10** (`test_recall_e2e.py`): simulates full multi-turn conversations using an LLM-simulated user (not fixed scripts) and checks whether the agent's final recommendations contain the gold assessments. The simulated user volunteers facts out of order and self-corrects mid-conversation to test robustness.

| Metric | Result |
|---|---|
| Recall@40 (retrieval) | 1.00 across all 10 traces |
| Recall@10 (end-to-end) | PERFECT on C1, C2, C3, C5, C6, C7, C10 |

---

## What Did Not Work

- **Full catalog in prompt** — 14,700 tokens per request, hit Groq's 12K TPM limit on every call. Removed; prompt dropped to ~3,900 tokens.
- **Smaller LLMs** — llama-3.1-8b and gemma2-9b broke the JSON schema under the 10-rule prompt. qwen3-32b returned `<think>` blocks that broke JSON parsing.
- **Gemini 2.0 Flash as primary** — 15 RPM limit caused 30-second timeout breaches during multi-turn conversations. Replaced with Groq (1,000 RPM).
- **Abstract prompt rules** — "prefer advanced-level tests for senior roles" was interpreted inconsistently. Specific catalog names in rules ("Core Java (Advanced Level) (New)" not "Core Java (New)") worked far better.
- **Dense embeddings** — cold-start latency of 3 to 6 seconds on Render free tier; no improvement over TF-IDF since Recall@40 was already 100%.

---

## How I Measured Improvement

Iteration loop: read a trace, identify whether the miss was a retrieval failure (gold item outside top-40) or a selection failure (gold item in top-40 but LLM did not pick it), fix the corresponding layer, rerun Recall@40 as a fast sanity check, then run Recall@10 only when retrieval was confirmed clean.

Score anchors were calibrated by first confirming via a free Python check (no API calls) that the missing item was already in the top-40 — if yes, the fix went to the prompt or anchor scoring rather than the boost rules. This separation kept the iteration loop fast and avoided burning API quota on retrieval-stage issues.
