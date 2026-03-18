# Event Surge Activation Copilot

> An AI-powered, agentic marketing activation platform that discovers real upcoming events via the **Ticketmaster Discovery API**, scores them against brand/audience fit, and generates complete campaign packages — briefs, copy, and AI-generated poster creatives via **Google Gemini** — all orchestrated by a **LangChain agent** through tool calling.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [API Keys](#api-keys)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [LangChain Agent (LLM Orchestration)](#langchain-agent-llm-orchestration)
- [MCP Server](#mcp-server)
- [Domain Logic](#domain-logic)
  - [Intent Normalization](#intent-normalization)
  - [Event Scoring Engine](#event-scoring-engine)
  - [Campaign Brief & Copy Generation](#campaign-brief--copy-generation)
  - [Image Generation](#image-generation)
  - [Refinement Pipeline](#refinement-pipeline)
- [Frontend (Chat UI)](#frontend-chat-ui)
- [Data Models](#data-models)
- [Configuration Reference](#configuration-reference)
- [Deployment](#deployment)
- [Development Notes](#development-notes)

---

## Overview

A marketer types a natural-language prompt like:

> *"Find family-friendly events in Dallas this weekend for a cold beverage brand"*

The system then:

1. **Normalizes intent** — extracts city, timeframe, brand category, audience, constraints
2. **Searches Ticketmaster** — queries the Discovery API v2 for real upcoming events by date range
3. **Scores & ranks** — evaluates each event on 6 dimensions (city fit, audience fit, brand fit, category fit, timing fit, visibility fit) totaling up to 100 points
4. **Generates 2 campaign recommendations** — for the top 2 events, produces:
   - A campaign brief (angle, message direction, CTA, activation use case)
   - Copy assets (headline, social caption, CTA, promo text)
   - An AI-generated draft poster image via Gemini
5. **Supports refinement** — the user can chat to refine any output (brief, copy, or image)

All of this is orchestrated by a **LangChain agent** that uses **Gemini 2.5 Flash** as the LLM, calling tools in whatever order it decides is best.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (apps/web)                           │
│                                                                      │
│   React 18 + TypeScript + Vite + react-markdown                      │
│   Chat UI with sidebar, message bubbles, recommendation cards        │
│   Vite proxy: /api/* → http://localhost:8000                         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP (JSON)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND API (apps/api)                            │
│                                                                      │
│   FastAPI + Uvicorn                                                  │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │               LangChain Agent Orchestrator                  │     │
│   │   LLM: Gemini 2.5 Flash (langchain-google-genai)           │     │
│   │   Agentic loop: invoke LLM → execute tool calls → repeat   │     │
│   │                                                             │     │
│   │   6 Tools (mirroring MCP Server):                           │     │
│   │   ├── search_events(city, timeframe)                        │     │
│   │   ├── rank_event_candidates(intent_json)                    │     │
│   │   ├── generate_campaign_brief(event_index)                  │     │
│   │   ├── generate_copy_assets(event_index)                     │     │
│   │   ├── generate_image_concept(event_index)                   │     │
│   │   └── generate_draft_poster(event_index)                    │     │
│   └────────────────────────┬───────────────────────────────────┘     │
│                            │ calls                                    │
│   ┌────────────────────────▼───────────────────────────────────┐     │
│   │              Domain Services Layer                          │     │
│   │   intent_service.py   → NLP-lite intent extraction          │     │
│   │   scoring_service.py  → Deterministic 6-dimension scoring   │     │
│   │   brief_service.py    → Campaign brief / copy / image gen   │     │
│   │   refinement_service.py → Iterative refinement pipeline     │     │
│   └────────────────────────┬───────────────────────────────────┘     │
│                            │                                          │
│   ┌────────────────────────▼───────────────────────────────────┐     │
│   │           Infrastructure Providers (Pluggable)              │     │
│   │   TicketmasterEventProvider  ←→  Ticketmaster API v2        │     │
│   │   GeminiCreativeProvider     ←→  Gemini 2.5 Flash Image     │     │
│   │   MockEventProvider          ←→  Hardcoded test events      │     │
│   │   MockCreativeProvider       ←→  Stub metadata              │     │
│   └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │           Persistence (Pluggable)                           │     │
│   │   InMemoryRunRepository  → In-process dict                  │     │
│   │   FileRunRepository      → data/runs.json                   │     │
│   └────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                     MCP SERVER (apps/mcp)                             │
│                                                                      │
│   FastMCP server exposing 8 tools via server.tool() decorator:       │
│   ├── Events:   search_events, get_event_details                     │
│   ├── Strategy: score_event_fit, rank_event_candidates               │
│   └── Creative: generate_campaign_brief, generate_copy_variants,     │
│                  generate_image_prompt, generate_draft_poster         │
│                                                                      │
│   HTTP Clients:                                                      │
│   ├── TicketmasterClient → Ticketmaster Discovery API v2             │
│   └── GeminiImageClient  → Gemini generateContent (image mode)       │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow (Single Request)

```
User prompt
  → POST /api/v1/runs { prompt: "..." }
  → RunService.create_run()
  → AgentOrchestrator.run()
      → Gemini LLM decides: "call search_events"
      → @tool search_events("Dallas", "this weekend")
          → TicketmasterEventProvider.search()
          → HTTP GET app.ticketmaster.com/discovery/v2/events.json
          → Returns 20 normalized EventCandidate objects
      → Gemini LLM decides: "call rank_event_candidates"
      → @tool rank_event_candidates(intent_json)
          → scoring_service.rank_events()
          → Returns sorted EventEvaluation list
      → Gemini LLM decides: "call generate_campaign_brief(0)"
      → @tool → brief_service.build_campaign_brief()
      → Gemini LLM decides: "call generate_copy_assets(0)"
      → @tool → brief_service.build_copy_assets()
      → Gemini LLM decides: "call generate_image_concept(0)"
      → @tool → brief_service.build_image_concept()
      → Gemini LLM decides: "call generate_draft_poster(0)"
      → @tool → GeminiCreativeProvider.generate_asset()
          → HTTP POST generativelanguage.googleapis.com (image generation)
          → Returns base64 data URI
      → ... repeats for event index 1 ...
      → LLM returns final summary
  → WorkflowResult assembled → serialized → JSON response
  → Frontend renders recommendation cards with posters
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | Chat UI with sidebar and recommendation cards |
| **Build Tool** | Vite 5 | Dev server with HMR + API proxy to backend |
| **Markdown** | react-markdown | Renders markdown in chat message bubbles |
| **Backend** | FastAPI + Uvicorn | REST API with async support |
| **LLM Agent** | LangChain + langchain-google-genai | Agentic tool-calling orchestration |
| **LLM Model** | Google Gemini 2.5 Flash | Agent reasoning (text) + image generation |
| **MCP Server** | FastMCP | Standardized tool protocol server |
| **Event API** | Ticketmaster Discovery API v2 | Real-time event search by city and date range |
| **Image Gen** | Gemini 2.5 Flash Image | AI poster generation with base64 inline data |
| **Persistence** | File-based JSON | Run history stored in `data/runs.json` |
| **Config** | python-dotenv | Environment variable management |
| **HTTP Client** | urllib.request | Zero-dependency HTTP for API calls |

---

## Project Structure

```
interview-challenge-project/
│
├── .env                             # API keys & config (not committed)
├── .gitignore                       # Excludes .env, node_modules, __pycache__, data/
├── README.md                        # This file
│
├── apps/
│   ├── api/                         # ── FASTAPI BACKEND ──
│   │   ├── pyproject.toml           # Python deps: fastapi, uvicorn, langchain, etc.
│   │   └── app/
│   │       ├── main.py              # FastAPI app factory, route registration, CORS
│   │       ├── api/
│   │       │   └── routes/
│   │       │       ├── health.py    # GET /api/v1/health
│   │       │       └── runs.py      # POST/GET /api/v1/runs, POST /refine
│   │       ├── config/
│   │       │   └── settings.py      # AppSettings dataclass (from_env)
│   │       ├── domain/
│   │       │   └── models.py        # All domain dataclasses (15 models)
│   │       ├── application/
│   │       │   ├── serializers.py   # Domain → JSON serialization
│   │       │   ├── orchestrators/
│   │       │   │   └── activation_run.py  # EventProvider protocol
│   │       │   └── services/
│   │       │       ├── agent_service.py      # LangChain agent + 6 tools
│   │       │       ├── run_service.py        # Workflow lifecycle (agent or deterministic)
│   │       │       ├── intent_service.py     # Prompt → NormalizedIntent
│   │       │       ├── scoring_service.py    # 6-dimension event scoring
│   │       │       ├── brief_service.py      # Brief, copy, image prompt builders
│   │       │       ├── creative_service.py   # CreativeProvider protocol + MockCreativeProvider
│   │       │       └── refinement_service.py # Iterative brief/copy/image refinement
│   │       └── infra/
│   │           ├── factories.py     # Provider factory (mock vs. real via env)
│   │           ├── providers/
│   │           │   ├── ticketmaster_provider.py  # Real Ticketmaster HTTP client
│   │           │   ├── creative_provider.py      # Real Gemini image generation
│   │           │   └── mock_event_provider.py    # Hardcoded Dallas test events
│   │           └── repositories/
│   │               ├── in_memory.py              # Dict-based run storage
│   │               └── file_repository.py        # JSON file persistence
│   │
│   ├── web/                         # ── REACT FRONTEND ──
│   │   ├── package.json             # Deps: react, react-dom, react-markdown
│   │   ├── vite.config.ts           # Vite config with /api proxy to :8000
│   │   ├── tsconfig.json
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx             # React DOM mount
│   │       ├── App.tsx              # Chat app: messages, send, refine, sidebar
│   │       ├── types.ts             # All TypeScript interfaces
│   │       ├── styles.css           # Full design system (CSS custom properties)
│   │       ├── components/
│   │       │   ├── ChatMessage.tsx  # Message bubbles + RunCard + RecommendationCard
│   │       │   ├── ChatInput.tsx    # Text input with Enter-to-send
│   │       │   └── Sidebar.tsx      # Run history + "New" button
│   │       └── features/
│   │           └── copilot/
│   │               └── api.ts       # API client (fetch wrappers + fallback data)
│   │
│   └── mcp/                         # ── MCP SERVER ──
│       ├── pyproject.toml           # Deps: fastmcp, httpx
│       └── app/
│           ├── server.py            # FastMCP server, registers 8 tools
│           ├── schemas.py           # MCPToolResponse dataclass
│           ├── tools/
│           │   ├── events.py        # search_events, get_event_details
│           │   ├── strategy.py      # score_event_fit, rank_event_candidates
│           │   └── creative.py      # generate_campaign_brief, generate_copy_variants,
│           │                        # generate_image_prompt, generate_draft_poster
│           └── clients/
│               ├── ticketmaster.py  # TicketmasterClient (real HTTP)
│               └── gemini.py        # GeminiImageClient (real HTTP)
│
└── packages/
    └── shared-schemas/              # Shared JSON schemas & example payloads
```

---

## Getting Started

### Prerequisites

| Requirement | Version |
|------------|---------|
| Python | 3.11+ (3.12 recommended) |
| Node.js | 18+ |
| npm | 9+ |
| Git | 2.x |

### API Keys

This project requires two free API keys:

| Service | Get Key At | Free Tier |
|---------|-----------|-----------|
| **Ticketmaster** | [developer.ticketmaster.com](https://developer.ticketmaster.com/) | 5,000 requests/day |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 15 RPM free |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Varshithagogineni/inmarket-AI-copilot.git
cd inmarket-AI-copilot

# 2. Install Python dependencies
pip install fastapi "uvicorn[standard]" pydantic httpx python-dotenv langchain langchain-google-genai

# 3. Install MCP server dependencies
pip install fastmcp

# 4. Install frontend dependencies
cd apps/web
npm install
cd ../..
```

### Environment Configuration

Create a `.env` file in the **project root**:

```env
# ── Event Discovery ──
EVENT_PROVIDER=ticketmaster
TICKETMASTER_API_KEY=your_ticketmaster_api_key_here

# ── Creative Generation ──
CREATIVE_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# ── Persistence ──
RUN_REPOSITORY=file
RUN_STORAGE_PATH=data/runs.json

# ── Prompt Versioning ──
PROMPT_VERSION=v1
```

> **Note:** The `.env` file is listed in `.gitignore` and is never committed.

#### Environment Variable Reference

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `EVENT_PROVIDER` | `ticketmaster` \| `mock` | `mock` | Event data source |
| `TICKETMASTER_API_KEY` | API key string | `""` | Ticketmaster Discovery API key |
| `CREATIVE_PROVIDER` | `gemini` \| `mock` | `mock` | Image generation provider |
| `GEMINI_API_KEY` | API key string | `""` | Google Gemini API key (used for both agent LLM and image gen) |
| `RUN_REPOSITORY` | `file` \| `memory` | `memory` | Run persistence strategy |
| `RUN_STORAGE_PATH` | File path | `data/runs.json` | Path for file-based persistence |
| `PROMPT_VERSION` | Version string | `v1` | Tracked in generated assets for A/B testing |

### Running the Application

Open **three terminal windows**:

**Terminal 1 — Backend API:**
```bash
cd apps/api
python -m uvicorn app.main:app --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd apps/web
npm run dev
```

**Terminal 3 — MCP Server (optional):**
```bash
cd apps/mcp
python -m app.server
```

Then open **http://localhost:5173** in your browser.

> The Vite dev server on port 5173 proxies all `/api/*` requests to the FastAPI backend on port 8000.

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### `GET /health`

Health check endpoint.

**Response:**
```json
{ "status": "ok", "service": "event-surge-api" }
```

---

### `POST /runs`

Create a new campaign activation run. This triggers the full LangChain agent workflow.

**Request Body:**
```json
{
  "prompt": "Find family-friendly events in Dallas this weekend for a cold beverage brand",
  "city": "Dallas",              // optional, extracted from prompt if omitted
  "timeframe": "this weekend",   // optional
  "brand_category": "beverage",  // optional
  "audience": "family",          // optional
  "campaign_goal": "awareness",  // optional
  "requested_outputs": ["poster", "social_caption", "headline"]  // optional
}
```

Only `prompt` is required. All other fields are extracted from the prompt via NLP if not provided.

**Response (200):**
```json
{
  "run_id": "uuid",
  "status": "completed",
  "created_at": "2026-03-18T10:00:00Z",
  "updated_at": "2026-03-18T10:00:05Z",
  "request": { ... },
  "steps": [
    { "key": "intent",     "label": "Understand request", "status": "completed", "detail": "..." },
    { "key": "discovery",  "label": "Find events",        "status": "completed", "detail": "..." },
    { "key": "evaluation", "label": "Choose event",       "status": "completed", "detail": "..." },
    { "key": "brief",      "label": "Generate assets",    "status": "completed", "detail": "..." }
  ],
  "events": [
    { "timestamp": "...", "event_type": "run_created", "message": "..." },
    { "timestamp": "...", "event_type": "agent_started", "message": "LangChain agent orchestrating..." },
    { "timestamp": "...", "event_type": "events_discovered", "message": "Agent discovered 15 events..." },
    { "timestamp": "...", "event_type": "assets_generated", "message": "LangChain agent completed..." }
  ],
  "normalized_intent": {
    "city": "Dallas",
    "timeframe": "this weekend",
    "brand_category": "cold beverage",
    "audience": "family",
    "campaign_goal": "awareness",
    "requested_outputs": ["poster", "social_caption", "headline"],
    "constraints": ["family_friendly"]
  },
  "selected_event": {
    "event_id": "...",
    "name": "Dallas Family Festival",
    "city": "Dallas",
    "date_label": "2026-03-21",
    "category": "family",
    "venue_name": "Fair Park",
    "score": 93,
    "rationale": "...",
    "score_breakdown": {
      "city_fit": 25,
      "audience_fit": 18,
      "brand_fit": 20,
      "category_fit": 10,
      "timing_fit": 10,
      "visibility_fit": 10
    },
    "summary": "..."
  },
  "alternative_events": [ ... ],
  "recommendations": [
    {
      "event": { "name": "Dallas Family Festival", "score": 93, ... },
      "campaign_brief": { "event_name": "...", "campaign_angle": "...", ... },
      "copy_assets": { "headline": "...", "social_caption": "...", "cta": "...", "promo_text": "..." },
      "image_concept": { "prompt": "...", "alt_text": "...", "style_notes": [...] },
      "generated_asset": { "provider": "gemini", "status": "submitted", "asset_uri": "data:image/png;base64,..." }
    },
    {
      "event": { "name": "Second Event", "score": 85, ... },
      "campaign_brief": { ... },
      "copy_assets": { ... },
      "image_concept": { ... },
      "generated_asset": { ... }
    }
  ],
  "campaign_brief": { ... },
  "copy_assets": { ... },
  "image_concept": { ... },
  "generated_asset": { ... },
  "revision_id": 1,
  "refinement_history": [],
  "asset_versions": [{ "revision_id": 1, "provider": "gemini", "status": "submitted", ... }]
}
```

---

### `GET /runs`

List all stored runs.

**Response:**
```json
{
  "runs": [
    {
      "run_id": "uuid",
      "status": "completed",
      "created_at": "...",
      "updated_at": "...",
      "prompt": "Find events in Dallas...",
      "selected_event_name": "Dallas Family Festival",
      "event_count": 6
    }
  ]
}
```

---

### `GET /runs/{run_id}`

Get a single run's full data (same shape as the POST response).

---

### `POST /runs/{run_id}/refine`

Refine a completed run's brief, copy, or image.

**Request Body:**
```json
{
  "instruction": "Make the headline more energetic and bold",
  "target": "copy"    // "brief" | "copy" | "image"
}
```

**Behavior by target:**

| Target | What Happens |
|--------|-------------|
| `brief` | Appends instruction to campaign angle + message direction, regenerates copy and image |
| `copy` | Appends instruction notes to headline, caption, and promo text |
| `image` | Appends instruction to image prompt + style notes, regenerates poster via Gemini |

Each refinement increments `revision_id` and appends to `refinement_history` and `asset_versions`.

---

## LangChain Agent (LLM Orchestration)

**File:** `apps/api/app/application/services/agent_service.py`

The LangChain agent is the core "agentic" component. Instead of a hardcoded function pipeline, the **Gemini LLM decides** which tools to call, in what order, and with what arguments.

### How It Works

```python
# 1. LLM initialized with tools bound
self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
self.llm_with_tools = self.llm.bind_tools(AGENT_TOOLS)

# 2. Agentic loop
messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)]
for _ in range(max_iterations):
    response = self.llm_with_tools.invoke(messages)    # LLM reasons + emits tool_calls
    messages.append(response)
    if not response.tool_calls:
        break                                           # LLM is done
    for tc in response.tool_calls:
        tool_fn = _get_tool_by_name(tc["name"])
        result = tool_fn.invoke(tc["args"])             # Execute tool
        messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
```

### Agent Tools

Each tool is decorated with `@tool` from `langchain_core.tools` and mirrors an MCP server capability:

| Tool | Inputs | Calls | Returns |
|------|--------|-------|---------|
| `search_events` | `city`, `timeframe` | TicketmasterEventProvider.search() | Event list JSON |
| `rank_event_candidates` | `intent_json` | scoring_service.rank_events() | Ranked scores JSON |
| `generate_campaign_brief` | `event_index` | brief_service.build_campaign_brief() | Brief JSON |
| `generate_copy_assets` | `event_index` | brief_service.build_copy_assets() | Copy JSON |
| `generate_image_concept` | `event_index` | brief_service.build_image_concept() | Image prompt JSON |
| `generate_draft_poster` | `event_index` | GeminiCreativeProvider.generate_asset() | Asset status JSON |

### System Prompt

The agent receives a system prompt instructing it to:
1. Always search events first
2. Rank them against the campaign intent
3. Generate full creative packages for the **top 2** events
4. Follow the correct dependency chain: search → rank → brief → copy → image → poster

### Fallback

If LangChain or Gemini is unavailable, `RunService` falls back to `_run_deterministic()` — the same workflow executed procedurally without LLM reasoning.

---

## MCP Server

**File:** `apps/mcp/app/server.py`

The MCP (Model Context Protocol) server wraps all external API calls and domain logic as standardized tools using **FastMCP**.

### Tool Registration

```python
server = FastMCP("event-surge-mcp")
server.tool(search_events)              # Events
server.tool(get_event_details)          # Events
server.tool(score_event_fit)            # Strategy
server.tool(rank_event_candidates)      # Strategy
server.tool(generate_campaign_brief)    # Creative
server.tool(generate_copy_variants)     # Creative
server.tool(generate_image_prompt)      # Creative
server.tool(generate_draft_poster)      # Creative
```

### MCP Tool Details

| Category | Tool | Description |
|----------|------|-------------|
| **Events** | `search_events(city, timeframe, keyword?, classification?)` | Queries Ticketmaster Discovery API, returns normalized event list |
| **Events** | `get_event_details(event_id)` | Reserved for single-event lookup (stub) |
| **Strategy** | `score_event_fit(intent, event)` | Scores one event against intent (dict inputs) |
| **Strategy** | `rank_event_candidates(intent, events)` | Scores and sorts all events, returns ranked list |
| **Creative** | `generate_campaign_brief(selected_event, intent)` | Returns campaign angle + CTA direction |
| **Creative** | `generate_copy_variants(brief)` | Returns headline + caption + CTA |
| **Creative** | `generate_image_prompt(brief)` | Returns descriptive image generation prompt |
| **Creative** | `generate_draft_poster(prompt, style_notes?)` | Calls Gemini API, returns asset URI |

### MCP HTTP Clients

- **TicketmasterClient** (`apps/mcp/app/clients/ticketmaster.py`): Real HTTP client using `urllib.request`, computes date ranges from timeframe strings, normalizes Ticketmaster response into structured dicts
- **GeminiImageClient** (`apps/mcp/app/clients/gemini.py`): Posts to Gemini's `generateContent` endpoint with `responseModalities: ["TEXT", "IMAGE"]`, extracts base64 inline data from response

---

## Domain Logic

### Intent Normalization

**File:** `apps/api/app/application/services/intent_service.py`

Extracts structured fields from a free-form prompt:

| Field | Extraction Method | Defaults |
|-------|------------------|----------|
| `city` | Matches against known cities (Dallas, Austin, Houston, San Antonio, Fort Worth) | "Dallas" |
| `timeframe` | Detects "this weekend", "today", "this week", "next week" | "this weekend" |
| `brand_category` | Matches "beverage", "snack", "restaurant", "qsr" | "consumer brand" |
| `audience` | Matches "family", "students", "sports fans", "music fans" | "general audience" |
| `campaign_goal` | Matches "awareness", "store visits", "product launch", "localized campaign" | "awareness" |
| `constraints` | Detects "family-friendly", "music", "sports" | `[]` |
| `requested_outputs` | Detects "poster", "caption"/"social", "headline" | all three |

### Event Scoring Engine

**File:** `apps/api/app/application/services/scoring_service.py`

Each event is scored across 6 deterministic dimensions (max 100 points):

| Dimension | Max Points | Logic |
|-----------|-----------|-------|
| **City Fit** | 25 | Exact city match = 25, else 0 |
| **Audience Fit** | 20 | Tag match = 20, family+family_friendly = 18, general = 12, fallback = 6 |
| **Brand Fit** | 20 | Tag match = 20, beverage+outdoor = 16, snack+sports/music = 15, restaurant+community = 15, fallback = 8 |
| **Category Fit** | 15 | Family constraint violated = 0, music/sports constraint match = 15, no constraints = 10, partial = 12, fallback = 6 |
| **Timing Fit** | 10 | Exact timeframe/date_label match = 10, weekend partial = 10, fallback = 4 |
| **Visibility Fit** | 10 | high = 10, medium = 7, low = 4 |

**Ranking:** Sorted by `(total_score, audience_fit, brand_fit, family_friendly)` descending.

### Campaign Brief & Copy Generation

**File:** `apps/api/app/application/services/brief_service.py`

| Output | Generated Fields |
|--------|-----------------|
| **Campaign Brief** | event_name, target_audience, campaign_angle, message_direction, cta_direction, activation_use_case, reason_selected |
| **Copy Assets** | headline, social_caption, cta, promo_text |
| **Image Concept** | prompt (descriptive), alt_text, style_notes list, prompt_version |

### Image Generation

**File:** `apps/api/app/infra/providers/creative_provider.py`

- **Model:** `gemini-2.5-flash-image`
- **Endpoint:** `generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`
- **Config:** `responseModalities: ["TEXT", "IMAGE"]` to get inline base64 image data
- **Output:** Returns `data:image/png;base64,...` data URI rendered directly in the frontend

### Refinement Pipeline

**File:** `apps/api/app/application/services/refinement_service.py`

Users can iteratively refine any output:

| Target | Refinement Behavior |
|--------|-------------------|
| `brief` | Appends instruction to `campaign_angle` and `message_direction`, then cascades: regenerates copy, image concept, and poster |
| `copy` | Appends instruction to `headline`, `social_caption`, and `promo_text` |
| `image` | Appends instruction to `prompt` and `style_notes`, regenerates poster via Gemini |

Each refinement increments `revision_id`, appends a `RefinementRecord`, and saves a new `AssetVersion`.

---

## Frontend (Chat UI)

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **App** | `App.tsx` | Root chat layout, message state, send/refine logic, sidebar toggle |
| **ChatMessage** | `ChatMessage.tsx` | User/assistant bubbles, RunCard with workflow steps, RecommendationCard per event |
| **ChatInput** | `ChatInput.tsx` | Textarea with Enter-to-send (Shift+Enter for newline), send button |
| **Sidebar** | `Sidebar.tsx` | Campaign run history, active state highlight, "+ New" button |

### Chat Intelligence

The frontend detects refinement requests from natural language:

```typescript
// Triggers refinement instead of new run
"refine", "change the", "make it", "update the", "more ", "less ", "try a different", "regenerate"

// Auto-detects target
"image"/"poster"/"visual" → target: "image"
"brief"/"strategy"/"angle" → target: "brief"
default → target: "copy"
```

### Design System

CSS custom properties define the visual language:

- **Chat layout:** sidebar (280px) + main area with header/messages/input
- **User messages:** gradient orange bubbles (right-aligned)
- **Assistant messages:** white bubbles (left-aligned) with markdown rendering
- **Recommendation cards:** numbered headers, score breakdown bars with gradient fills
- **Animations:** fadeSlideIn for messages, thinking dots for loading
- **Responsive:** breakpoints at 768px and 480px

### API Client

**File:** `apps/web/src/features/copilot/api.ts`

All API calls include fallback responses so the frontend works even when the backend is offline — useful for UI development.

| Function | Endpoint | Fallback |
|----------|---------|----------|
| `createCampaignRun(payload)` | `POST /api/v1/runs` | Returns hardcoded demo run |
| `refineCampaignRun(runId, payload)` | `POST /api/v1/runs/{id}/refine` | Client-side mock refinement |
| `listCampaignRuns()` | `GET /api/v1/runs` | Returns demo run summary |
| `getCampaignRun(runId)` | `GET /api/v1/runs/{id}` | Returns demo run |

---

## Data Models

**File:** `apps/api/app/domain/models.py`

All models are pure Python `@dataclass` classes with zero framework dependencies:

| Model | Fields | Purpose |
|-------|--------|---------|
| `CampaignRequest` | prompt, city?, timeframe?, brand_category?, audience?, campaign_goal?, requested_outputs | User input |
| `NormalizedIntent` | city, timeframe, brand_category, audience, campaign_goal, requested_outputs, constraints | Structured intent |
| `EventCandidate` | event_id, name, city, date_label, category, venue_name, family_friendly, visibility_hint, audience_tags, brand_tags, summary | Normalized event from Ticketmaster |
| `EventEvaluation` | event, total_score, score_breakdown, rationale | Scored event |
| `CampaignBrief` | event_name, target_audience, campaign_angle, message_direction, cta_direction, activation_use_case, reason_selected | Strategy output |
| `CopyAssetSet` | headline, social_caption, cta, promo_text | Marketing copy |
| `ImageConcept` | prompt, alt_text, style_notes, prompt_version | Image generation input |
| `GeneratedAsset` | provider, status, prompt_version, asset_uri?, error? | Image generation output |
| `EventRecommendation` | evaluation, campaign_brief, copy_assets, image_concept, generated_asset | Full package for one event |
| `WorkflowResult` | normalized_intent, candidate_evaluations, selected_event, campaign_brief, copy_assets, image_concept, generated_asset, recommendations, revision_id, refinement_history, asset_versions | Complete run output |
| `WorkflowRunRecord` | run_id, status, request, created_at, updated_at, steps, events, result?, error? | Persistent run record |
| `WorkflowStep` | key, label, status, detail | Pipeline step tracking |
| `WorkflowEvent` | timestamp, event_type, message | Audit log entry |
| `RefinementRecord` | revision_id, target, instruction, applied_at | Refinement history |
| `AssetVersion` | revision_id, prompt_version, provider, status, asset_uri? | Asset version tracking |

---

## Configuration Reference

### Provider Factory Pattern

**File:** `apps/api/app/infra/factories.py`

Providers are selected at startup via environment variables:

```python
def build_event_provider(settings):
    if settings.event_provider == "ticketmaster":
        return TicketmasterEventProvider(api_key=settings.ticketmaster_api_key)
    return MockEventProvider()        # Default for offline dev

def build_creative_provider(settings):
    if settings.creative_provider == "gemini":
        return GeminiCreativeProvider(api_key=settings.gemini_api_key)
    return MockCreativeProvider()     # Default for offline dev
```

This means you can develop the full UI and scoring logic offline with `EVENT_PROVIDER=mock` and `CREATIVE_PROVIDER=mock`.

---

## Deployment

### Docker Compose (Recommended)

```yaml
services:
  api:
    build: ./apps/api
    ports: ["8000:8000"]
    env_file: .env
  web:
    build: ./apps/web
    ports: ["5173:5173"]
    depends_on: [api]
  mcp:
    build: ./apps/mcp
    env_file: .env
```

### Production Considerations

| Concern | Approach |
|---------|---------|
| **Secrets** | All API keys via environment variables; `.env` never committed |
| **Scaling** | API is stateless; scale horizontally behind a load balancer |
| **Persistence** | Swap `FileRunRepository` for PostgreSQL/Redis by implementing `RunRepository` protocol |
| **Rate Limits** | Ticketmaster: 5,000/day; Gemini: 15 RPM free tier — add caching/queuing for production |
| **CORS** | Currently allows `localhost:5173`; update `allow_origins` for production domain |
| **Monitoring** | `WorkflowEvent` audit logs provide full observability per run |

---

## Development Notes

- Built entirely with **Claude Code** (Agentic IDE) as required by the project specification
- **Mock providers** enable full offline development — no API keys needed for UI work
- **Prompt versioning** via `PROMPT_VERSION` env var — tracked in every generated asset for A/B testing
- **File-based persistence** chosen for simplicity; the `RunRepository` protocol makes database migration trivial
- **Zero-dependency HTTP** — both API and MCP clients use Python's built-in `urllib.request` instead of third-party HTTP libraries for external API calls
- **Deterministic scoring** ensures reproducible event rankings regardless of LLM variability
- **Graceful degradation** — LangChain agent falls back to deterministic orchestration if unavailable; frontend falls back to mock data if backend is offline
