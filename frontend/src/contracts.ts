export type ExecutionMode = "live" | "replay";
export type MemoryStatus = "verified" | "unverified";

export interface Author {
  id: string;
  display_name: string;
}

export interface MemoryVerification {
  command: string[];
  exit_code: number;
  passed: number;
  evidence_excerpt: string;
}

export interface MemoryCapsule {
  id: string;
  slug: string;
  title: string;
  summary: string;
  problem: string;
  triggers: string[];
  steps: string[];
  tags: string[];
  author: Author;
  version: string;
  compatibility: string[];
  status: MemoryStatus;
  verification: MemoryVerification;
  stars: number;
  installs: number;
  fork_of: string | null;
  created_at: string;
}

export interface InstallManifest {
  memory_id: string;
  slug: string;
  version: string;
  install_path: string;
  content_sha256: string;
  installed_at: string;
}

export interface UsageReceiptVerification {
  command: string[];
  exit_code: number;
  output_excerpt: string;
}

export interface UsageReceipt {
  id: string;
  memory_id: string;
  consumer: string;
  matched_trigger: string;
  injected_into_codex: boolean;
  codex_reported_use: boolean;
  effect: string;
  changed_files: string[];
  verification: UsageReceiptVerification;
  created_at: string;
}

export interface DemoStats {
  published: number;
  verified: number;
  installs: number;
  successful_uses: number;
}

export interface DemoSnapshot {
  featured_memories: MemoryCapsule[];
  installed_memories: InstallManifest[];
  latest_receipt: UsageReceipt | null;
  stats: DemoStats;
}
