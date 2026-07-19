# AcadEase AI (LangGraph edition)

AI-powered multi-agent academic assistant for **GNDU MCA students**, built on
**LangGraph**, using your real catalog data (84 subjects, 26 note sets, 31
PYQs, 30 topics of curated resources).

## Graph

```
START -> router -> notes ──────┐
              └──> pyq ────────┼──(empty result?)──> recommender -> END
              └──> guidance ───────────────────────────────────────> END
              └──> recommendation ─────────────────────────────────> END
              └──> general ────────────────────────────────────────> END
```

`router` classifies intent (`notes` / `pyq` / `guidance` / `recommendation` /
`general`) and extracts subject/semester/exam type via Grok, with a keyword
fallback if the LLM is unreachable. `notes` and `pyq` conditionally hand off
to `recommender` when the catalog has nothing for that subject — the
assistant never just says "not found."

## Why a resolver, not just filtering

Your six data files don't use perfectly consistent subject naming — verified
directly against the uploaded data. For example **"Cloud Computing"** has
notes, PYQs, and curated resources, but no entry at all in `aliases.json` or
`subjects.json`. So `data_loader.py` resolves free text against a pool built
from *all* the files (aliases + notes subjects + pyq subjects + resource
topics), not just `aliases.json` alone, then falls back to TF-IDF similarity
if nothing matches directly.

## Project layout

```
backend/
  app.py                 FastAPI entrypoint, invokes the compiled graph
  graph.py                LangGraph StateGraph: nodes + conditional edges
  state.py                AgentState TypedDict shared across nodes
  router.py               Router node (intent + entity extraction)
  notes_agent.py           Notes node
  pyq_agent.py              PYQ node
  guidance_agent.py         Guidance node (study plan generation)
  recommender_agent.py      Recommender node (curated + LLM-suggested)
  general_agent.py          Greeting/fallback node
  data_loader.py            loads your JSON files, subject resolution, search
  llm_client.py              Grok (xAI) API wrapper
  config.py
  data/
    aliases.json    (your data — subject_code/name/aliases)
    courses.json    (your data — MCA/IMCA/PGDCA/PGDAI/DCA)
    subjects.json   (your data — 84 subjects w/ semester, course, dept)
    notes.json      (your data — 26 note sets)
    pyqs.json       (your data — 31 previous year papers)
    resources.json  (your data — 30 topics of YouTube/books/websites/practice)
  requirements.txt
  .env.example
  render.yaml
frontend/
  src/                     React (Vite) chat UI
  vercel.json
  .env.example
```

## 1. Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GROK_API_KEY=<your xAI API key>
python -m uvicorn app:app --reload --port 8000
```
 
Check it: `curl http://localhost:8000/health` — should report your real
counts (84 subjects, 26 notes, 31 pyqs, 30 resource topics).

## 2. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## 3. Try it

- "DBMS notes" → Notes Agent, metadata match
- "PYQs for cloud computing" → PYQ Agent, metadata match (Sem 3, Mid + Final)
- "help me prepare for my DAA exam in a week" → Guidance Agent, grounded with
  DAA's real semester/course from `subjects.json`
- "notes for human values" → Notes Agent finds nothing (no notes.json entry)
  → auto hands off to Recommender Agent

## 4. Deploy

**Backend → Render**: connect the repo, root directory `backend`,
`render.yaml` is already set up — add your `GROK_API_KEY` secret in the
Render dashboard, then update `CORS_ORIGINS` once you have the frontend URL.

**Frontend → Vercel**: root directory `frontend`, set `VITE_API_BASE_URL` to
your Render backend URL.

## Extending

- **New subjects**: add entries to `aliases.json` (or just add notes/pyqs —
  the resolver picks up subject names directly from those files too).
- **New notes/PYQs**: append to `notes.json` / `pyqs.json` following the
  existing shape; `file_path` should point wherever you end up hosting the
  actual PDFs.
- **Real embeddings instead of TF-IDF**: swap the vectorizer setup inside
  `data_loader.py` — the agent nodes don't need to change.
- **LangGraph checkpointing / memory across sessions**: not wired in yet;
  `graph.compile()` in `graph.py` is where you'd add a checkpointer
  (e.g. `MemorySaver`) if you want persistent multi-turn state server-side
  instead of the frontend resending history each turn.

## Notes on the Grok integration

`llm_client.py` talks to xAI's OpenAI-compatible endpoint
(`https://api.x.ai/v1/chat/completions`). Change `GROK_MODEL` in `.env` to
rotate models — nothing else changes.

## What I verified without a live LLM key

I don't have your Grok API key or network access in this sandbox, so I
couldn't run the LLM-dependent nodes (router's classification, guidance
plans, LLM-suggested resources) end-to-end. I did directly test, against
your real uploaded data:
- subject resolution for informal queries (`"daa"`, `"cloud computing pyqs"`,
  `"ml"`, `"nlp mid sem"`, etc.) — including catching and fixing a bug where
  a short alias ("cloud") was winning over the more specific "Cloud
  Computing" match
- the Notes and PYQ nodes' metadata filtering end-to-end
- the general/greeting node
- a subject-context lookup bug where a subject offered under two different
  programs (`CSL4050` appears for both `MCA_TYP` and a `MCA_FYC` course_id
  that doesn't exist in `courses.json`) was silently dropping course info

All Python files pass a syntax compile check; do a real run-through once
your Grok key is in place, and let me know if anything surfaces.
