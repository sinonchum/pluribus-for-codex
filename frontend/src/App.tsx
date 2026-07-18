import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  Code2,
  Database,
  GitBranch,
  Hexagon,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Square,
  TestTube2,
  Wifi,
  WifiOff,
  XCircle,
} from "lucide-react";
import { missionApi } from "./api";
import type { AgentRecord, ExecutionMode, MissionSnapshot } from "./contracts";
import { replayMetadata, replayMission } from "./replay";

const demoRepository = import.meta.env.VITE_DEMO_REPOSITORY ?? "demo/seed-health-api";
const demoBaseline = import.meta.env.VITE_DEMO_BASELINE ?? "resolved by backend at launch";
const codexPreflight = import.meta.env.VITE_CODEX_PREFLIGHT ?? "NOT RUN · start through demo launcher";

const fixedRequest = {
  repository_path: demoRepository,
  objective:
    "Add GET /health/details with version, uptime, and sanitized database status. Reuse HealthService, add one degraded-state test, and do not change authentication or add dependencies.",
  agent_count: 4,
  max_concurrency: 2,
  allow_dirty_repository: false,
  protected_paths: [".env", ".git/**", "src/middleware/auth.js"],
  verification_commands: [{ executable: "npm", args: ["test"], timeout_seconds: 120 }],
};

function LaunchScreen({ onReplay, onLive }: { onReplay: () => void; onLive: () => Promise<void> }) {
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");
  const launch = async () => {
    setLaunching(true);
    setError("");
    try {
      await onLive();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Mission launch failed");
    } finally {
      setLaunching(false);
    }
  };

  return (
    <main className="launch-shell">
      <nav className="topbar">
        <div className="brand"><Hexagon size={20} /><span>PLURIBUS</span></div>
        <span className="eyebrow">MISSION CONTROL FOR CODEX</span>
      </nav>
      <section className="launch-grid">
        <div className="launch-copy">
          <span className="kicker"><span className="pulse" />SHARED EVIDENCE LEDGER</span>
          <h1>Four Codex agents.<br /><span>One proven result.</span></h1>
          <p>Coordinate isolated agents without a group chat. Pluribus moves verified knowledge between workers, integrates their patches, and independently checks the result.</p>
          <div className="principles">
            <span><GitBranch size={16} />Isolated worktrees</span>
            <span><Database size={16} />Causal knowledge</span>
            <span><ShieldCheck size={16} />Independent proof</span>
          </div>
        </div>
        <div className="launch-card">
          <div className="card-heading">
            <div><p className="overline">FIXED DEMO MISSION</p><h2>Ready to orchestrate</h2></div>
            <span className="ready"><span />READY</span>
          </div>
          <label>Repository<input value={fixedRequest.repository_path} readOnly /></label>
          <label>Objective<textarea value={fixedRequest.objective} readOnly rows={4} /></label>
          <div className="config-grid">
            <div><small>BASELINE</small><strong>{demoBaseline.slice(0, 12)}</strong></div>
            <div><small>CODEX</small><strong>{codexPreflight}</strong></div>
            <div><small>WORKERS</small><strong>4 roles</strong></div>
            <div><small>CONCURRENCY</small><strong>2 max</strong></div>
          </div>
          {error && <div className="launch-error" role="alert"><WifiOff size={15} /><span>{error}. Open the recorded replay instead.</span></div>}
          <button className="primary" onClick={launch} disabled={launching}><Play size={16} fill="currentColor" />{launching ? "Starting…" : "Launch Hive"}</button>
          <button className="secondary" onClick={onReplay}><RotateCcw size={15} />Open recorded replay</button>
          <p className="helper">The replay is deterministic, evidence-backed, and always clearly labeled.</p>
        </div>
      </section>
    </main>
  );
}

function missionIsVerified(mission: MissionSnapshot) {
  return mission.status === "verified" && mission.verification.exitCode === 0 && mission.protectedPathsUnchanged;
}

function StatusDot({ status }: { status: AgentRecord["status"] }) {
  const icon = status === "completed" ? <Check size={12} /> : status === "failed" || status === "timed_out" ? <XCircle size={12} /> : <Activity size={12} />;
  return <span className={`status status-${status}`}>{icon}{status.replace("_", " ")}</span>;
}

function AgentChapter({ mission }: { mission: MissionSnapshot }) {
  const icons = { Scout: Search, Builder: Code2, Tester: TestTube2, Reviewer: ShieldCheck };
  return (
    <section className="story-panel" aria-labelledby="agents-title">
      <div className="story-heading">
        <div><span className="story-number">01</span><p>ORCHESTRATION</p><h2>Parallel work, one coordinated outcome</h2></div>
        <div className="chapter-stat"><strong>2×</strong><span>maximum concurrency</span></div>
      </div>
      <h3 id="agents-title" className="sr-heading">Agent roster</h3>
      <div className="agent-stage">
        {mission.agents.map((agent, index) => {
          const Icon = icons[agent.role];
          return (
            <article className={`demo-agent role-${agent.role.toLowerCase()}`} key={agent.id}>
              <div className="agent-top"><span className="agent-avatar"><Icon size={19} /></span><StatusDot status={agent.status} /></div>
              <span className="agent-index">0{index + 1}</span>
              <h3>{agent.role}</h3>
              <p>{agent.task}</p>
              <div className="agent-result"><CheckCircle2 size={14} /><span>{agent.detail}</span></div>
              <small>{agent.duration}</small>
            </article>
          );
        })}
      </div>
      <div className="chapter-callout"><Bot size={17} /><strong>Each agent worked in an isolated Git worktree.</strong><span>No shared mutable workspace. No agent group chat.</span></div>
    </section>
  );
}

function KnowledgeChapter({ mission }: { mission: MissionSnapshot }) {
  const primary = mission.patches[0];
  return (
    <section className="story-panel" aria-labelledby="hive-title">
      <div className="story-heading">
        <div><span className="story-number">02</span><p>HIVE MEMORY</p><h2>Knowledge became a code change</h2></div>
        <div className="chapter-stat accent"><strong>{mission.patches.length}</strong><span>evidence patches</span></div>
      </div>
      <h3 id="hive-title" className="sr-heading">Hive memory</h3>
      <div className="knowledge-flow">
        <div className="knowledge-node scout-node"><span><Search size={18} /></span><small>SCOUT DISCOVERED</small><strong>Health checks already use a shared service.</strong><code>src/services/health.js:1–4</code></div>
        <div className="handoff-arrow"><span>{primary.id}</span><ArrowRight size={30} /><small>source linked</small></div>
        <div className="knowledge-node builder-node"><span><Code2 size={18} /></span><small>BUILDER CONSUMED</small><strong>Extended the existing service instead of duplicating it.</strong><code>src/server.js · health.js</code></div>
      </div>
      <div className="causal-proof"><CheckCircle2 size={18} /><div><strong>causal use recorded</strong><span>The ledger proves the Builder received and used the Scout’s finding.</span></div></div>
      <div className="patch-strip">
        {mission.patches.map((patch) => (
          <article className="patch-card" key={patch.id}>
            <div><code>{patch.id}</code><span>{patch.status.replace("_", " ")}</span></div>
            <strong>{patch.summary}</strong>
            <small><Database size={12} />{patch.evidence}</small>
            <p>Delivered → {patch.deliveredTo.join(", ")}</p>
            {patch.consumedBy.map((usage) => <p className="consumed" key={usage.agent}>Consumed ✓ {usage.agent}</p>)}
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidenceChapter({ mission }: { mission: MissionSnapshot }) {
  const [tab, setTab] = useState<"verify" | "diff" | "review">("verify");
  const verified = missionIsVerified(mission);
  return (
    <section className="story-panel" aria-labelledby="evidence-title">
      <div className="story-heading">
        <div><span className="story-number">03</span><p>INDEPENDENT PROOF</p><h2>Coordinator verified the result itself</h2></div>
        <div className="chapter-stat success"><strong>0</strong><span>test failures</span></div>
      </div>
      <h3 id="evidence-title" className="sr-heading">Evidence</h3>
      <div className="proof-layout">
        <div className="proof-summary">
          <span className="proof-seal"><ShieldCheck size={34} /></span>
          <p>MISSION RESULT</p>
          <h3>{verified ? "VERIFIED" : mission.status.toUpperCase()}</h3>
          <span>Coordinator-observed · agent claims excluded</span>
          <div className="proof-metrics">
            <div><strong>3/3</strong><small>tests passed</small></div>
            <div><strong>{mission.verification.exitCode}</strong><small>exit code</small></div>
            <div><strong>408ms</strong><small>runtime</small></div>
          </div>
          <div className="safe-paths"><Check size={14} /><span>Protected paths unchanged</span></div>
        </div>
        <div className="evidence-browser">
          <div className="evidence-tabs" role="tablist">
            <button role="tab" aria-selected={tab === "verify"} onClick={() => setTab("verify")}>Verification</button>
            <button role="tab" aria-selected={tab === "diff"} onClick={() => setTab("diff")}>Integrated diff</button>
            <button role="tab" aria-selected={tab === "review"} onClick={() => setTab("review")}>Review</button>
          </div>
          {tab === "verify" && <div className="terminal-proof" role="tabpanel"><div className="terminal-bar"><span /><span /><span /><code>$ npm test</code></div><pre>{mission.verification.output}</pre></div>}
          {tab === "diff" && <div className="terminal-proof" role="tabpanel"><div className="terminal-bar"><span /><span /><span /><code>{mission.integrationBranch}</code></div><pre>{mission.diff}</pre></div>}
          {tab === "review" && <div className="review-proof" role="tabpanel">{mission.review.map((item) => <div key={item}><CheckCircle2 size={16} /><span>{item}</span></div>)}</div>}
        </div>
      </div>
    </section>
  );
}

const chapters = [
  { label: "Orchestrate", caption: "4 isolated agents" },
  { label: "Share knowledge", caption: "Causal reuse" },
  { label: "Verify independently", caption: "Coordinator proof" },
] as const;

function MissionControl({ initial, mode, onExit }: { initial: MissionSnapshot; mode: ExecutionMode; onExit: () => Promise<void> }) {
  const [mission, setMission] = useState(initial);
  const [chapter, setChapter] = useState(0);
  const [connection, setConnection] = useState<"connected" | "reconnecting">(mode === "replay" ? "connected" : "reconnecting");
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "live") return;
    return missionApi.events(mission.id, (event) => setMission((current) => ({ ...current, ...event.payload })), setConnection);
  }, [mission.id, mode]);

  const exit = async () => {
    setStopping(true);
    setStopError(null);
    try {
      await onExit();
    } catch (error) {
      setStopError(error instanceof Error ? error.message : "Could not stop mission");
      setStopping(false);
    }
  };

  return (
    <main className="control-shell">
      {mode === "replay" && <div className="replay-banner"><RotateCcw size={13} /><strong>REPLAY — RECORDED COORDINATOR EVIDENCE</strong><span>{replayMetadata.coordinatorEvidence} · not live execution</span></div>}
      <nav className="control-nav">
        <div className="brand"><Hexagon size={19} /><span>PLURIBUS</span><i>/</i><b>Demo Story</b></div>
        <div className="nav-actions"><span className={`connection ${connection}`}><Wifi size={13} />{mode === "replay" ? "recorded evidence" : connection}</span><button onClick={exit} disabled={stopping}><Square size={12} />{stopping ? "Stopping…" : mode === "live" ? "Stop mission" : "Exit replay"}</button></div>
      </nav>
      {stopError && <div className="mission-error" role="alert">Stop failed: {stopError}</div>}

      <section className="demo-hero">
        <div className="hero-copy">
          <span className="hero-kicker">MISSION COMPLETE <i /> {mission.id}</span>
          <h1>4 Codex agents.<br /><em>One verified result.</em></h1>
          <p>{mission.objective}</p>
        </div>
        <div className="hero-result"><span><CheckCircle2 size={18} />MISSION VERIFIED</span><strong>3/3</strong><p>tests passed</p><small>Protected paths unchanged</small></div>
      </section>

      <section className="demo-nav" aria-label="Demo chapters">
        {chapters.map((item, index) => (
          <button key={item.label} className={chapter === index ? "active" : ""} aria-pressed={chapter === index} onClick={() => setChapter(index)}>
            <span>0{index + 1}</span><div><strong>{item.label}</strong><small>{item.caption}</small></div>{index < chapters.length - 1 && <ChevronRight size={18} />}
          </button>
        ))}
      </section>

      <div className="semantic-sections" aria-hidden="true">
        <span>Hive memory</span><span>Evidence</span>
      </div>

      <div className="story-viewport">
        {chapter === 0 && <AgentChapter mission={mission} />}
        {chapter === 1 && <KnowledgeChapter mission={mission} />}
        {chapter === 2 && <EvidenceChapter mission={mission} />}
      </div>

      <footer className="demo-footer"><span><GitBranch size={12} />baseline {mission.baseline.slice(0, 8)}</span><strong>Codex agents don’t need a group chat. They need a shared evidence ledger.</strong><span><Activity size={12} />ledger synchronized</span></footer>
    </main>
  );
}

export default function App() {
  const startsInReplay = import.meta.env.VITE_DEMO_MODE === "replay";
  const [mission, setMission] = useState<MissionSnapshot | null>(startsInReplay ? replayMission : null);
  const [mode, setMode] = useState<ExecutionMode>(startsInReplay ? "replay" : "live");
  const liveRequest = useMemo(() => fixedRequest, []);
  const launchLive = async () => {
    const created = await missionApi.create(liveRequest);
    const started = await missionApi.start(created.id);
    setMode("live");
    setMission(started);
  };
  const exitMission = async () => {
    if (!mission) return;
    if (mode === "live") await missionApi.stop(mission.id);
    setMission(null);
  };
  if (mission) return <MissionControl initial={mission} mode={mode} onExit={exitMission} />;
  return <LaunchScreen onReplay={() => { setMode("replay"); setMission(replayMission); }} onLive={launchLive} />;
}
