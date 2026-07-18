import type { DemoSnapshot, InstallManifest, MemoryCapsule, UsageReceipt } from "./contracts";

export const replayMemory: MemoryCapsule = {
  id: "mem_billing_audit_handoff_v1",
  slug: "preserve-billing-audit-trail",
  title: "Preserve billing audit trail during invoice transitions",
  summary: "Alice Chen's four-year Billing Platform handoff: route every invoice state change through the audited transition primitive.",
  problem: "Direct invoice status assignments bypass Northstar's append-only financial ledger, erasing the audit evidence required by Finance and Compliance.",
  triggers: ["add a new invoice status", "cancel an invoice", "change billing state", "update invoice status"],
  steps: [
    "Never assign invoice.status directly in Billing Service workflows.",
    "Add the new status to InvoiceStatus, then route the operation through transition_invoice().",
    "Record the ledger event before persisting the new invoice state.",
    "Run uv run pytest -q and preserve the billing audit-trail output as evidence.",
  ],
  tags: ["billing", "audit", "handoff", "codex"],
  author: { id: "dev_alice", display_name: "Alice Chen · Billing, 4 years" },
  version: "1.0.0",
  compatibility: ["northstar-billing>=0.1", "python>=3.11"],
  status: "verified",
  verification: {
    command: ["uv", "run", "pytest", "-q"],
    exit_code: 0,
    passed: 3,
    evidence_excerpt: "3 passed",
  },
  stars: 47,
  installs: 18,
  fork_of: null,
  created_at: "2026-07-18T10:00:00Z",
};

export const replayInstallManifest: InstallManifest = {
  memory_id: "mem_billing_audit_handoff_v1",
  slug: "preserve-billing-audit-trail",
  version: "1.0.0",
  install_path: ".pluribus/installed/preserve-billing-audit-trail/MEMORY.md",
  content_sha256: "sha256:recorded-billing-handoff-package",
  installed_at: "2026-07-18T10:05:00Z",
};

export const replayReceipt: UsageReceipt = {
  id: "use_handoff_demo_001",
  memory_id: "mem_billing_audit_handoff_v1",
  consumer: "Bob · Successor Engineer",
  matched_trigger: "add a new invoice status",
  injected_into_codex: true,
  codex_reported_use: true,
  effect: "Preserved Alice's append-only billing audit rule while adding invoice cancellation.",
  changed_files: ["billing/invoices.py"],
  verification: {
    command: ["uv", "run", "pytest", "-q"],
    exit_code: 0,
    output_excerpt: "3 passed",
  },
  created_at: "2026-07-18T10:08:00Z",
};

export const replaySnapshot: DemoSnapshot = {
  featured_memories: [replayMemory],
  installed_memories: [],
  latest_receipt: replayReceipt,
  stats: { published: 1, verified: 1, installs: 18, successful_uses: 1 },
};

export const replayMetadata = {
  label: "REPLAY — RECORDED EVIDENCE",
  source: "sanitized deterministic billing handoff fixture",
  live: false,
} as const;
