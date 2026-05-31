# symph-back-end

FastAPI backend for Symphony — Yuno's Agentic AI Orchestration Platform.

FastAPI + LangGraph + PostgreSQL, running in a Python virtualenv named `symphony`.

## Dev Commands

```bash
# One-time virtualenv setup
mkvirtualenv symphony
workon symphony
pip install -r requirements.txt

# Start dev server
workon symphony
fastapi dev app/main.py
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

Shut down with `Ctrl+C`.

## Source Layout

```
app/
  main.py          ← FastAPI app, router registration
  database.py      ← async SQLAlchemy engine and session factory
  dependencies.py  ← shared FastAPI dependencies (DB session, auth)
  routers/         ← route handlers grouped by domain
  schemas/         ← Pydantic request/response models
  models/          ← SQLAlchemy ORM models
alembic/           ← database migrations
  versions/        ← migration scripts
alembic.ini        ← Alembic configuration
requirements.txt
```

## Database Management

### Prerequisites

PostgreSQL must be running. Create the database once:

```bash
brew services restart postgresql
psql -U postgres
CREATE DATABASE symphony;
\q
```

### Environment Variable

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost/symphony"
```

If not set, the default above is used.

### Alembic Migrations

```bash
workon symphony

# Apply all pending migrations (run after first setup and after any schema change)
alembic upgrade head

# Create a new migration after changing SQLAlchemy models
alembic revision --autogenerate -m "describe_change"

# Check current migration state
alembic current

# View migration history
alembic history
```

### Schema Overview

| Table | Key columns |
|---|---|
| `agents` | id, name, model, description, system_prompt, tools (JSON), memory_enabled, status, created_at, updated_at |
| `workflows` | id, name, description, graph_definition (JSON), status, created_at, updated_at |
| `messages` | id, agent_id (FK), session_id, role, content, created_at |
| `logs` | id, agent_id (FK), workflow_id (FK), level, message, created_at |
| `agent_memory` | id, agent_id (FK), key, value, created_at, updated_at |

## API Overview

All endpoints are under `/api/v1` and require `Authorization: Bearer <token>`.
Auth is currently a stub — any non-empty token is accepted.

| Resource | Endpoints |
|---|---|
| Agents | GET/POST `/api/v1/agents`, GET/PUT/DELETE `/api/v1/agents/{id}` |
| Workflows | GET/POST `/api/v1/workflows`, GET/PUT/DELETE `/api/v1/workflows/{id}` |
| Messages | GET/POST `/api/v1/messages`, GET/DELETE `/api/v1/messages/{id}` |
| Logs | GET/POST `/api/v1/logs`, GET `/api/v1/logs/{id}` |
| Agent Memory | GET/POST `/api/v1/agents/{id}/memory`, GET/DELETE `/api/v1/agents/{id}/memory/{key}` |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost/symphony` | PostgreSQL async connection string |
| `ANTHROPIC_API_KEY` | — | Required. Anthropic API key for Claude models |
| `SLACK_BOT_TOKEN` | — | Slack bot token (`xoxb-...`) for Socket Mode |
| `SLACK_APP_TOKEN` | — | Slack app-level token (`xapp-...`) for Socket Mode |
| `LANGCHAIN_TRACING_V2` | `false` | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | — | LangSmith API key (get at smith.langchain.com) |
| `LANGCHAIN_PROJECT` | — | LangSmith project name (e.g. `symphony`) |

## Slack Integration

Symphony includes a Socket Mode Slack bot (`app/slack_bot.py`) that starts automatically with the FastAPI server.

### How it works

- Listens for **direct messages** (`message.im`) and **@mentions** (`app_mention`)
- Routes each message to the first agent whose `channels` JSONB list contains `"slack"`
- Falls back to `claude-haiku-4-5-20251001` with a default system prompt if no agent is configured
- Persists every user message and assistant reply to the `messages` table; the Slack channel ID is used as the `session_id`
- Gracefully disables itself if `SLACK_BOT_TOKEN` or `SLACK_APP_TOKEN` are not set

### Setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps) with **Socket Mode** enabled
2. Add bot scopes: `chat:write`, `im:history`, `app_mentions:read`
3. Subscribe to events: `message.im`, `app_mention`
4. Set the tokens:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-..."
   export SLACK_APP_TOKEN="xapp-..."
   ```
5. In the Symphony UI (Agent Configuration → Channels), add `slack` to the channels list for the agent that should handle Slack messages

---

## Observability — LangSmith Tracing

Symphony integrates with [LangSmith](https://smith.langchain.com) for deep LLM tracing. When enabled, every workflow run and Slack bot message is automatically traced — including full prompt/response content, token counts, cost, and per-node latency. No code changes are needed; tracing is entirely controlled by environment variables.

### Setup

1. Sign up at [smith.langchain.com](https://smith.langchain.com) and create a project named `symphony`
2. Go to **Settings → API Keys** and generate a new key
3. Add to your `.env` file:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_...
   LANGCHAIN_PROJECT=symphony
   ```
4. Restart the backend — tracing starts immediately on the next workflow run or Slack message

To disable tracing, set `LANGCHAIN_TRACING_V2=false` or remove the variable.

### What gets traced

| Trigger | What you see in LangSmith |
|---|---|
| Workflow run (any node with an Agent) | Full LangGraph run tree, per-node latency, Claude prompt + response |
| Slack message | Single LLM call with system prompt, user message, and reply |

### Viewing traces

1. Open [smith.langchain.com](https://smith.langchain.com) and select the **symphony** project
2. The **Traces** tab lists every run in reverse-chronological order
3. Click a trace to expand the full call tree — each node shows input, output, token usage, latency, and cost
4. Use the **Filter** bar to search by status, model, latency, or date range

### Local logs

All run events are also persisted to the local `logs` table and visible in the Symphony UI under **Logs**.
