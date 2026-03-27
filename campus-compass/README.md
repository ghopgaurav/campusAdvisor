# Campus Compass

An AI-powered graduate school advisor that helps students research universities, compare programs, understand costs, and make informed decisions about their academic future.

## Architecture

```
campus-compass/
├── backend/        # FastAPI + Claude agent
└── frontend/       # Next.js chat UI (coming soon)
```

## Backend

The backend is a FastAPI application that wraps a Claude-powered agentic loop. Claude autonomously decides which tools to call (college scorecard, web search, Reddit, etc.) to answer student questions.

### Tools available to the agent

| Tool | Description |
|------|-------------|
| `college_scorecard` | Query the US Dept of Education College Scorecard API |
| `fetch_page` | Fetch and extract readable text from any university webpage |
| `web_search` | General web search for current info |
| `cost_of_living` | Look up living cost estimates for a city |
| `reddit_search` | Search Reddit/forums for student experiences |

### Setup

```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `SCORECARD_API_KEY` | College Scorecard API key (free at api.data.gov) |
| `ANTHROPIC_MODEL` | Model to use (default: `claude-sonnet-4-20250514`) |
| `MAX_TOOL_CALLS_PER_TURN` | Max tool calls per agent turn (default: 15) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Send a message to the advisor |

## Frontend

Next.js chat UI — coming soon.
