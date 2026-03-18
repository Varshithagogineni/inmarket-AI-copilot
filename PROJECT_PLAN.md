# Event Surge Activation Copilot

## 1. Recommended Architecture

Use a three-tier application with a dedicated agent tooling layer:

- `React` for the marketer-facing UI
- `FastAPI` for the product API, orchestration entrypoints, persistence, and streaming updates
- `FastMCP` for model-callable tools that expose Ticketmaster, scoring utilities, and creative generation helpers

This keeps the user experience clean, the orchestration layer testable, and external integrations isolated behind reusable tools.

## 2. High-Level System Design

### Frontend: React

Responsibilities:

- Collect the marketer request in plain language and optional structured filters
- Show progress through the agent workflow
- Present shortlisted events, the chosen event, rationale, campaign brief, and generated assets
- Support refine-and-regenerate loops for copy and image outputs

Suggested pages/components:

- `CampaignIntakePage`
- `RunProgressPanel`
- `EventComparisonCard`
- `RecommendationSummary`
- `CampaignBriefPanel`
- `CreativeAssetsGallery`
- `RefinementDrawer`

Recommended stack:

- React + TypeScript
- Vite
- TanStack Query for API state
- React Router
- Zod-backed form validation
- Playwright for end-to-end tests

### Backend API: FastAPI

Responsibilities:

- Accept campaign requests from the UI
- Validate and normalize user intent
- Create and track workflow runs
- Invoke the reasoning/orchestration layer
- Stream intermediate state back to the UI
- Persist run metadata, event candidates, briefs, and asset references

Key modules:

- `api/routes/copilot.py`
- `api/routes/assets.py`
- `api/routes/health.py`
- `application/orchestrators/activation_run.py`
- `application/services/run_service.py`
- `application/services/brief_service.py`
- `application/services/creative_service.py`
- `domain/models/*.py`
- `infra/db/*.py`
- `infra/queue/*.py`

Recommended infrastructure:

- PostgreSQL for runs, requests, event evaluations, and asset metadata
- Redis for caching and background job coordination
- Object storage for generated images
- Server-Sent Events or WebSockets for live progress updates

### Tooling Layer: FastMCP

Use `FastMCP` as the tool server that the orchestrator can call through the LLM runtime. This is where external capabilities and reusable decision tools live.

Suggested MCP tools:

- `search_events`
  - Queries Ticketmaster Discovery API by city, date window, keyword, and classification
- `get_event_details`
  - Fetches richer metadata for a selected candidate
- `score_event_fit`
  - Applies deterministic scoring inputs like family-friendliness, category fit, timing fit, venue relevance, and local activation potential
- `rank_event_candidates`
  - Produces a scored shortlist from candidate events
- `generate_campaign_brief`
  - Converts the selected event and user goal into a structured campaign brief
- `generate_copy_variants`
  - Produces headline, caption, CTA, and promo text options
- `generate_image_prompt`
  - Converts the campaign brief into an image-safe, brand-aware visual prompt
- `generate_draft_poster`
  - Calls Gemini native image generation for the draft visual

FastMCP should remain integration-focused and stateless where possible. Put persistence and session ownership in FastAPI, not in the MCP server.

## 3. End-to-End Workflow

1. User enters a request such as: "Find the best family-friendly event in Dallas this weekend for promoting a cold beverage brand."
2. React sends the request to FastAPI.
3. FastAPI normalizes the request into structured intent:
   - city
   - timeframe
   - brand category
   - audience
   - campaign goal
   - requested outputs
4. FastAPI creates a workflow run and starts orchestration.
5. The orchestrator calls FastMCP tools to search and shortlist Ticketmaster events.
6. Candidate events are scored and ranked using deterministic scoring plus LLM reasoning.
7. The best-fit event is selected with an explainable rationale.
8. A structured campaign brief is generated.
9. Copy outputs are generated from the brief.
10. An image prompt is generated and sent to Gemini image generation.
11. FastAPI stores result metadata and streams updates to the UI.
12. React presents the recommendation, rationale, brief, and creative assets.

## 4. Decisioning Model

Use a hybrid scoring system so the recommendation feels opinionated but remains explainable.

Suggested score dimensions:

- audience fit
- brand-category fit
- event-category fit
- timing fit
- foot-traffic potential
- family-friendliness or demographic fit
- creative potential
- location relevance

Recommended pattern:

- Deterministic scoring for observable facts
- LLM reasoning for narrative judgment and tie-breaking
- Final explanation composed from both score data and qualitative reasoning

This is safer and easier to debug than relying on pure free-form reasoning.

## 5. Suggested Repository Structure

```text
event-surge-activation-copilot/
  apps/
    api/
      app/
        api/
        application/
        domain/
        infra/
        tests/
      pyproject.toml
    mcp/
      app/
        server.py
        tools/
        clients/
        schemas/
        tests/
      pyproject.toml
    web/
      src/
        app/
        components/
        features/
        hooks/
        lib/
        tests/
      package.json
  packages/
    shared-schemas/
      openapi/
      jsonschema/
  docs/
    architecture/
    api-contracts/
  .env.example
  AGENTS.md
  PROJECT_PLAN.md
```

## 6. Core API Contracts

Suggested FastAPI endpoints:

- `POST /api/v1/runs`
  - Create a new activation workflow run
- `GET /api/v1/runs/{run_id}`
  - Retrieve run status and outputs
- `GET /api/v1/runs/{run_id}/stream`
  - Stream progress updates
- `POST /api/v1/runs/{run_id}/refine`
  - Refine brief, copy, or poster prompt
- `GET /api/v1/assets/{asset_id}`
  - Fetch asset metadata

Suggested run output shape:

- `request`
- `normalized_intent`
- `candidate_events`
- `selected_event`
- `selection_rationale`
- `campaign_brief`
- `copy_assets`
- `image_prompt`
- `image_asset`
- `status`
- `errors`

## 7. Prompt and Agent Design

Use one orchestrator agent with clear tool access instead of many loosely scoped agents.

Suggested internal stages:

- `intent_extraction`
- `event_discovery`
- `candidate_evaluation`
- `recommendation`
- `brief_generation`
- `copy_generation`
- `image_prompt_generation`
- `draft_asset_generation`

Guardrails:

- Require structured outputs between stages
- Keep prompts versioned
- Log tool calls and model decisions per run
- Add fallbacks if no suitable event is found
- Block unsupported or unsafe visual requests before image generation

## 8. External Integrations

### Ticketmaster Discovery API

Use it as the source of truth for real-world event opportunities.

Integration notes:

- Wrap the API in a dedicated client
- Add retry, timeout, and rate-limit handling
- Normalize raw event payloads into internal schemas
- Cache common searches for short periods

### Gemini Native Image Generation

Use it only after the recommendation and brief are approved or generated.

Integration notes:

- Separate image prompt construction from image generation
- Store prompt versions with each asset
- Support regeneration without rerunning event selection
- Add response validation and artifact persistence

## 9. Data Model

Core entities:

- `CampaignRequest`
- `NormalizedIntent`
- `EventCandidate`
- `EventEvaluation`
- `Recommendation`
- `CampaignBrief`
- `CopyAssetSet`
- `ImageAsset`
- `WorkflowRun`

Important fields:

- source API ids
- city and timeframe
- scoring breakdown
- rationale text
- prompt versions
- model/provider metadata
- generation timestamps

## 10. Testing Strategy

Because this product is agentic and integration-heavy, testing should be layered.

### Backend and MCP tests

- Unit tests for intent parsing, scoring, ranking, and prompt builders
- Contract tests for Ticketmaster and Gemini client wrappers
- Integration tests for the full workflow using mocked external APIs
- Failure-path tests for empty results, malformed payloads, timeouts, and provider errors

### Frontend tests

- Component tests for result states, loading states, and error states
- End-to-end tests for create-run, stream-progress, result rendering, and refine flows

### Edge cases to cover

- no events returned for location or timeframe
- multiple equally good events
- vague user request with missing city or timeframe
- family-friendly request returning adult-oriented events
- API timeout or rate limiting
- image generation failure after successful event selection
- regenerate copy without regenerating image
- refine selected event without losing prior artifacts

## 11. Production Readiness Checklist

- Strong schema validation at every boundary
- Centralized error handling and typed exceptions
- Config-driven provider selection
- Structured logs and trace ids per run
- Rate limiting and retries for third-party APIs
- Feature flags for experimental scoring or prompt versions
- Observability dashboards for workflow success, latency, and failure reasons

## 12. Implementation Plan

### Phase 1: Foundation

- Create monorepo structure
- Set up React, FastAPI, and FastMCP apps
- Define shared schemas for requests and results
- Add environment/config management
- Add baseline CI for lint, typecheck, and tests

### Phase 2: Event Discovery

- Implement Ticketmaster client
- Add search and detail MCP tools
- Build event normalization and scoring
- Expose FastAPI run creation and status endpoints

### Phase 3: Recommendation Engine

- Add orchestrator workflow
- Implement candidate ranking and rationale generation
- Build recommendation UI and progress streaming

### Phase 4: Creative Generation

- Add brief and copy generation
- Add Gemini image prompt generation and draft poster creation
- Render creative outputs in the UI

### Phase 5: Refinement and Hardening

- Add refine/regenerate endpoints
- Improve fallback behavior and observability
- Expand automated tests for edge cases
- Load test critical workflow paths

## 13. Suggested First Build Sprint

If you want a strong interview-ready demo quickly, build this slice first:

- plain-language intake form
- Ticketmaster-backed event shortlist
- transparent scoring and final recommendation
- campaign brief output
- headline, caption, and CTA generation
- one draft poster generation flow

That is the smallest slice that still tells the full value story: signal to decision to action.
