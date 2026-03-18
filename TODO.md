# TODO

## Completed

- [x] Scaffold monorepo structure for web, api, mcp, and shared schemas
- [x] Implement core orchestration and deterministic recommendation logic
- [x] Add MCP tool interfaces for events and creative generation contracts
- [x] Build the first-pass React workflow UI
- [x] Add and run core tests that are feasible in the current environment
- [x] Add workflow run tracking, serialized API responses, and alternative event summaries
- [x] Add a Ticketmaster normalization/provider scaffold for future live integration
- [x] Add config-driven provider selection and prompt version metadata
- [x] Add creative asset provider abstraction for mock and Gemini modes
- [x] Add run listing and refinement support for brief, copy, and image outputs
- [x] Add a simple UI refinement flow without rerunning event selection
- [x] Add file-backed run persistence, revision history, and asset lineage
- [x] Add run history browsing and workflow event logs
- [x] Add MCP-native scoring and ranking tools

## Next

- [ ] Install Python and Node dependencies in a fully provisioned environment
- [ ] Verify the live Ticketmaster request and normalization path with a real API key
- [ ] Verify the live Gemini image generation request path with a real API key
- [ ] Replace the mock provider with real Ticketmaster or MCP-backed event discovery in FastAPI orchestration
- [ ] Add production persistence with PostgreSQL and caching with Redis
- [ ] Add SSE or WebSocket streaming from workflow runs
- [ ] Add Playwright end-to-end coverage
