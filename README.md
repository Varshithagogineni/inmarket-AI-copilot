# Event Surge Activation Copilot

An AI-powered marketing activation platform that discovers real upcoming events via the Ticketmaster API and generates localized campaign recommendations — complete with briefs, copy, and AI-generated poster creatives via Google Gemini.

Built as a full-stack agentic application with a **LangChain agent** orchestrating the workflow through **tool calling**, an **MCP Server** wrapping the external APIs, and a **React chat UI** for conversational interaction.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Chat UI                        │
│              (Vite + TypeScript + react-markdown)        │
└──────────────────────┬──────────────────────────────────┘
                       │  /api/runs (Vite proxy)
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │          LangChain Agent (Gemini LLM)           │    │
│  │  Orchestrates workflow via tool calling:         │    │
│  │    search_events → rank → brief → copy → image  │    │
│  └─────────┬───────────────────────────────────────┘    │
│            │ calls tools                                 │
│  ┌─────────▼───────────────────────────────────────┐    │
│  │        Domain Services & Scoring Engine          │    │
│  │  Intent normalization, deterministic scoring,    │    │
│  │  brief/copy/image generation, refinement         │    │
│  └─────────┬───────────────────────────────────────┘    │
│            │                                             │
│  ┌─────────▼───────────────────────────────────────┐    │
│  │    Infrastructure Providers (Pluggable)          │    │
│  │  TicketmasterEventProvider ←→ Ticketmaster API   │    │
│  │  GeminiCreativeProvider   ←→ Gemini Image API    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  MCP Server (FastMCP)                    │
│  8 tools: search_events, get_event_details,             │
│  score_event_fit, rank_event_candidates,                │
│  generate_campaign_brief, generate_copy_variants,       │
│  generate_image_prompt, generate_draft_poster            │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **LangChain + Gemini Agent**: The LLM decides which tools to call and in what order, making the workflow truly agentic rather than a hardcoded pipeline. Falls back to deterministic orchestration if LangChain is unavailable.
- **MCP Server**: Wraps Ticketmaster and Gemini API calls as standardized MCP tools via FastMCP, enabling any MCP-compatible client to interact with the same capabilities.
- **Provider Pattern**: Event and creative providers are injected via factories — swap between `mock` and real APIs (`ticketmaster`/`gemini`) via environment variables.
- **Domain-Driven Design**: Business logic (scoring, briefs, copy) lives in `domain/` and `application/services/`, independent of HTTP framework or API clients.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, react-markdown |
| Backend | Python 3.12, FastAPI, Uvicorn |
| LLM Agent | LangChain, langchain-google-genai (Gemini 2.5 Flash) |
| MCP Server | FastMCP |
| Event API | Ticketmaster Discovery API v2 |
| Image Generation | Google Gemini 2.5 Flash Image |
| Persistence | File-based JSON storage |

---

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Node.js 18+** and npm
- **API Keys**:
  - [Ticketmaster API Key](https://developer.ticketmaster.com/) (free)
  - [Google Gemini API Key](https://aistudio.google.com/apikey) (free tier)

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Varshithagogineni/inmarket-AI-copilot.git
cd inmarket-AI-copilot
```

### 2. Create the `.env` file

Create a `.env` file in the project root:

```env
EVENT_PROVIDER=ticketmaster
TICKETMASTER_API_KEY=your_ticketmaster_api_key_here

CREATIVE_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

RUN_REPOSITORY=file
RUN_STORAGE_PATH=data/runs.json
PROMPT_VERSION=v1
```

### 3. Install Python dependencies

```bash
pip install fastapi uvicorn[standard] pydantic httpx python-dotenv langchain langchain-google-genai
```

### 4. Install frontend dependencies

```bash
cd apps/web
npm install
cd ../..
```

### 5. Install MCP server dependencies (optional)

```bash
pip install fastmcp
```

---

## Running the Application

### Start the API server

```bash
cd apps/api
python -m uvicorn app.main:app --port 8000
```

### Start the frontend dev server (in a separate terminal)

```bash
cd apps/web
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies `/api` requests to the backend on port 8000.

### Start the MCP server (optional, separate terminal)

```bash
cd apps/mcp
python -m app.server
```

---

## Usage

1. Open `http://localhost:5173` in your browser
2. Type a campaign request in the chat, for example:
   - *"Find events in Dallas this weekend for a beverage brand targeting families"*
   - *"Sports events in Austin next week for a snack brand"*
3. The LangChain agent will:
   - Search Ticketmaster for real events via tool calling
   - Score and rank them for brand/audience fit
   - Generate 2 full campaign recommendations with briefs, copy, and AI-generated poster images
4. Refine results by chatting naturally:
   - *"Make the headline more energetic"*
   - *"Change the image to be more colorful"*
   - *"Update the brief to focus on families"*

---

## Project Structure

```
├── apps/
│   ├── api/                    # FastAPI backend + LangChain agent
│   │   ├── app/
│   │   │   ├── api/routes/     # HTTP route handlers
│   │   │   ├── application/
│   │   │   │   ├── services/   # Business logic services
│   │   │   │   │   ├── agent_service.py    # LangChain agent orchestrator
│   │   │   │   │   ├── run_service.py      # Workflow lifecycle management
│   │   │   │   │   ├── intent_service.py   # Prompt normalization
│   │   │   │   │   ├── scoring_service.py  # Event scoring engine
│   │   │   │   │   ├── brief_service.py    # Brief/copy/image generators
│   │   │   │   │   └── refinement_service.py
│   │   │   │   ├── serializers.py
│   │   │   │   └── orchestrators/
│   │   │   ├── config/         # Environment settings
│   │   │   ├── domain/models.py # Core domain dataclasses
│   │   │   └── infra/          # Provider implementations
│   │   │       ├── providers/  # Ticketmaster, Gemini, Mock
│   │   │       └── repositories/
│   │   └── pyproject.toml
│   ├── web/                    # React frontend
│   │   ├── src/
│   │   │   ├── App.tsx         # Chat UI + conversation logic
│   │   │   ├── components/     # ChatMessage, ChatInput, Sidebar
│   │   │   ├── types.ts        # TypeScript type definitions
│   │   │   └── styles.css      # Full design system
│   │   └── package.json
│   └── mcp/                    # FastMCP server
│       ├── app/
│       │   ├── server.py       # MCP tool registration
│       │   ├── tools/          # Event, strategy, creative tools
│       │   ├── clients/        # Ticketmaster, Gemini HTTP clients
│       │   └── schemas.py
│       └── pyproject.toml
├── .env                        # API keys (not committed)
└── .gitignore
```

---

## LangChain Agent Details

The LangChain agent (`agent_service.py`) uses **Google Gemini 2.5 Flash** as the LLM with **tool calling** to orchestrate the activation workflow:

### Tools (mirroring MCP Server)

| Tool | Description |
|------|-------------|
| `search_events` | Search Ticketmaster for events by city + timeframe |
| `rank_event_candidates` | Score and rank events against campaign intent |
| `generate_campaign_brief` | Create campaign strategy for a selected event |
| `generate_copy_assets` | Generate headline, caption, CTA, promo text |
| `generate_image_concept` | Create image prompt and style notes |
| `generate_draft_poster` | Generate poster image via Gemini |

### Agent Flow

The agent receives the user's campaign request and autonomously decides the tool-calling sequence:

1. Calls `search_events` with city and timeframe
2. Calls `rank_event_candidates` with the normalized intent
3. For top 2 events: calls `generate_campaign_brief` → `generate_copy_assets` → `generate_image_concept` → `generate_draft_poster`

The LLM reasons about which tools to use and in what order — it is not a hardcoded pipeline.

---

## MCP Server

The FastMCP server (`apps/mcp/`) exposes 8 tools across three categories:

- **Events**: `search_events`, `get_event_details` — wraps Ticketmaster Discovery API
- **Strategy**: `score_event_fit`, `rank_event_candidates` — deterministic scoring engine
- **Creative**: `generate_campaign_brief`, `generate_copy_variants`, `generate_image_prompt`, `generate_draft_poster` — wraps Gemini API

Tools are registered via `server.tool()` and are callable by any MCP-compatible client.

---

## Deployment (Discussion)

For production deployment, the architecture supports:

- **Docker Compose**: Each service (API, Web, MCP) as a separate container
- **Kubernetes**: Horizontal scaling of the API service for concurrent agent workflows
- **Serverless**: API routes as AWS Lambda / Cloud Functions, with the MCP server as a long-running service
- **Environment**: All secrets via environment variables; no hardcoded keys
- **CI/CD**: GitHub Actions for lint, test, build, and deploy pipelines

---

## Development Notes

- Built with **Claude Code** (Agentic IDE)
- Mock providers available for offline development (`EVENT_PROVIDER=mock`, `CREATIVE_PROVIDER=mock`)
- File-based persistence for simplicity; swap to database by implementing the `RunRepository` protocol
- Prompt versions tracked via `PROMPT_VERSION` env var for A/B testing
