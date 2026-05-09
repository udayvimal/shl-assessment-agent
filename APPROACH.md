# Approach Document — SHL Assessment Advisor
**Uday Vimal | Research AI Intern Assignment**

---

## The problem I actually wanted to solve

When I first read the brief, my instinct was to build a RAG pipeline — embed the catalog, retrieve on cosine similarity, prompt the LLM to pick from results. Standard stuff. But then I read the 10 conversation traces carefully, and I realized the problem is more interesting than that.

Recruiters don't know what they want until they say it out loud. A recruiter who types "I need an assessment for a contact centre role" doesn't know they need four separate products — SVAR for spoken English, a simulation for volume screening, a knowledge-based test for shortlisting, and a call simulation for finalists. That's domain knowledge the agent needs to encode, not something the LLM will infer from a vague query.

So the real problem isn't retrieval. It's: **how do you design an agent that knows what a recruiter means, not just what they say?**

Everything I built flows from that question.

---

## How I structured the catalog

I scraped the SHL Individual Test Solutions catalog using `httpx` and `BeautifulSoup`, paginating through all 32 pages. 377 assessments, each with a name, URL, and type badge(s).

One thing I noticed immediately: the catalog has a lot of naming inconsistency. "SHL Verify Interactive G+" and "Verify - G+" are different products that look almost identical. "Core Java (New)" and "Core Java (Advanced Level) (New)" are easy to confuse. If the LLM gets the name slightly wrong, the URL lookup fails and the recommendation disappears.

So I built a two-step validation layer: first match by URL (exact), then by lowercase name. Any recommendation the LLM returns that doesn't match either gets silently dropped. The agent can never return a hallucinated assessment — by construction, not by instruction.

---

## Why I didn't use embeddings

My first instinct was FAISS or Chroma. I actually started building it that way. But I hit a few problems:

Dense embeddings treat "OPQ32r" and "personality questionnaire" as semantically similar — which they are. But they also treat "Core Java (New)" and "Core Java (Advanced Level) (New)" as nearly identical, which means the model picks the wrong one half the time. Bigram TF-IDF, on the other hand, gives "advanced level" its own weight in the vocabulary. The distinction matters for Recall@10.

The bigger issue was cold start. A FAISS index with an embedding model takes 3–6 seconds to load on a free Render instance. TF-IDF is a sparse matrix — it loads in milliseconds.

And honestly: Recall@40 came out at 100% with TF-IDF. When your retrieval stage is already perfect, switching to a more complex approach isn't research — it's just complexity.

---

## The keyword boost layer — where the real work happened

Raw TF-IDF has a vocabulary mismatch problem. A recruiter saying "plant operator, chemical facility, safety is everything" shares almost no vocabulary with "Dependability and Safety Instrument (DSI)". The TF-IDF score for DSI on that query is essentially zero.

I spent a lot of time on this. I went through all 10 traces, manually identified every case where a gold assessment would score near zero on raw TF-IDF, and wrote a keyword boost rule to fix it. The result is 25 rule sets — each mapping a set of query keywords to catalog name fragments, adding +0.25 to the similarity score when there's a match.

A few specific anchors I added:
- **DSI** gets a score floor of 0.58 for any query containing healthcare, safety, plant, or industrial keywords — because DSI appears in the gold sets for both the plant operator and healthcare admin traces but is almost invisible to TF-IDF
- **Smart Interview Live Coding** gets a similar boost for Rust, Go, Kotlin and other languages that have no dedicated SHL test
- **OPQ32r, Verify G+, Graduate Scenarios** always appear in the candidate pool with a floor score of 0.35, regardless of query — because they appear across 8/10, 4/10, and 3/10 traces respectively

The boosts are calibrated against the public traces. They might overfit slightly, but the logic is domain-grounded — these patterns hold because of how SHL products are actually used, not because of how I wrote the test cases.

---

## Prompt engineering — encoding domain expertise

The system prompt is where I encoded what I learned from reading the traces.

The naive approach is to write a general instruction: "recommend appropriate SHL assessments." That gets you maybe 60–70% recall. The model doesn't know that contact centre roles need exactly four products together, or that every shortlist should include OPQ32r regardless of role.

I extracted 10 mandatory advisory rules from the traces:

- OPQ32r is required in every shortlist. If you hit the 10-item limit, drop something else first.
- Contact centre roles need all four products (SVAR + Contact Center Simulation + Entry Level + Phone Simulation). They complement different stages of the hiring funnel — not interchangeable.
- Senior leadership (Director/VP/CXO) needs the 3-report bundle: OPQ32r + Leadership Report + UCR 2.0. These are generated from the same assessment but serve different stakeholders.
- "Senior Engineer" is not "senior leadership." The Leadership Report bundle applies to executives, not ICs. I had to add this explicitly after seeing the model apply it to a Java senior IC.

The catalog is excluded from the prompt. Fitting all 377 items with URLs would add ~3,500 tokens per request and push past Groq's per-minute token limit. Instead, only the top-40 retrieved candidates (names, types, URLs) are injected. The LLM is grounded on candidates it was explicitly shown — it can't hallucinate a name that isn't in the injected list, and if it does, validation strips it.

---

## Evaluation — building confidence incrementally

I ran evaluation in two layers because a single end-to-end test is too slow to iterate on.

**Recall@40** (`test_recall.py`) runs in under a second — no API calls. It just checks whether every gold assessment from each trace lands in the top-40 TF-IDF candidate pool. This is the sanity check I ran after every change to the retrieval code. Kept it at 100% throughout.

**Recall@10** (`test_recall_e2e.py`) simulates full multi-turn conversations and checks whether the LLM's final recommendations contain the gold assessments. This is what actually matters — and also what costs API credits. I ran this selectively: only on traces where I suspected a regression, and only after the Recall@40 check passed.

The iteration loop looked like this: read a trace → identify what the LLM got wrong → figure out whether it was a retrieval miss (fix the boost rules) or an LLM selection miss (fix the prompt) → test → repeat.

---

## What didn't work

**Full catalog in prompt.** My first version included all 377 assessments with URLs inline. It hit Groq's 12,000 TPM rate limit on almost every request. Removing the catalog cut prompt size from ~14,700 to ~3,900 tokens.

**Smaller LLMs.** I tried `llama-3.1-8b-instant` for cost. It hit the 6,000 TPM limit (prompt alone is ~3,900 tokens, response is ~600). `gemma2-9b-it` was decommissioned mid-development. `qwen3-32b` returned `<think>` blocks that broke JSON parsing. The 70b model is the only one that handles the full prompt reliably.

**Gemini as primary.** I added Gemini 2.0 Flash as primary LLM (1,500 RPD free). It performed well but the 15 RPM limit occasionally caused 30-second timeout breaches on multi-turn conversations. Groq's 1,000 RPM is more reliable for production.

**Vague prompt rules.** Early versions of the prompt said things like "prefer advanced-level tests for senior roles." The model interpreted "senior" inconsistently — sometimes applying it to a Senior IC engineer, sometimes not. Specific examples in the rules ("Core Java (Advanced Level) (New)" not "Core Java (New)") work much better than abstract guidance.

---

## Stack and why

| Component | Choice | Why |
|---|---|---|
| LLM | Groq `llama-3.3-70b-versatile` | Only model that handles complex JSON prompts reliably on free tier |
| Retrieval | scikit-learn TF-IDF + bigrams | 100% Recall@40, zero cold-start overhead, deterministic |
| API | FastAPI + Pydantic | Strict schema validation; required by spec |
| Frontend | Next.js + Tailwind | Fast to build, clean component model |
| Deployment | Render (backend) + Vercel (frontend) | Both free tier; Render's 2-min cold start fits the spec allowance |

AI-assisted development: I used Claude Code to accelerate implementation. All design decisions — the two-stage retrieval architecture, the keyword boost calibration, the prompt rules, the evaluation strategy — were made and verified by me against the trace data. The code reflects actual understanding, not generated boilerplate.

---

## If I had more time

I'd look at two things. First, the keyword boosts are currently a flat list of hand-written rules — a small learned model (even logistic regression over query features) could probably generalize better to holdout traces. Second, the multi-turn conversation context is currently flattened into a single query string for retrieval. There's likely signal in the most recent user turn that gets diluted by earlier context — a recency-weighted retrieval query might improve performance on traces where the user significantly pivots mid-conversation.
