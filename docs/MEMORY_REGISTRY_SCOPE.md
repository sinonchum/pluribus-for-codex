# Pluribus Memory Registry — Pivot Scope v1

## Product definition

**Pluribus for Codex is the open registry for reusable, verified Codex memories.**

It lets developers publish debugging methods and coding best practices learned with Codex, discover memories created by others, install them into a local Pluribus-managed Codex memory pack, and prove that an installed memory was actually used and helped verification pass.

> GitHub for useful Codex memories.

## The one demo claim

A debugging method learned by Developer A can be published, installed by Developer B, consumed by B's Codex session, and tied to a successful verification receipt.

## Golden path

```text
Developer A publishes a verified debugging memory
                        ↓
Developer B searches the public registry
                        ↓
Developer B installs the memory locally
                        ↓
Pluribus injects the matching memory into a Codex task
                        ↓
Codex applies the method to a failing fixture repository
                        ↓
Verification passes and a usage receipt is recorded
```

## Fixed demo memory

**Title:** Fix duplicate pytest module collisions

**Problem:** Two test directories contain files with the same module name, causing pytest import-file-mismatch collection failures.

**Trigger phrases:**

- `import file mismatch`
- `duplicate test module`
- `test_runner.py collision`

**Method:** Configure pytest with `--import-mode=importlib` before renaming tests or changing import paths.

**Evidence:** The fixture fails before the method is applied and passes after the resulting configuration change.

**Tags:** `python`, `pytest`, `debugging`, `codex`

## MVP surfaces

1. **Explore** — searchable memory cards with author, tags, verification status, stars, installs, and version.
2. **Memory detail** — problem, triggers, method, evidence, compatibility, version, fork lineage, and install action.
3. **Publish** — create one sanitized Memory Capsule through an API or fixed UI form.
4. **Install** — write a deterministic local memory package under `.pluribus/installed/<slug>/MEMORY.md` and a machine-readable manifest.
5. **Use** — select relevant installed memories and inject them into a bounded Codex prompt through the existing Codex adapter.
6. **Receipt** — record that a memory matched, was injected, was reported as used, affected named files, and was followed by coordinator-run verification.

## Honest boundary

The MVP does **not** claim to mutate hidden Codex model memory. Pluribus manages explicit local memory packages and injects relevant content into Codex task context. The demo must describe this as an installed Pluribus memory used by Codex.

## Shared contract

### Memory Capsule

```json
{
  "id": "mem_pytest_importlib_v1",
  "slug": "fix-pytest-module-collisions",
  "title": "Fix duplicate pytest module collisions",
  "summary": "Use pytest importlib mode when duplicate test module names collide.",
  "problem": "Pytest raises import file mismatch during collection.",
  "triggers": ["import file mismatch", "duplicate test module", "test_runner.py collision"],
  "steps": [
    "Confirm the collision is caused by duplicate test module basenames.",
    "Set pytest addopts to --import-mode=importlib.",
    "Run the full suite and preserve the output as evidence."
  ],
  "tags": ["python", "pytest", "debugging", "codex"],
  "author": {"id": "dev_alice", "display_name": "Alice Chen"},
  "version": "1.0.0",
  "compatibility": ["python>=3.11", "pytest>=8"],
  "status": "verified",
  "verification": {
    "command": ["pytest", "-q"],
    "exit_code": 0,
    "passed": 4,
    "evidence_excerpt": "4 passed"
  },
  "stars": 128,
  "installs": 1402,
  "fork_of": null,
  "created_at": "2026-07-18T10:00:00Z"
}
```

### Install Manifest

```json
{
  "memory_id": "mem_pytest_importlib_v1",
  "slug": "fix-pytest-module-collisions",
  "version": "1.0.0",
  "install_path": ".pluribus/installed/fix-pytest-module-collisions/MEMORY.md",
  "content_sha256": "<sha256>",
  "installed_at": "2026-07-18T10:05:00Z"
}
```

### Usage Receipt

```json
{
  "id": "use_demo_001",
  "memory_id": "mem_pytest_importlib_v1",
  "consumer": "dev_bob",
  "matched_trigger": "import file mismatch",
  "injected_into_codex": true,
  "codex_reported_use": true,
  "effect": "Configured pytest importlib collection mode.",
  "changed_files": ["pyproject.toml"],
  "verification": {
    "command": ["pytest", "-q"],
    "exit_code": 0,
    "output_excerpt": "4 passed"
  },
  "created_at": "2026-07-18T10:08:00Z"
}
```

## Frozen API endpoints

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

`GET /api/demo/snapshot` is the only aggregate endpoint required by the UI. It returns:

```json
{
  "featured_memories": [],
  "installed_memories": [],
  "latest_receipt": null,
  "stats": {
    "published": 0,
    "verified": 0,
    "installs": 0,
    "successful_uses": 0
  }
}
```

## Non-goals for the hackathon

- Real multi-user authentication
- Billing or paid memories
- Arbitrary cloud synchronization
- A social following system
- General multi-agent orchestration UI
- Hidden-state synchronization between models
- Automatic publication of raw Codex transcripts
- Supporting every coding agent

## Demo acceptance criteria

- A seeded verified memory appears in Explore.
- Search for `pytest` returns the memory.
- Install creates the local Markdown package and manifest.
- The installed memory is visible in My Codex.
- A Codex task receives the memory context.
- The fixture changes a named file.
- Coordinator verification returns exit code `0`.
- A Usage Receipt connects publisher, memory, consumer, changed file, and test evidence.
- Replay data is explicitly labeled when the live Codex path is not used.
