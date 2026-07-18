# Pluribus fixed demo

This directory owns the disposable hackathon mission used by Mission Control.

## Replay (recommended presentation fallback)

```bash
node demo/start-demo.mjs --mode replay
```

The launcher creates a fresh Git repository at the OS temporary directory, commits the health API baseline, and starts the frontend. Replay is permanently labeled `REPLAY — RECORDED EVIDENCE` and is never presented as live execution.

## Live backend

```bash
set VITE_API_BASE_URL=http://127.0.0.1:8000
node demo/start-demo.mjs --mode live
```

The seed intentionally contains an existing `HealthService`, version utility, authentication middleware, and a basic health test, but no `/health/details` route. It contains no credentials and has zero runtime dependencies.
