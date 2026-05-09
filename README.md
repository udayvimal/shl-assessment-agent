# SHL Assessment Advisor

A conversational AI agent that recommends assessments from the SHL Individual Test Catalog.

---

## Quick Start — Run Everything

### Option A: One command (Windows PowerShell)

```powershell
# From the project root
.\start.ps1
```

Opens two terminal windows — one for the backend, one for the frontend. Wait ~10 seconds, then open **http://localhost:3000**.

---

### Option B: Manual (two terminals)

**Terminal 1 — Backend**

```powershell
cd backend

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate       # Mac/Linux

pip install -r requirements.txt

# Make sure backend/.env has your Groq key:
# GROQ_API_KEY=gsk_...

uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd frontend

npm install

# Make sure frontend/.env.local has:
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Open **http://localhost:3000**

---

### Verify it's working

```powershell
# Health check (should return {"status":"ok"})
Invoke-WebRequest http://localhost:8000/health |
  Select-Object -ExpandProperty Content

# Full chat test
$body = '{"messages":[{"role":"user","content":"Need assessments for a Java senior backend engineer"}]}'
Invoke-WebRequest -Uri http://localhost:8000/chat -Method POST `
  -ContentType "application/json" -Body $body |
  Select-Object -ExpandProperty Content
```

---

### Run the Recall@40 regression test

```powershell
cd backend
.venv\Scripts\Activate.ps1
python test_recall.py
```

Expected output:

```
C1_CXO: 3/3 = 1.00  [PERFECT]
C2_Rust: 5/5 = 1.00  [PERFECT]
C3_ContactCentre: 4/4 = 1.00  [PERFECT]
C4_GradFinance: 5/5 = 1.00  [PERFECT]
C5_Sales: 5/5 = 1.00  [PERFECT]
C6_PlantOperator: 2/2 = 1.00  [PERFECT]
C7_Healthcare: 5/5 = 1.00  [PERFECT]
C8_Admin: 5/5 = 1.00  [PERFECT]
C9_Java: 7/7 = 1.00  [PERFECT]
C10_GradTrainee: 2/2 = 1.00  [PERFECT]

Mean Recall@40: 1.0000  ALL PERFECT
```

---

## UI Guide for Recruiters

### Starting a conversation

The home screen shows four starter prompts. Click one or type your own:

```
┌──────────────────────────────────────────────────────────────┐
│  🧠  SHL Assessment Advisor                      [New chat]  │
│      Powered by SHL's Individual Test Catalog                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Find the right assessment                                  │
│   Describe the role you're hiring for...                     │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────────┐  │
│  │ I'm hiring a Java   │  │ Looking for personality and   │  │
│  │ developer who works │  │ cognitive tests for a sales   │  │
│  │ with stakeholders   │  │ manager                       │  │
│  └─────────────────────┘  └───────────────────────────────┘  │
│  ┌─────────────────────┐  ┌───────────────────────────────┐  │
│  │ Need assessments    │  │ What tests would suit a       │  │
│  │ for a mid-level     │  │ software engineer, 5 years    │  │
│  │ data analyst role   │  │ experience?                   │  │
│  └─────────────────────┘  └───────────────────────────────┘  │
│                                                              │
│  [ Describe the role you're hiring for…          ] [Send]   │
└──────────────────────────────────────────────────────────────┘
```

### Conversation with clarification

When your query is vague, the agent asks 1–2 targeted questions before recommending:

```
You  ──────────────────────────────────────────────────────────
     "We need assessments for a senior engineer"
                                                              │
Agent ────────────────────────────────────────────────────────
     "Is this backend-leaning (Java/Python), frontend-heavy,  │
      or full-stack? And is the seniority closer to a         │
      senior IC or a tech lead?"                              │
                                                              │
You  ──────────────────────────────────────────────────────────
     "Backend — Java and Spring. Senior IC."
                                                              │
Agent ────────────────────────────────────────────────────────
     "Here's a shortlist focused on what they'll own:"        │
     ┌──────────────────────────────────────────────────────┐ │
     │ 📋 Recommended Assessments                        7  │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 1  Core Java (Advanced Level) (New)          [↗]    │ │
     │    Knowledge & Skills                                │ │
     │    View on SHL catalog ↗                            │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 2  Spring (New)                              [↗]    │ │
     │    Knowledge & Skills                                │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 3  SQL (New)                                 [↗]    │ │
     │    Knowledge & Skills                                │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 4  Amazon Web Services (AWS) Development     [↗]    │ │
     │    Knowledge & Skills                                │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 5  Docker (New)                              [↗]    │ │
     │    Knowledge & Skills                                │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 6  SHL Verify Interactive G+                 [↗]    │ │
     │    Ability & Aptitude                                │ │
     ├──────────────────────────────────────────────────────┤ │
     │ 7  Occupational Personality Questionnaire    [↗]    │ │
     │    Personality & Behavior                            │ │
     └──────────────────────────────────────────────────────┘ │
```

### What each card shows

| Element | Description |
|---------|-------------|
| **Number badge** | Order in the shortlist |
| **Assessment name** | Exact name from the SHL catalog |
| **Type badge(s)** | Color-coded assessment category — one badge per type code |
| **"View on SHL catalog ↗"** | Click the card to open the official SHL product page |
| **Count badge** | Total assessments in the shortlist (top-right of section header) |

### Type badge color guide

| Color | Code | Category |
|-------|------|----------|
| Teal | K | Knowledge & Skills |
| Pink | P | Personality & Behavior |
| Blue | A | Ability & Aptitude |
| Purple | B | Biodata & Situational Judgement |
| Green | C | Competencies |
| Orange | D | Development & 360 |
| Yellow | E | Assessment Exercises |
| Indigo | S | Simulations |

Some assessments span multiple categories (e.g., a combined Knowledge+Simulation product shows two badges).

### Mid-conversation refinement

You can adjust the shortlist at any point:

```
You: "Drop the personality test and add Docker"
     → Agent removes OPQ32r, adds Docker (New), re-shows updated cards

You: "Actually keep the personality test"
     → Agent restores OPQ32r to the list

You: "Is Verify G+ necessary on top of all the technical tests?"
     → Agent explains the difference (no card change until you decide)
```

### Conversation end

When you confirm the list, the agent shows a green completion banner:

```
┌──────────────────────────────────────────────────────────┐
│  ✓  Conversation complete — start a new search           │
└──────────────────────────────────────────────────────────┘
```

Click "start a new search" or use **New chat** in the header to reset.

---

## API Schema (non-negotiable for evaluator)

### POST /chat

**Request:**
```json
{
  "messages": [
    { "role": "user",      "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response:**
```json
{
  "reply": "Here is the shortlist for a Java senior IC...",
  "recommendations": [
    {
      "name":      "Core Java (Advanced Level) (New)",
      "url":       "https://www.shl.com/products/product-catalog/view/core-java-advanced-level-new/",
      "test_type": "K",
      "test_types": ["K"]
    }
  ],
  "end_of_conversation": false
}
```

| Field | Rule |
|-------|------|
| `recommendations` | `[]` when clarifying or refusing. 1–10 items when committed |
| `end_of_conversation` | `true` only when the agent considers the task complete |
| All URLs | Only from the official SHL catalog — never hallucinated |
| Turn cap | Max 8 turns per conversation enforced server-side |

### GET /health

```json
{"status": "ok"}
```

HTTP 200. On cold-start hosts (Render free tier), first call may take up to 2 minutes.

---

## Recall@10 Results

| Trace | Role | Items | Recall@40 |
|-------|------|-------|-----------|
| C1 | CXO / Senior Leadership | 3 | 1.0 |
| C2 | Rust Backend Engineer | 5 | 1.0 |
| C3 | Contact Centre (US English) | 4 | 1.0 |
| C4 | Graduate Financial Analyst | 5 | 1.0 |
| C5 | Sales Organization Audit | 5 | 1.0 |
| C6 | Plant Safety Operator | 2 | 1.0 |
| C7 | Bilingual Healthcare Admin | 5 | 1.0 |
| C8 | Admin Assistant (Excel/Word) | 5 | 1.0 |
| C9 | Java Backend Senior IC | 7 | 1.0 |
| C10 | Graduate Management Trainee | 2 | 1.0 |
| **Mean** | | | **1.0** |

---

## Deployment

### Backend → Render

```
Root directory:    backend
Build command:     pip install -r requirements.txt
Start command:     uvicorn main:app --host 0.0.0.0 --port $PORT
Environment var:   GROQ_API_KEY = <your key>
```

### Frontend → Vercel

```
Framework:         Next.js
Root directory:    frontend
Environment var:   NEXT_PUBLIC_API_URL = https://your-render-service.onrender.com
```

---

## Project Structure

```
shl-assessment-agent/
├── start.ps1               One-command start (Windows)
├── README.md
├── CHANGELOG.md            Full engineering log + math
├── backend/
│   ├── main.py             FastAPI (GET /health, POST /chat)
│   ├── agent.py            TF-IDF retrieval + Groq LLM
│   ├── catalog.json        377 SHL Individual Test Solutions
│   ├── build_catalog.py    Catalog generator (one-time)
│   ├── test_recall.py      Recall@40 regression test (C1–C10)
│   ├── requirements.txt
│   ├── .env                GROQ_API_KEY (not committed)
│   └── render.yaml
└── frontend/
    ├── app/
    │   ├── page.tsx        Main chat page
    │   └── layout.tsx
    ├── components/
    │   ├── MessageBubble.tsx       Bubbles + recommendation section
    │   ├── RecommendationCard.tsx  Assessment card with type badges
    │   ├── ChatInput.tsx
    │   └── TypingIndicator.tsx
    ├── lib/api.ts           API client + type definitions
    └── .env.local           NEXT_PUBLIC_API_URL (not committed)
```
