# Campus Compass 🧭

An evidence-backed university advisor for international students applying to US universities.

## What It Does

Campus Compass helps international students research, compare, and shortlist US universities
by combining real data from federal databases, university websites, and student communities.

Ask it anything:
- "Find affordable MS CS programs that don't require GRE"
- "Compare Georgia Tech and UIUC for electrical engineering"
- "What are my chances at MIT with a 3.8 GPA and 330 GRE?"
- "How much does it cost to live in Boston as a student?"
- "What do students say about life at Purdue?"

## Architecture

No database. No pre-built dataset. Just a smart orchestration layer:

```
Student → Chat UI (Next.js) → FastAPI → Claude (with 5 real-time tools)
                                              ↓
                               ┌──────────────────────────┐
                               │  📊 College Scorecard    │ federal university data
                               │  📄 Page Fetcher         │ scrapes official program pages
                               │  🌐 Web Search           │ current info via DuckDuckGo
                               │  💰 Cost of Living       │ student living cost estimates
                               │  💬 Reddit Search        │ real student discussions
                               └──────────────────────────┘
```

Every response cites its sources. Official data is clearly separated from community opinions.

---

## Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/ghopgaurav/campusAdvisor
cd campusAdvisor/campus-compass

# Add your API keys
cp backend/.env.example backend/.env
# Edit backend/.env with your AWS and Scorecard keys

# Start the full stack
docker compose up --build

# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

### Option B — Local development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys

uvicorn app.main:app --reload
# → http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm install
# .env.local already points to http://localhost:8000/api
npm run dev
# → http://localhost:3000
```

---

## Environment Variables

Create `backend/.env` from the example:

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | ✅ | AWS access key (for Bedrock) |
| `AWS_SECRET_ACCESS_KEY` | ✅ | AWS secret key (for Bedrock) |
| `AWS_REGION` | ✅ | AWS region (default: `us-east-1`) |
| `SCORECARD_API_KEY` | ✅ | Free at [api.data.gov](https://api.data.gov/signup/) |
| `ANTHROPIC_MODEL` | optional | Bedrock model ID (default: Claude Sonnet) |
| `MAX_TOOL_CALLS_PER_TURN` | optional | Default: 15 |
| `LOG_LEVEL` | optional | Default: `INFO` |

### Getting API Keys

**AWS Bedrock (for Claude):**
1. Create an AWS account at [aws.amazon.com](https://aws.amazon.com)
2. Enable Claude model access in the [Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess)
3. Create an IAM user with `AmazonBedrockFullAccess` policy
4. Generate access keys under IAM → Security credentials

**College Scorecard:**
1. Sign up (free, instant) at [api.data.gov/signup](https://api.data.gov/signup/)
2. The key is emailed within a few minutes

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/test` | Lists all registered tools |
| `POST` | `/api/chat` | Send a message to the advisor |

**Example chat request:**
```json
POST /api/chat
{
  "message": "Find affordable CS programs in California",
  "student_profile": {
    "gpa": 3.5,
    "degree_target": "MS",
    "field_target": "Computer Science",
    "budget_total_usd": 50000,
    "needs_funding": false
  },
  "conversation_history": []
}
```

**Response:**
```json
{
  "response": "Based on College Scorecard data, here are the most affordable...",
  "tools_used": [
    { "tool_name": "search_us_universities", "query": "CS programs CA" }
  ],
  "follow_up_suggestions": [
    "What about living costs in Los Angeles?",
    "How competitive is my profile for these programs?"
  ]
}
```

---

## Running Tests

```bash
# Make sure the backend is running first
cd backend
source .venv/bin/activate

# Backend integration tests (6 tests, ~3 minutes)
python test_backend.py

# Individual tool tests
python test_scorecard.py
python test_page_fetcher.py
```

---

## Project Structure

```
campus-compass/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Settings (pydantic-settings)
│       ├── routers/
│       │   └── chat.py          # POST /api/chat, GET /api/test
│       ├── schemas/
│       │   └── chat.py          # Pydantic request/response models
│       ├── orchestrator/
│       │   ├── agent.py         # CampusCompassAgent — main loop
│       │   ├── tool_registry.py # ToolRegistry — wires all tools
│       │   └── system_prompt.py # The full agent persona & instructions
│       └── tools/
│           ├── scorecard.py         # College Scorecard API
│           ├── page_fetcher.py      # URL fetch + AI extraction
│           ├── web_search.py        # DuckDuckGo search
│           ├── cost_of_living.py    # City cost estimates
│           └── reddit_search.py     # Reddit via DDG site: filter
└── frontend/
    ├── Dockerfile
    ├── next.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   └── page.tsx
        ├── components/
        │   ├── ChatWindow.tsx
        │   ├── MessageBubble.tsx    # Renders markdown, tool badges, suggestions
        │   ├── InputBar.tsx
        │   ├── ProfilePanel.tsx     # Student profile (saved to localStorage)
        │   ├── ToolBadge.tsx
        │   ├── SuggestionChips.tsx
        │   └── WelcomeScreen.tsx
        ├── hooks/
        │   └── useChat.ts           # Chat state + conversation history
        └── lib/
            ├── api.ts
            └── types.ts
```

---

## How the Agent Works

1. **Student sends a message** — optionally with their profile (GPA, scores, budget, etc.)
2. **Claude reads the system prompt** — which defines its persona, tool-use philosophy, and how to handle different question types
3. **Claude decides which tools to call** — often chains multiple tools (Scorecard → page fetch → Reddit)
4. **Each tool runs with a 30s timeout** — errors are returned as structured messages so Claude can gracefully recover
5. **Claude synthesizes a final response** — citing sources, separating official data from community opinions
6. **Response includes follow-up suggestions** — generated from keywords in the response

The agent is capped at 15 tool calls per turn to prevent runaway loops.
