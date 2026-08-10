export type ExecutionMode = "live" | "replay";
export type MissionStatus = "created" | "running" | "verified" | "partially_verified" | "failed" | "requires_human_review" | "stopped";
export type AgentStatus = "queued" | "running" | "completed" | "failed" | "timed_out";

export interface AgentRecord {
  id: string;
  role: "Scout" | "Builder" | "Tester" | "Reviewer";
  task: string;
  status: AgentStatus;
  branch?: string;
  duration: string;
  detail: string;
}

export interface KnowledgePatch {
  id: string;
  author: string;
  type: "repository_fact" | "constraint" | "test_result" | "risk";
  status: "proposed" | "source_linked" | "execution_verified" | "disputed";
  summary: string;
  evidence: string;
  deliveredTo: string[];
  consumedBy: Array<{ agent: string; effect: string; changedFiles: string[] }>;
}

export interface VerificationRecord {
  executable: string;
  args: string[];
  workingDirectory: string;
  exitCode: number;
  duration: string;
  output: string;
  coordinatorObserved: true;
}

export interface MissionSnapshot {
  id: string;
  objective: string;
  repository: string;
  baseline: string;
  integrationBranch: string;
  status: MissionStatus;
  startedAt: string;
  agents: AgentRecord[];
  patches: KnowledgePatch[];
  stages: Array<{ label: string; state: "pending" | "active" | "done" | "failed" }>;
  diff: string;
  verification: VerificationRecord;
  review: string[];
  protectedPathsUnchanged: boolean;
}

export interface MissionEvent {
  id: number;
  type: string;
  payload: Partial<MissionSnapshot>;
}
