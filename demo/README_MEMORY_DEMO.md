# Pluribus Memory Registry demo

This launcher presents Pluribus as a registry for reusable, verified Codex memories. It serves the Person 4 frontend on `127.0.0.1` and requires the presenter to choose **Replay** or **Live** explicitly.

## Prerequisites

- Node.js 20+ with npm
- Frontend dependencies installed once:

  ```bash
  npm --prefix frontend ci
  ```

The launcher does not install packages, start the registry API, run Codex, or modify the old seed mission fixture.

## Replay: deterministic presentation path

```bash
node demo/start-memory-demo.mjs --mode replay
```

Optional frontend port:

```bash
node demo/start-memory-demo.mjs --mode replay --port 4173
```

Open the printed URL (normally <http://127.0.0.1:5173>). Replay requires no backend and must display the exact persistent label:

```text
REPLAY — RECORDED EVIDENCE
```

Replay uses the deterministic, sanitized Memory Registry data compiled into the frontend. It demonstrates the product flow; it does **not** claim that a live API, filesystem installation, Codex run, or verification command happened during this launch.

## Live: integrated system only

Start the integrated backend separately, then launch the frontend with its API base:

```bash
# Terminal 1
cd backend
uv sync --dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2, from the repository root
node demo/start-memory-demo.mjs --mode live --api-base http://127.0.0.1:8000
```

`VITE_API_BASE_URL` is also accepted when `--api-base` is omitted:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 node demo/start-memory-demo.mjs --mode live
```

On Windows `cmd.exe`:

```bat
set VITE_API_BASE_URL=http://127.0.0.1:8000
node demo\start-memory-demo.mjs --mode live
```

The default Live API base is `http://127.0.0.1:8000`. The launcher prints the chosen base. Live never silently falls back to Replay: missing endpoints, backend downtime, CORS failures, and integration errors remain visible as Live errors.

### Live dependencies owned by Persons 1–3

A complete Live golden path requires their integrated work:

1. **Person 1 — Registry API and persistence:** frozen memory list/detail/publish/star/install/installed/snapshot endpoints and seeded `mem_pytest_importlib_v1`.
2. **Person 2 — Local Memory Runtime:** deterministic `.pluribus/installed/<slug>/MEMORY.md`, manifest integrity, trigger matching, and bounded Codex context injection.
3. **Person 3 — Usage and verification:** duplicate-module fixture, coordinator-run `pytest -q`, sanitized evidence, and a valid Usage Receipt.

The frontend launcher cannot substitute for any of these dependencies and does not fabricate their Live output.

## Presenter golden path

1. **Explore** — search for `pytest` and point out the verified badge, Alice Chen, tags, stars, installs, and version.
2. **Memory Detail** — open **Fix duplicate pytest module collisions** and show its problem, triggers, steps, compatibility, and verification evidence.
3. **Install to Codex** — install and show the successful installed state.
4. **My Codex** — show version `1.0.0` and the explicit local Pluribus package path.
5. **Codex Uses** — run the integrated use in Live, or replay the recorded use in Replay.
6. **Usage Receipt** — show publisher → memory → consumer → `pyproject.toml` → `pytest -q` exit code `0` / `4 passed`.
7. **Publish** — show the validated Memory Capsule form and emphasize that raw transcript upload is not supported.

## Expected screens

- **Explore:** searchable marketplace cards and tags
- **Memory Detail:** reusable method and verification evidence
- **Publish:** sanitized, validated Memory Capsule fields only
- **My Codex:** Pluribus-managed local installation state
- **Usage Receipt:** projector-readable proof chain and verification result

In Replay, every screen must retain `REPLAY — RECORDED EVIDENCE`. In Live, the mode must remain `LIVE`, including when an API operation fails.

## Honest memory boundary

Pluribus does **not** mutate hidden Codex model state. An installation is an explicit package under a caller-supplied project root, and matching memory content is injected into a bounded Codex task context by the runtime adapter. A Usage Receipt records the observable chain and coordinator verification; it is not proof of hidden-model-state modification.

## Troubleshooting

### `--mode is required`

Choose intentionally:

```bash
node demo/start-memory-demo.mjs --mode replay
# or
node demo/start-memory-demo.mjs --mode live --api-base http://127.0.0.1:8000
```

### Frontend dependencies or Vite are missing

```bash
npm --prefix frontend ci
```

Then rerun the launcher. It deliberately does not mutate dependencies for you.

### Port already in use

The launcher uses Vite's strict-port behavior so it cannot quietly move the presentation URL. Select another port:

```bash
node demo/start-memory-demo.mjs --mode replay --port 4173
```

### Live shows API/network errors

This is not a Replay trigger. Confirm the backend is running, the printed API base is correct, `/health` responds, the Person 1 routes are integrated, and localhost CORS permits the selected frontend origin. Restart with the correct `--api-base`; do not relabel failed Live output as successful Replay evidence.

### Replay makes network requests

Stop the demo and treat this as a bug. Replay is required to use only deterministic frontend data and to need no backend.

## Verification before handoff

Launcher-only checks (they do not leave a server running):

```bash
node --check demo/start-memory-demo.mjs
node demo/start-memory-demo.mjs --help
node demo/start-memory-demo.mjs --mode replay --port 0   # expected validation failure
node demo/start-memory-demo.mjs                          # expected explicit-mode failure
```

Full Person 4 gates:

```bash
cd frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
npm audit
```

Before presenting, exercise all five screens in a real browser at `1440x900` or `1920x1080`, repeat at `390px` width, and confirm:

- the golden path works;
- Replay has zero failed network requests;
- the browser console has zero JavaScript errors;
- the selected mode label is persistent and honest;
- no token, raw transcript, personal home path, or OAuth material appears.

Stop the launcher with `Ctrl+C`; shutdown signals are forwarded to Vite.
