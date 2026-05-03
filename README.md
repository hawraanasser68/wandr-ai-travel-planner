# Wandr — AI Travel Planner

An AI-powered travel planning assistant built with a LangGraph multi-step agent, RAG-based destination knowledge, an ML travel-style classifier, and a streaming React frontend.

---

## What It Does

You type a query like *"I want an adventure trip under $100/day, family-friendly"*. The agent:

1. **Classifies** your travel style (Adventure, Relaxation, Culture, Budget, Luxury, or Family) using a trained ML model
2. **Retrieves** relevant destination knowledge from a pgvector database (RAG)
3. **Fetches** live weather and currency exchange rates if needed
4. **Synthesises** a full, formatted travel plan using a powerful LLM

Everything streams token-by-token to the browser in real time.

---

## Architecture

```
Browser (React + Vite)
    │  SSE stream
    ▼
FastAPI  ──►  LangGraph Agent
                │
                ├─► ML Classifier (scikit-learn)   → travel style label
                ├─► RAG Retriever (pgvector)        → destination knowledge
                ├─► Weather Tool (Open-Meteo, free) → live conditions
                └─► Currency Tool (Frankfurter ECB) → exchange rates
                │
                └─► Synthesis LLM → final travel plan
```

**Two-model routing** keeps costs low: a fast/cheap model (Llama 3.1 8B or Gemini Flash) drives the ReAct tool loop; a larger model (Llama 3.3 70B or Gemini Pro) writes the final answer only once.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Zustand, Leaflet |
| Backend | FastAPI, Uvicorn, SQLAlchemy (async) |
| Agent | LangGraph, LangChain |
| LLM | Groq (Llama 3.1/3.3) or Google Gemini |
| ML Classifier | scikit-learn (Random Forest, ~96-100% F1) |
| RAG | pgvector, sentence-transformers (`all-MiniLM-L6-v2`) |
| Database | PostgreSQL 16 + pgvector extension |
| Auth | JWT + bcrypt |
| Email | Resend API |
| Deployment | Docker Compose, nginx |

---

## Quick Start (Docker — recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A free [Groq API key](https://console.groq.com) (no credit card required)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/hawraanasser68/wandr-ai-travel-planner.git
cd wandr-ai-travel-planner

# 2. Create backend/.env from the example
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in at minimum:

```env
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
GROQ_API_KEY=gsk_...
```

```bash
# 3. Build and start everything
docker-compose up --build
```

| URL | Service |
|---|---|
| http://localhost | React frontend |
| http://localhost:8000/docs | FastAPI Swagger UI |
| http://localhost:5432 | PostgreSQL (if needed) |

On first boot the app automatically:
- Runs Alembic migrations (creates all tables)
- Ingests travel documents into pgvector

---

## Local Development (no Docker)

### Prerequisites
- Python 3.11+, Node 20+
- PostgreSQL 14+ with the [pgvector extension](https://github.com/pgvector/pgvector#installation)

### Backend

```bash
cd backend

# Install dependencies (using uv — fast)
pip install uv
uv venv && source .venv/bin/activate
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your keys

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # Vite dev server on http://localhost:5173
```

The Vite config proxies `/auth` and `/agent` to `localhost:8000` automatically — no CORS issues.

---

## Test Directly from GitHub (Codespaces)

GitHub Codespaces gives you a full cloud development environment in your browser — no local install needed.

### Setup

1. Go to the repo on GitHub
2. Click the green **Code** button → **Codespaces** tab → **Create codespace on mainn**
3. Wait ~2 minutes for the container to build
4. When the terminal opens, add your secrets:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env in the built-in VS Code editor
# Set JWT_SECRET_KEY and GROQ_API_KEY at minimum
```

5. Start the app:

```bash
docker-compose up --build
```

6. Codespaces will show a **"Open in Browser"** popup for ports 80 (frontend) and 8000 (API).

### Adding Secrets Permanently (Optional)

So you don't re-enter keys each time:

1. GitHub → Your profile → **Settings** → **Codespaces** → **Secrets**
2. Add `GROQ_API_KEY`, `JWT_SECRET_KEY`, etc.
3. Link them to this repository

They'll be injected as environment variables automatically next time you open a Codespace.

---

## Environment Variables

All config lives in `backend/.env`. Copy from `backend/.env.example`.

### Required

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Random 32-byte hex string for signing JWTs |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` (default) |
| `GOOGLE_API_KEY` | Required when `LLM_PROVIDER=gemini` |

### LLM Provider

```env
LLM_PROVIDER=groq          # "groq" (default, free) or "gemini"

# Groq models (free tier at console.groq.com)
FAST_MODEL=llama-3.1-8b-instant       # ReAct loop (speed)
SYNTH_MODEL=llama-3.3-70b-versatile   # Final synthesis (quality)

# Gemini models (free tier at aistudio.google.com)
# FAST_MODEL=gemini-1.5-flash
# SYNTH_MODEL=gemini-1.5-pro
```

### Optional APIs (all free tiers)

| Variable | Service | Used For |
|---|---|---|
| `OPENWEATHERMAP_API_KEY` | openweathermap.org | Weather (app works without it) |
| `RESEND_API_KEY` | resend.com | Email travel plan to user |
| `LANGCHAIN_API_KEY` | smith.langchain.com | LangSmith tracing (debug) |

---

## API Endpoints

### Auth

```
POST /auth/register    { email, password, webhook_email? }  → { token }
POST /auth/login       { email, password }                  → { token }
GET  /auth/me                                               → { id, email }
```

### Agent

```
POST /agent/chat               → SSE stream of chunks
GET  /agent/runs               → list of past runs (paginated)
GET  /agent/runs/{id}          → single run with full response
POST /agent/runs/{id}/email    → email the plan to user's webhook_email
```

#### Chat request body

```json
{
  "query": "I want a relaxing beach holiday under $150/day",
  "history": [],
  "country": "Unknown",
  "avg_cost_per_day": 150.0,
  "family_friendly": false
}
```

#### SSE stream format

Each event is a JSON line:

```
data: {"type": "token",       "content": "Here are"}
data: {"type": "tool_call",   "content": "rag_retriever"}
data: {"type": "tool_result", "content": "Bali, Santorini..."}
data: {"type": "done",        "content": "", "run_id": "uuid"}
data: {"type": "error",       "content": "message"}
```

---

## Project Structure

```
wandr-ai-travel-planner/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, CORS
│   │   ├── config.py            # All settings via pydantic-settings
│   │   ├── routers/             # auth.py, agent.py
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph: ReAct loop + synthesis
│   │   │   ├── prompts.py       # System prompts
│   │   │   └── tools/           # classifier, rag, weather, currency
│   │   ├── rag/                 # ingestion.py, retriever.py, embedder.py
│   │   ├── database/            # SQLAlchemy ORM models
│   │   ├── services/            # agent_runner, auth, webhook
│   │   └── schemas/             # Pydantic request/response models
│   ├── classifier/              # ML model: train, inference, transforms
│   ├── artifacts/               # Trained model files (.joblib)
│   ├── rag_documents/           # destinations.json (knowledge base)
│   ├── alembic/                 # Database migrations
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/               # Chat, History, Login, Register
│   │   ├── components/          # MapPanel, MarkdownRenderer, etc.
│   │   ├── api/client.ts        # Fetch wrappers + SSE streaming
│   │   └── store/               # Zustand: auth, chat state
│   ├── nginx.conf
│   └── Dockerfile
├── training/                    # Dataset builder + validation scripts
├── docker-compose.yml
└── .devcontainer/               # GitHub Codespaces config
    └── devcontainer.json
```

---

## ML Classifier

The classifier predicts one of 6 travel styles from user input:

**Adventure · Relaxation · Culture · Budget · Luxury · Family**

Trained on 158 destinations using a scikit-learn pipeline:

- Text (`description` + `key_activities`) → TF-IDF (300 features)
- Numeric (`avg_cost_per_day`) → StandardScaler
- Categorical (`country`) → OneHotEncoder

Three models were tested (Logistic Regression, Random Forest, SVC); Random Forest achieved the best F1. The trained model lives in `backend/artifacts/`.

To retrain:

```bash
cd backend
python classifier/train.py
```

---

## RAG System

10 curated destinations (Bali, Queenstown, Florence, Kyoto, Lisbon, Bangkok, Maldives, Dubai, Patagonia, Santorini) are stored as vector embeddings in pgvector.

Each destination has multiple document sections: `understand`, `do`, `eat`, `sleep`, `buy`, `practical`.

**Retrieval flow:**
1. Embed the user query with `all-MiniLM-L6-v2` (384 dimensions)
2. If ML confidence > 0.7: filter by `travel_style` before cosine similarity search
3. Return top-5 chunks to the agent

Documents are ingested automatically on startup from `backend/rag_documents/destinations.json`.

---

## Contributing

1. Fork the repo and create a feature branch
2. Run `docker-compose up --build` to start locally
3. Backend auto-reloads on file changes (Uvicorn `--reload`)
4. Frontend hot-reloads via Vite HMR
5. Open a PR against `mainn`
