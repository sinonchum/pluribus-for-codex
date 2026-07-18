# Person 4 Implementation Plan — Memory Marketplace UI

## 0. Identity and fixed baseline

- Role: Person 4 — Memory Marketplace UI and presentation-ready demo story owner.
- Delivery branch: `feat/memory-marketplace-ui`.
- Required base commit: `1b5e078d70b807ad92453737882f797eae6cc423`.
- PR target: `pivot/memory-registry-v1`.
- Product: **GitHub for useful Codex memories**.
- Golden path: **Publish → Discover → Install → Codex Uses → Verify**.

This plan supersedes the historical Mission Control UI. Scout, Builder, Tester, Reviewer, Agent Roster, Hive Memory, and the old mission dashboard are prohibited as primary product concepts.

## 1. Scope and ownership

Person 4 may modify only:

```text
frontend/**
demo/start-memory-demo.mjs
demo/README_MEMORY_DEMO.md
```

Person 4 must not modify backend code, registry tables, API router registration, Person 3's fixture/evidence directories, or frozen response shapes.

## 2. Required user journey

```text
Explore
→ search for pytest
→ open Fix duplicate pytest module collisions
→ inspect problem, triggers, steps, compatibility, and verification
→ click Install to Codex
→ confirm installed state in My Codex
→ run or replay the use
→ inspect the verified Usage Receipt
```

The interface must be understandable within five seconds as a registry/marketplace for reusable Codex debugging memories.

## 3. Technical architecture

### 3.1 Application model

Use a small React state machine instead of server-dependent routing for the demo-critical path. The active screen is one of:

```text
explore | detail | publish | installed | receipt
```

Why:

- deterministic in Replay mode;
- easy to test with React Testing Library;
- no URL/server fallback dependency during the hackathon demo;
- no new package dependency;
- screen transitions remain immediate.

The app state owns:

- execution mode (`live` or `replay`);
- current screen;
- query and selected tag;
- selected memory slug;
- installed memory IDs;
- latest Usage Receipt;
- loading and API error state.

### 3.2 Frozen TypeScript contract

Replace obsolete mission types with exact interfaces from `MEMORY_REGISTRY_SCOPE.md`:

- `Author`
- `MemoryVerification`
- `MemoryCapsule`
- `InstallManifest`
- `UsageReceiptVerification`
- `UsageReceipt`
- `DemoStats`
- `DemoSnapshot`
- `ExecutionMode`

No frontend-only fields may be added to API objects. UI-only state stays in component/local state.

### 3.3 API adapter

Create `memoryApi` with the frozen routes:

```text
GET    /api/memories?query=&tag=&sort=
POST   /api/memories
GET    /api/memories/{slug}
POST   /api/memories/{slug}/star
POST   /api/memories/{slug}/install
GET    /api/installed
POST   /api/usage-receipts
GET    /api/usage-receipts/{id}
GET    /api/demo/snapshot
```

Technical rules:

- Base URL from `VITE_API_BASE_URL`, default `http://127.0.0.1:8000`.
- Encode slugs and query parameters.
- Use JSON content type for writes.
- Surface non-2xx responses with status-aware errors.
- Replay mode must not call live endpoints.
- Live mode must never silently fall back to Replay while labeling itself Live.

### 3.4 Deterministic Replay

Replace old mission replay data with only frozen Memory Registry fields:

- exact featured `mem_pytest_importlib_v1` capsule;
- deterministic installed manifest;
- deterministic `use_demo_001` Usage Receipt;
- aggregate Demo Snapshot;
- replay metadata that explicitly says `REPLAY — RECORDED EVIDENCE`.

Replay data may not contain Scout/Builder/Tester/Reviewer or invented receipt fields.

### 3.5 Visual system

Use the reusable Pluribus foundation selectively, but rebuild the information architecture for a marketplace/package registry.

Visual principles:

- immediate search and featured memory cards;
- large marketplace title and readable body text;
- one signal green for verified/install state;
- warm paper/white reading surfaces and restrained dark navigation;
- square, repository-like geometry;
- monospace for IDs, versions, commands, paths, and receipts;
- no gradients, glassmorphism, neon, or decorative dashboard metrics;
- no dense three-column mission-control wall;
- projector-readable Usage Receipt;
- minimum primary control height of 44–46px;
- desktop and 390px mobile support.

## 4. Screen-by-screen implementation

### 4.1 Explore Memories

Functions:

- registry header and five-second product explanation;
- search input with `pytest` behavior;
- tag filters for python, pytest, debugging, codex;
- featured memory cards;
- verified badge;
- author, version, stars, installs;
- clear action to open detail;
- direct navigation to Publish and My Codex.

Implementation:

- controlled query and selected-tag state;
- client filtering in Replay;
- `memoryApi.list` in Live;
- semantic card articles and accessible buttons.

Dependencies:

- frozen Memory Capsule;
- Person 1 list/search endpoint for final Live integration.

### 4.2 Memory Detail

Functions:

- title, author, version, ID;
- problem and trigger phrases;
- ordered reusable steps;
- compatibility;
- verification command, pass count, evidence excerpt;
- fork lineage;
- obvious Install to Codex button;
- installed-state confirmation.

Implementation:

- selected Memory Capsule from replay snapshot or detail API;
- install transition updates local state only after replay action or successful Live response;
- no claim of hidden Codex memory mutation.

Dependencies:

- Person 1 detail and install-record endpoints;
- Person 2 local package behavior for end-to-end integration.

### 4.3 Publish Memory

Functions:

- fixed validated Memory Capsule form;
- title, summary, problem, triggers, steps, tags, compatibility, version;
- author and verification fields represented by fixed safe demo values where appropriate;
- clear validation messages;
- no transcript upload.

Implementation:

- controlled form state;
- deterministic client validation;
- Live submission through `memoryApi.create`;
- Replay submission demonstrates validated shape without pretending to publish live.

Dependencies:

- Person 1 create endpoint for Live.

### 4.4 My Codex

Functions:

- installed memory list;
- version;
- deterministic install path from manifest;
- installed status;
- last-used/receipt relationship when available;
- action to run or replay use.

Implementation:

- Replay manifest from frozen data;
- Live list from `GET /api/installed`;
- honest label: Pluribus-managed local memory package used by Codex.

Dependencies:

- Person 1 installed list;
- Person 2 real local package integration.

### 4.5 Usage Receipt

Functions:

- large proof chain: publisher → memory → consumer → Codex use → changed file → verification;
- matched trigger;
- injected and Codex-reported-use booleans;
- effect;
- changed `pyproject.toml`;
- `pytest -q`, exit code `0`, and `4 passed`;
- explicit Live or `REPLAY — RECORDED EVIDENCE` state.

Implementation:

- semantic ordered proof chain;
- receipt fields only from frozen contract;
- projector-first typography;
- no mission-agent narrative.

Dependencies:

- Person 3 sanitized replay receipt and final evidence;
- Usage Receipt API after integration.

## 5. Test plan — RED → GREEN → REFACTOR

Write and observe failures before UI implementation for:

1. Explore search for `pytest` finds the fixed memory.
2. Opening detail shows problem, reusable steps, and verification.
3. Install changes the action to installed state.
4. My Codex lists the installed memory and version.
5. Usage Receipt shows publisher-to-verification chain and `pyproject.toml`.
6. Replay always shows the exact label `REPLAY — RECORDED EVIDENCE`.
7. Publish rejects an incomplete Memory Capsule and exposes no transcript upload.
8. Navigation keeps all demo-critical actions directly available.

Tests use React Testing Library and user-event. They must assert user-observable behavior, not implementation details.

## 6. Parallel execution plan

### Shared scaffold — serial prerequisite

Owner: integration branch.

Files:

```text
frontend/IMPLEMENTATION_PLAN_PERSON4.md
frontend/src/contracts.ts
frontend/src/api.ts
frontend/src/replay.ts
```

Purpose:

- freeze the shared TypeScript/API/replay contract before parallel work;
- eliminate contract drift between tests and UI.

### Lane A — behavior tests

Branch: `lane/person4-marketplace-tests`

Owns:

```text
frontend/src/App.test.tsx
frontend/src/test/** (only if needed)
```

Can run in parallel after scaffold. It intentionally begins RED because the old App does not expose the new marketplace behavior.

### Lane B — marketplace UI

Branch: `lane/person4-marketplace-ui`

Owns:

```text
frontend/src/App.tsx
frontend/src/styles.css
frontend/src/main.tsx (only if required)
frontend/index.html
frontend/src/design-system/** (if introduced)
```

Can run in parallel with Lane A against the frozen contract. It must not weaken tests after integration.

### Lane C — demo launcher and handoff

Branch: `lane/person4-marketplace-demo`

Owns:

```text
demo/start-memory-demo.mjs
demo/README_MEMORY_DEMO.md
```

Fully independent of Lane A/B. It supports explicit `--mode live|replay`, starts the frontend, passes mode/API environment, and documents honest boundaries.

### Integration sequence

```text
shared scaffold
→ Lane A tests
→ Lane B UI
→ Lane C launcher/docs
→ resolve only contract/interface mismatches
→ full frontend gates
→ real browser five-screen QA
```

Lane A and Lane B may be integrated in either order, but the final state must pass Lane A without deleting or weakening assertions.

## 7. Risk and dependency register

| Risk/dependency | Owner | Parallel strategy | Mitigation |
|---|---|---|---|
| Registry API not merged yet | Person 1 | Build against frozen contract | Replay is deterministic; Live remains explicit and error-visible |
| Local install package not merged yet | Person 2 | UI install state can be developed against manifest contract | Do not claim filesystem write in Replay; verify real install at integration |
| Receipt/evidence not merged yet | Person 3 | Use exact frozen receipt fixture | Replace with sanitized Person 3 evidence without changing UI shape |
| Existing frontend is obsolete | Person 4 | Full replacement in owned files | Preserve only reusable technical setup and dependencies |
| Old narrative leaks into UI | Person 4 | Contract tests and text search | Reject Scout/Builder/Tester/Reviewer/Mission Control primary concepts |
| Live mislabeled as Replay or vice versa | Person 4 | Mode is explicit and immutable per launch | Persistent exact replay banner; no silent fallback |
| Projector readability | Person 4 | Browser QA after functional integration | Test 1440×900 and 1920×1080 plus 390px mobile |
| Parallel merge conflicts | Person 4 | File ownership per lane | Scaffold first; no overlapping files across lanes |

## 8. Verification gates

Automated:

```bash
cd frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
npm audit
```

Browser:

- Explore, Detail, Publish, My Codex, Usage Receipt all render.
- Search/install/navigation path works.
- Replay label is exact and persistent.
- No white screen, clipping, overlap, page-level overflow, or tiny critical text.
- Desktop projector viewport and 390px mobile viewport pass.
- Browser console errors: zero.
- Runtime exceptions: zero.
- Failed network requests in Replay: zero.

Repository:

- `git diff --check` passes.
- No backend files changed.
- No secrets, absolute personal paths, raw transcript, or OAuth data.
- Branch contains only Person 4-owned paths.

## 9. Delivery

- Push only `feat/memory-marketplace-ui`.
- Open Draft PR to `pivot/memory-registry-v1`.
- Include required screen screenshots, actual automated output, browser-console result, Live/Replay status, dependencies, and blockers.
- Person 4 merges after Persons 1–3 according to the team integration order.
