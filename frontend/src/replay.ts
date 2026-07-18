import type { DemoSnapshot, InstallManifest, MemoryCapsule, UsageReceipt } from "./contracts";

export const replayMemory: MemoryCapsule = {
  id: "mem_pytest_importlib_v1",
  slug: "fix-pytest-module-collisions",
  title: "Fix duplicate pytest module collisions",
  summary: "Use pytest importlib mode when duplicate test module names collide.",
  problem: "Pytest raises import file mismatch during collection.",
  triggers: ["import file mismatch", "duplicate test module", "test_runner.py collision"],
  steps: [
    "Confirm the collision is caused by duplicate test module basenames.",
    "Set pytest addopts to --import-mode=importlib.",
    "Run the full suite and preserve the output as evidence.",
  ],
  tags: ["python", "pytest", "debugging", "codex"],
  author: { id: "dev_alice", display_name: "Alice Chen" },
  version: "1.0.0",
  compatibility: ["python>=3.11", "pytest>=8"],
  status: "verified",
  verification: {
    command: ["pytest", "-q"],
    exit_code: 0,
    passed: 4,
    evidence_excerpt: "4 passed",
  },
  stars: 128,
  installs: 1402,
  fork_of: null,
  created_at: "2026-07-18T10:00:00Z",
};

export const replayInstallManifest: InstallManifest = {
  memory_id: "mem_pytest_importlib_v1",
  slug: "fix-pytest-module-collisions",
  version: "1.0.0",
  install_path: ".pluribus/installed/fix-pytest-module-collisions/MEMORY.md",
  content_sha256: "sha256:recorded-demo-memory-package",
  installed_at: "2026-07-18T10:05:00Z",
};

export const replayReceipt: UsageReceipt = {
  id: "use_demo_001",
  memory_id: "mem_pytest_importlib_v1",
  consumer: "dev_bob",
  matched_trigger: "import file mismatch",
  injected_into_codex: true,
  codex_reported_use: true,
  effect: "Configured pytest importlib collection mode.",
  changed_files: ["pyproject.toml"],
  verification: {
    command: ["pytest", "-q"],
    exit_code: 0,
    output_excerpt: "4 passed",
  },
  created_at: "2026-07-18T10:08:00Z",
};

export const replaySnapshot: DemoSnapshot = {
  featured_memories: [replayMemory],
  installed_memories: [],
  latest_receipt: replayReceipt,
  stats: {
    published: 1,
    verified: 1,
    installs: 1402,
    successful_uses: 1,
  },
};

export const replayMetadata = {
  label: "REPLAY — RECORDED EVIDENCE",
  source: "sanitized deterministic fixture",
  live: false,
} as const;
