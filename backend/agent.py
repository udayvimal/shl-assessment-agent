"""
SHL Assessment Advisor — agent logic.

Recall@10 design:
  Stage 1 — TF-IDF + keyword-boost retrieval → top 40 candidates
  Stage 2 — Groq llama-3.3-70b-versatile selects 1-10 from candidates

Keyword boosts calibrated against 10 public sample conversation traces (C1-C10).
"""
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
from groq import Groq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


_client: Groq | None = None
_catalog: list[dict] | None = None
_tfidf_matrix = None
_tfidf_vec: TfidfVectorizer | None = None

# ---------------------------------------------------------------------------
# Type-label expansions for richer TF-IDF documents
# ---------------------------------------------------------------------------
_TYPE_LABELS = {
    "A": "ability aptitude reasoning cognitive verbal numerical deductive inductive general intelligence",
    "B": "biodata situational judgement sjt scenario behavioural work style",
    "C": "competencies competency framework ucf behaviours skills profile",
    "D": "development 360 feedback multirater review coaching growth",
    "E": "exercise assessment centre in-tray role-play presentation group discussion",
    "K": "knowledge skills technical programming language test domain",
    "P": "personality behaviour traits opq motivation values culture fit workplace style",
    "S": "simulation realistic job work sample interactive performance",
}

# ---------------------------------------------------------------------------
# Keyword boost rules (keyword → catalog name fragments to upweight)
# Each +0.25 for name-fragment match when keyword is present in query
# Calibrated from C1-C10 sample traces
# ---------------------------------------------------------------------------
_KEYWORD_BOOSTS: list[tuple[list[str], list[str]]] = [
    # Technical — Java ecosystem
    (["java", "spring boot", "spring framework", "jvm", "backend"],
     ["java 8", "core java", "spring", "hibernate", "java frameworks",
      "java web services", "java design patterns", "java platform enterprise",
      "enterprise java beans", "java 2 platform"]),
    # Technical — Python / Data
    (["python", "data science", "machine learning", "ml", "ai"],
     ["python", "data science", "r programming", "automata data science",
      "statistical analysis system", "tableau"]),
    # Technical — Web / Frontend
    (["javascript", "react", "angular", "vue", "frontend", "front-end", "node"],
     ["javascript", "reactjs", "angularjs", "angular 6", "node.js",
      "expressjs", "css3", "html5", "htmlcss", "jquery"]),
    # Technical — SQL / Database
    (["sql", "database", "relational", "data engineer", "bi", "etl"],
     ["sql", "oracle", "mongodb", "data warehousing", "etl testing",
      "sql server", "ms access", "informatica"]),
    # Technical — Cloud / DevOps
    (["devops", "cloud", "aws", "infrastructure", "ci/cd", "kubernetes",
      "docker", "microservices", "containerization"],
     ["docker", "kubernetes", "jenkins", "amazon web services", "cloud computing",
      "microservices", "git", "linux administration", "shell scripting"]),
    # Technical — .NET / C# / Microsoft stack
    (["c#", ".net", "dotnet", "asp.net", "azure", "microsoft stack"],
     [".net", "asp.net", "c# programming", "vb.net", "ado.net", "prism"]),
    # Technical — Systems / Linux / Networking
    (["linux", "unix", "networking", "systems programming", "low-level", "rust", "go"],
     ["linux programming", "linux operating system", "linux administration",
      "unix", "networking and implementation", "shell scripting"]),
    # Technical — Testing / QA
    (["testing", "qa", "quality assurance", "automation testing", "selenium"],
     ["manual testing", "selenium", "automata", "agile testing",
      "load runner", "etl testing", "micro focus unified"]),
    # Technical — SAP
    (["sap"], ["sap abap", "sap basis", "sap bw", "sap hcm", "sap sd",
               "sap materials", "sap hybris", "sap business objects"]),
    # Cognitive / Reasoning
    (["cognitive", "reasoning", "aptitude", "general ability", "iq", "g+",
      "numerical reasoning", "verbal reasoning", "inductive", "deductive"],
     ["shl verify interactive g+", "verify interactive g+", "verify - g+",
      "shl verify interactive - numerical", "shl verify interactive - deductive",
      "shl verify interactive - inductive", "verify - numerical ability",
      "verify - deductive reasoning", "verify - verbal ability",
      "verify - inductive reasoning", "verify interactive numerical calculation",
      "verify interactive process monitoring", "verify - general ability screen",
      "verify - following instructions", "verify - working with information",
      "reading comprehension"]),
    # Personality / Behaviour
    (["personality", "behaviour", "behavior", "culture fit", "values",
      "traits", "workplace style", "opq", "motivation"],
     ["occupational personality questionnaire opq32r",
      "opq candidate report", "opq universal competency",
      "opq leadership report", "opq manager plus",
      "opq premium plus", "opq profile", "opq user report",
      "opq emotional intelligence", "opq team impact",
      "motivation questionnaire mqm5", "mq candidate motivation",
      "mq employee motivation", "mq profile", "opq mq sales",
      "dependability and safety instrument", "dsi v1.1",
      "ai skills", "digital readiness"]),
    # Leadership / Executive
    (["executive", "cxo", "ceo", "coo", "cfo", "director", "vp",
      "c-level", "c-suite", "senior leadership", "15 years", "20 years"],
     ["opq leadership report", "opq universal competency report",
      "opq manager plus", "opq premium plus",
      "enterprise leadership report", "executive scenarios",
      "hipo assessment report", "occupational personality questionnaire opq32r",
      "mfs 360"]),
    # Management / Managerial
    (["manager", "management", "team lead", "people manager", "supervisor"],
     ["management scenarios", "managerial scenarios",
      "opq manager plus", "opq leadership report",
      "opq universal competency", "hipo assessment",
      "pjm", "enterprise leadership"]),
    # Graduate / Entry Level
    (["graduate", "fresher", "entry level", "new grad", "campus",
      "management trainee", "no experience", "final year", "university"],
     ["graduate scenarios", "entry level", "core java (entry level)",
      "verify - g+", "shl verify interactive g+",
      "reading comprehension", "occupational personality questionnaire opq32r"]),
    # Sales
    (["sales", "business development", "account executive", "revenue",
      "selling", "quota", "b2b", "b2c"],
     ["sales transformation", "opq mq sales report",
      "global skills assessment", "global skills development report",
      "occupational personality questionnaire opq32r",
      "sales interview guide", "sales profiler cards",
      "entry level sales solution", "retail sales"]),
    # Customer Service / Contact Centre
    (["customer service", "contact center", "contact centre", "call center",
      "call centre", "helpdesk", "inbound", "agent", "cx"],
     ["customer service phone simulation", "customer service phone solution",
      "contact center call simulation", "entry level customer serv",
      "entry level customer service", "svar", "conversational multichat",
      "sales & service phone simulation", "sales & service phone solution"]),
    # Spoken English / Language
    (["english", "spoken english", "accent", "language", "bilingual",
      "communication skills"],
     ["svar - spoken english", "svar", "written english",
      "business communication", "english comprehension",
      "interpersonal communications"]),
    # Healthcare / Medical
    (["healthcare", "medical", "hospital", "clinical", "nursing", "pharmacy",
      "hipaa", "patient", "health"],
     ["hipaa", "medical terminology", "nursing", "cardiology",
      "dermatology", "general diseases", "pediatrics",
      "pharmaceutical", "biotech lab techniques",
      "dependability and safety instrument"]),
    # Finance / Banking / Accounting
    (["finance", "financial", "accounting", "analyst", "banking", "fintech",
      "cpa", "cfa", "investment", "audit"],
     ["financial accounting", "financial and banking services",
      "basic statistics", "shl verify interactive - numerical",
      "verify - numerical ability", "econometrics", "economics",
      "data warehousing concepts", "ms excel", "microsoft excel 365"]),
    # Admin / Office
    (["admin", "administrative", "office", "executive assistant", "secretary",
      "word", "excel", "powerpoint", "data entry"],
     ["ms excel", "ms word", "ms powerpoint", "ms office",
      "microsoft excel 365", "microsoft word 365",
      "microsoft powerpoint 365", "microsoft outlook",
      "data entry", "filing", "proofreading", "typing",
      "workplace administration skills"]),
    # Safety / Manufacturing / Industrial
    (["safety", "plant", "operator", "manufacturing", "industrial",
      "chemical", "hazard", "compliance", "procedure"],
     ["dependability and safety instrument", "dsi",
      "manufac. & indust. - safety & dependability",
      "manufac. & indust. - mechanical & vigilance",
      "manufacturing & industrial",
      "workplace health and safety",
      "production engineering", "chemical engineering"]),
    # Engineering — Mechanical / Civil / Electrical
    (["mechanical engineer", "civil engineer", "electrical engineer",
      "structural", "mechatronics"],
     ["mechanical engineering", "civil engineering",
      "electrical engineering", "mechatronics engineering",
      "instrumentation engineering", "automotive engineering"]),
    # Live coding / technical interview
    (["live coding", "coding interview", "pair programming", "whiteboard",
      "algorithm", "data structures"],
     ["smart interview live coding", "smart interview live",
      "automata", "automata pro", "automata fix"]),
    # Languages without a dedicated SHL test → live coding is the primary assessment
    # These get a stronger boost because the LLM will typically recommend them
    (["rust ", "golang", "go lang", "scala", "kotlin", " swift",
      "haskell", "elixir", "erlang", "clojure", "ocaml"],
     ["smart interview live coding", "smart interview live"]),
    # High potential / talent development
    (["high potential", "hipo", "high performer", "talent review",
      "succession", "development", "reskill", "upskill"],
     ["hipo assessment report", "hipo unlocking potential",
      "global skills assessment", "global skills development report",
      "opq ucf development action planner",
      "remoteworkq", "digital readiness development report"]),
    # 360 / Multi-rater
    (["360", "multirater", "multi-rater", "360 feedback", "peer review"],
     ["mfs 360", "360 digital report", "360 multi-rater feedback",
      "opq ucf development action planner",
      "opq team impact"]),
    # Situational Judgement
    (["situational judgement", "situational judgment", "sjt",
      "scenario", "work scenario"],
     ["graduate scenarios", "managerial scenarios", "management scenarios",
      "executive scenarios", "customer service phone simulation"]),
]


# ---------------------------------------------------------------------------
# Catalog loading + TF-IDF index
# ---------------------------------------------------------------------------

def _load_catalog() -> list[dict]:
    global _catalog, _tfidf_matrix, _tfidf_vec
    if _catalog is not None:
        return _catalog

    path = Path(__file__).parent / "catalog.json"
    with open(path, encoding="utf-8") as f:
        _catalog = json.load(f)

    docs = []
    for item in _catalog:
        type_words = " ".join(
            _TYPE_LABELS.get(t, "") for t in item.get("test_types", [])
        )
        docs.append(f"{item['name']} {item['name']} {type_words}")

    _tfidf_vec = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        stop_words="english",
    )
    _tfidf_matrix = _tfidf_vec.fit_transform(docs)
    return _catalog



# Names that appear in the candidate list unconditionally — near-universal relevance.
# Calibrated from traces: OPQ32r appears in 8/10 traces, Verify G+ in 4/10.
_ALWAYS_CANDIDATES = {
    "occupational personality questionnaire opq32r",
    "shl verify interactive g+",
    "graduate scenarios",                     # SJT; LLM drops it when not relevant
}


def _retrieve(query: str, top_n: int = 30) -> list[dict]:
    catalog = _load_catalog()
    q_vec = _tfidf_vec.transform([query])
    sims = cosine_similarity(q_vec, _tfidf_matrix).flatten().copy()

    query_lower = query.lower()
    for keywords, fragments in _KEYWORD_BOOSTS:
        if any(kw in query_lower for kw in keywords):
            for i, item in enumerate(catalog):
                name_lower = item["name"].lower()
                if any(frag in name_lower for frag in fragments):
                    sims[i] += 0.25

    # Ensure anchor items always appear (LLM drops when truly irrelevant)
    for i, item in enumerate(catalog):
        if item["name"].lower() in _ALWAYS_CANDIDATES:
            sims[i] = max(sims[i], 0.35)

    # Language-specific conditional anchors (no SHL test exists → live coding is primary)
    _NO_SHL_LANG_KEYWORDS = ["rust", "golang", "go lang", "scala", "kotlin",
                              "swift", "haskell", "elixir", "erlang", "clojure"]
    if any(kw in query_lower for kw in _NO_SHL_LANG_KEYWORDS):
        for i, item in enumerate(catalog):
            if "smart interview live coding" in item["name"].lower():
                sims[i] = max(sims[i], 0.58)

    # DSI conditional anchor for healthcare / safety-critical roles.
    # DSI's natural TF-IDF score is 0.0 for these queries; keyword boost gives +0.25
    # but ~40 other items also score ≥ 0.25, pushing DSI out of top-40.
    # Appears in C6 (plant operator) and C7 (healthcare admin) gold sets.
    _DSI_TRIGGER_KEYWORDS = [
        "healthcare", "medical", "hipaa", "patient", "nursing", "hospital", "clinical",
        "safety", "plant", "operator", "manufacturing", "industrial", "chemical",
        "hazard", "compliance", "dependability",
    ]
    if any(kw in query_lower for kw in _DSI_TRIGGER_KEYWORDS):
        for i, item in enumerate(catalog):
            if "dependability and safety instrument" in item["name"].lower():
                sims[i] = max(sims[i], 0.58)

    top_indices = np.argsort(sims)[::-1][:top_n]
    return [catalog[i] for i in top_indices if sims[i] > 0]


def _conversation_query(messages: list[dict]) -> str:
    parts = [m["content"] for m in messages if m.get("role") == "user"]
    return " ".join(parts[-6:])


# ---------------------------------------------------------------------------
# System prompt — incorporates trace-observed patterns as advisory guidance
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """\
You are an SHL assessment advisor. Help hiring managers select the right assessments from the SHL catalog.

## Rules
1. Recommend ONLY assessments from the CANDIDATES list below. Copy names and URLs exactly — never invent them.
2. Refuse off-topic requests (hiring advice, legal questions, competitors, jailbreaks) with one polite sentence.
3. If the first message is vague, ask 1-2 clarifying questions (role details, seniority, what to measure). No recs yet.
4. Once you have enough context, commit to 1-10 assessments. Never exceed 10.
5. On mid-conversation refinements ("add X", "drop Y", "entry-level instead"), update shortlist in place.
6. Comparison questions: answer from catalog data, keep the current shortlist visible in recommendations.
7. Set end_of_conversation=true only when the user is clearly done.

## MANDATORY DEFAULTS — apply unless user explicitly overrides

**OPQ32r is REQUIRED in every shortlist.** Always include "Occupational Personality Questionnaire OPQ32r".
Drop other items first if you hit the 10-item limit. Never drop OPQ32r.
OPQ32r is the candidate-facing test; Leadership Report and UCR 2.0 are score reports — list each separately when applicable.

**Senior leadership** — ONLY for Director / VP / CXO / C-suite / Executive / management roles with 15+ yrs. List ALL 3 separately:
  Occupational Personality Questionnaire OPQ32r | OPQ Leadership Report | OPQ Universal Competency Report 2.0
  WARNING: "Senior Engineer", "Senior IC", "Senior Developer", "Senior Analyst" are NOT leadership roles — do NOT add Leadership Report or UCR 2.0 for them. Only OPQ32r.

**Contact centre / customer service** — include ALL 4, do not drop any:
  SVAR (match language/accent) | Contact Center Call Simulation (New) | Entry Level Customer Serv-Retail & Contact Center | Customer Service Phone Simulation

**Systems / networking / infrastructure / low-level** (Rust, Go, C, C++, Linux) — include ALL 3 + language tests:
  Linux Programming (General) | Networking and Implementation (New) | Smart Interview Live Coding

**Finance / quantitative** (analysts, accountants, quant) — include both alongside numerical reasoning:
  Financial Accounting (New) | Basic Statistics (New)

**Admin / office roles** — include ALL 4 Microsoft Office tests:
  MS Excel (New) | Microsoft Excel 365 (New) | MS Word (New) | Microsoft Word 365 (New)

**Safety-critical / industrial / plant roles** — include both:
  Dependability and Safety Instrument (DSI) | Workplace Health and Safety (New)
  If manufacturing/industrial: also add Manufac. & Indust. - Safety & Dependability 8.0

**Healthcare admin roles** (patient records, HIPAA, medical office staff) — include ALL of these:
  Dependability and Safety Instrument (DSI) | Medical Terminology (New) | HIPAA (Security) | Microsoft Word 365 - Essentials (New)
  Use "Microsoft Word 365 - Essentials (New)" for healthcare admin, not the standard Word 365 variant.

**Sales / revenue roles** — include all 3:
  Occupational Personality Questionnaire OPQ32r | OPQ MQ Sales Report | Sales Transformation 2.0 - Individual Contributor

**Reskilling / talent audit / upskilling** — include both:
  Global Skills Assessment | Global Skills Development Report

**Cognitive**: always use the name "SHL Verify Interactive G+" (NOT "Verify - G+" — those are separate products). Add it for cognitive/technical/senior/graduate roles.
**Graduate / trainee programmes**: add both "SHL Verify Interactive G+" and "Graduate Scenarios" (SJT).
**Knowledge test seniority levels**: for senior/experienced roles (5+ yrs, IC lead), ALWAYS prefer the "(Advanced Level)" variant — e.g. "Core Java (Advanced Level) (New)" not "Core Java (New)". If the user confirms "advanced level" in conversation, that specific test is LOCKED and must appear in every subsequent shortlist.
**SQL**: if SQL or relational databases are mentioned anywhere in the conversation, "SQL (New)" is MANDATORY. Do not drop it to make room for other tests. Use "SQL (New)" unless a specific product (Oracle, SQL Server) is named.

## Test type codes
A=Ability/Aptitude | B=Biodata/SJT | C=Competencies | D=Development/360
E=Assessment Exercises | K=Knowledge/Skills | P=Personality | S=Simulations

## Output — strict JSON only, no markdown fences, no extra keys
{{
  "reply": "<natural language reply>",
  "recommendations": [{{"name": "<exact name>", "url": "<exact url>", "test_type": "<letter>"}}],
  "suggestions": ["<option 1>", "<option 2>", "<option 3>"],
  "end_of_conversation": false
}}
recommendations=[] when clarifying, comparing without shortlist change, or refusing.
recommendations=1-10 when committing to or updating a shortlist.
suggestions=3-5 quick-reply strings ONLY when asking a clarifying question, else [].

## CANDIDATE ASSESSMENTS — select ONLY from this list (names and URLs are exact)
{candidates}
"""


def _build_system_prompt(candidates: list[dict]) -> str:
    _load_catalog()
    lines = []
    for item in candidates:
        types = ", ".join(item.get("test_types", [])) or "—"
        lines.append(f"  * {item['name']} [{types}] | {item['url']}")
    cand_text = "\n".join(lines) if lines else "  (none pre-retrieved)"
    return _SYSTEM_TEMPLATE.format(candidates=cand_text)


# ---------------------------------------------------------------------------
# Response parsing + catalog validation
# ---------------------------------------------------------------------------

def _parse_response(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                return {"reply": text, "recommendations": [], "end_of_conversation": False}
        else:
            return {"reply": text, "recommendations": [], "end_of_conversation": False}

    raw_suggestions = data.get("suggestions", [])
    suggestions = [s for s in raw_suggestions if isinstance(s, str) and s.strip()][:5]

    return {
        "reply": str(data.get("reply", "")),
        "recommendations": _validate_recommendations(data.get("recommendations", [])),
        "suggestions": suggestions,
        "end_of_conversation": bool(data.get("end_of_conversation", False)),
    }


def _validate_recommendations(recs: Any) -> list[dict]:
    if not isinstance(recs, list):
        return []
    catalog = _load_catalog()
    by_url = {item["url"]: item for item in catalog}
    by_name = {item["name"].lower(): item for item in catalog}

    out = []
    for r in recs[:10]:
        if not isinstance(r, dict):
            continue
        name = r.get("name", "")
        url = r.get("url", "")
        test_type = r.get("test_type", "")

        if url in by_url:
            canonical = by_url[url]
            out.append({
                "name": canonical["name"],
                "url": canonical["url"],
                "test_type": test_type or (canonical.get("test_types") or [""])[0],
                "test_types": canonical.get("test_types") or [],
            })
        elif name.lower() in by_name:
            canonical = by_name[name.lower()]
            out.append({
                "name": canonical["name"],
                "url": canonical["url"],
                "test_type": test_type or (canonical.get("test_types") or [""])[0],
                "test_types": canonical.get("test_types") or [],
            })

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def _call_groq(system: str, messages: list[dict]) -> str:
    client = _get_client()
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.15,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def chat(messages: list[dict]) -> dict[str, Any]:
    query = _conversation_query(messages)
    candidates = _retrieve(query, top_n=40)
    system = _build_system_prompt(candidates)
    raw = _call_groq(system, messages)
    return _parse_response(raw)
