import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowRight, Bot, Box, Check, CheckCircle2, CircleDot, Clock3,
  Code2, Database, GitBranch, Hexagon, Play, Radio, RotateCcw, Search,
  ShieldCheck, Square, TestTube2, Users, Wifi, WifiOff, XCircle
} from "lucide-react";
import { missionApi } from "./api";
import type { AgentRecord, ExecutionMode, MissionSnapshot } from "./contracts";
import { replayMetadata, replayMission } from "./replay";

const demoRepository = import.meta.env.VITE_DEMO_REPOSITORY ?? "demo/seed-health-api";
const demoBaseline = import.meta.env.VITE_DEMO_BASELINE ?? "resolved by backend at launch";
const codexPreflight = import.meta.env.VITE_CODEX_PREFLIGHT ?? "NOT RUN · start through demo launcher";

const fixedRequest = {
  repository_path: demoRepository,
  objective: "Add GET /health/details with version, uptime, and sanitized database status. Reuse HealthService, add one degraded-state test, and do not change authentication or add dependencies.",
  agent_count: 4,
  max_concurrency: 2,
  allow_dirty_repository: false,
  protected_paths: [".env", ".git/**", "src/middleware/auth.js"],
  verification_commands: [{ executable: "npm", args: ["test"], timeout_seconds: 120 }]
};

function StatusDot({ status }: { status: AgentRecord["status"] }) {
  const icon = status === "completed" ? <Check size={11} /> : status === "failed" || status === "timed_out" ? <XCircle size={11} /> : <CircleDot size={11} />;
  return <span className={`status status-${status}`}>{icon}{status.replace("_", " ")}</span>;
}

function LaunchScreen({ onReplay, onLive }: { onReplay: () => void; onLive: () => Promise<void> }) {
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");
  const launch = async () => { setLaunching(true); setError(""); try { await onLive(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Mission launch failed"); } finally { setLaunching(false); } };
  return <main className="launch-shell">
    <nav className="topbar"><div className="brand"><Hexagon size={20}/><span>PLURIBUS</span></div><span className="eyebrow">CODEX COLLECTIVE</span></nav>
    <section className="launch-grid">
      <div className="launch-copy">
        <span className="kicker"><span className="pulse"/>MISSION CONTROL</span>
        <h1>Many agents.<br/><span>One evidence ledger.</span></h1>
        <p>Launch four isolated Codex workers. Watch verified discoveries propagate, patches integrate, and the Coordinator prove the result.</p>
        <div className="principles"><span><ShieldCheck size={16}/> Evidence-backed</span><span><GitBranch size={16}/> Worktree isolated</span><span><CheckCircle2 size={16}/> Independently verified</span></div>
      </div>
      <div className="launch-card">
        <div className="card-heading"><div><p className="overline">FIXED DEMO MISSION</p><h2>Launch Hive</h2></div><span className="ready"><span/>READY</span></div>
        <label>Repository<input value={fixedRequest.repository_path} readOnly /></label>
        <label>Objective<textarea value={fixedRequest.objective} readOnly rows={4}/></label>
        <div className="config-grid">
          <div><small>BASELINE</small><strong>{demoBaseline.slice(0, 12)}</strong></div><div><small>GIT TREE</small><strong>Clean baseline</strong></div>
          <div><small>CODEX PREFLIGHT</small><strong>{codexPreflight}</strong></div><div><small>WORKTREE PLAN</small><strong>2 writers + coordinator</strong></div>
          <div><small>WORKERS</small><strong>4 roles</strong></div><div><small>CONCURRENCY</small><strong>2 max</strong></div><div><small>TIMEOUT</small><strong>12 min</strong></div><div><small>REPAIR</small><strong>1 round</strong></div>
        </div>
        <div className="command"><span>$</span><code>npm test</code><small>cwd: {demoRepository} · 120s</small></div>
        {error && <div className="launch-error" role="alert"><WifiOff size={15}/><span>{error}. Backend unavailable? Open the recorded replay.</span></div>}
        <button className="primary" onClick={launch} disabled={launching}><Play size={16} fill="currentColor"/>{launching ? "Starting…" : "Launch Hive"}</button>
        <button className="secondary" onClick={onReplay}><RotateCcw size={15}/>Open recorded replay</button>
        <p className="helper">Replay is deterministic and always labeled. It is never presented as live execution.</p>
      </div>
    </section>
  </main>;
}

function AgentRoster({ mission }: { mission: MissionSnapshot }) {
  const icons = { Scout: Search, Builder: Code2, Tester: TestTube2, Reviewer: ShieldCheck };
  return <section className="panel agents-panel" aria-labelledby="agents-title">
    <header><div><p className="overline">COLLECTIVE</p><h2 id="agents-title">Agent roster</h2></div><span className="counter">{mission.agents.length}</span></header>
    <div className="agent-list">{mission.agents.map(agent => { const Icon = icons[agent.role]; return <article className="agent" key={agent.id}>
      <div className={`agent-icon role-${agent.role.toLowerCase()}`}><Icon size={17}/></div>
      <div className="agent-main"><div className="agent-line"><strong>{agent.role}</strong><StatusDot status={agent.status}/></div><span>{agent.id}</span><p>{agent.task}</p><small>{agent.detail}</small>{agent.branch && <code><GitBranch size={11}/>{agent.branch}</code>}</div>
      <span className="duration"><Clock3 size={12}/>{agent.duration}</span>
    </article>; })}</div>
  </section>;
}

function HiveMemory({ mission }: { mission: MissionSnapshot }) {
  const [selected, setSelected] = useState(mission.patches[0]?.id);
  return <section className="panel hive-panel" aria-labelledby="hive-title">
    <header><div><p className="overline">SHARED EVIDENCE</p><h2 id="hive-title">Hive memory</h2></div><span className="source-count">{mission.patches.length} patches</span></header>
    <div className="causal-summary"><div className="node scout"><Search size={14}/>Scout</div><div className="flow"><span>kp_018</span><ArrowRight size={18}/></div><div className="node builder"><Code2 size={14}/>Builder</div><div className="causal-proof"><Check size={12}/>causal use recorded</div></div>
    <div className="patch-list">{mission.patches.map(patch => <button key={patch.id} className={`patch ${selected === patch.id ? "selected" : ""}`} onClick={() => setSelected(patch.id)}>
      <div className="patch-top"><code>{patch.id}</code><span className={`knowledge-status ks-${patch.status}`}>{patch.status.replace("_", " ")}</span></div>
      <strong>{patch.summary}</strong><small>{patch.author} · {patch.type.replace("_", " ")}</small>
      <div className="evidence"><Database size={13}/><span>{patch.evidence}</span></div>
      <div className="delivery"><span className="delivered">Delivered → {patch.deliveredTo.join(", ")}</span>{patch.consumedBy.map(use => <span className="consumed" key={use.agent}>Consumed ✓ {use.agent}</span>)}</div>
      {selected === patch.id && patch.consumedBy.map(use => <div className="usage" key={use.agent}><p>{use.effect}</p><code>{use.changedFiles.join(" · ")}</code></div>)}
    </button>)}</div>
  </section>;
}

function missionIsVerified(mission: MissionSnapshot) {
  return mission.status === "verified" && mission.verification.exitCode === 0 && mission.protectedPathsUnchanged;
}

function missionStatusLabel(mission: MissionSnapshot) {
  return missionIsVerified(mission) ? "VERIFIED" : mission.status.replaceAll("_", " ").toUpperCase();
}

function EvidencePanel({ mission }: { mission: MissionSnapshot }) {
  const [tab, setTab] = useState<"diff"|"verify"|"review">("verify");
  const verification = mission.verification;
  const verified = missionIsVerified(mission);
  return <section className="panel evidence-panel" aria-labelledby="evidence-title">
    <header><div><p className="overline">COORDINATOR PROOF</p><h2 id="evidence-title">Evidence</h2></div><span className={verified ? "verified" : "status status-running"}>{verified ? <CheckCircle2 size={14}/> : <Activity size={14}/>} {missionStatusLabel(mission)}</span></header>
    <div className="tabs" role="tablist">
      <button role="tab" aria-selected={tab === "diff"} className={tab === "diff" ? "active" : ""} onClick={() => setTab("diff")}>Integrated diff</button>
      <button role="tab" aria-selected={tab === "verify"} className={tab === "verify" ? "active" : ""} onClick={() => setTab("verify")}>Verification</button>
      <button role="tab" aria-selected={tab === "review"} className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>Review</button>
    </div>
    {tab === "diff" && <div className="diff-wrap" role="tabpanel"><div className="diff-meta"><GitBranch size={13}/><code>{mission.integrationBranch}</code></div><pre className="diff">{mission.diff}</pre></div>}
    {tab === "verify" && <div className="verify-view" role="tabpanel">
      <div className={`proof-card ${verified ? "success" : ""}`}><div className="proof-icon">{verified ? <CheckCircle2 size={20}/> : <Activity size={20}/>}</div><div><small>COORDINATOR-OBSERVED</small><h3>{verified ? "All required checks passed" : `Mission ${missionStatusLabel(mission).toLowerCase()}`}</h3><p>Agent claims are excluded from this result.</p></div><strong>exit {verification.exitCode}</strong></div>
      <div className="command-detail"><div><small>EXECUTABLE</small><code>{verification.executable}</code></div><div><small>ARGUMENTS</small><code>{verification.args.join(" ")}</code></div><div><small>DURATION</small><code>{verification.duration}</code></div></div>
      <div className="working-dir"><small>WORKING DIRECTORY</small><code>{verification.workingDirectory}</code></div>
      <pre className="output">{verification.output}</pre>
      <div className="protected"><ShieldCheck size={16}/><div><strong>{mission.protectedPathsUnchanged ? "Protected files unchanged" : "Protected-path check failed"}</strong><span>.env · .git/** · src/middleware/auth.js</span></div>{mission.protectedPathsUnchanged ? <Check size={16}/> : <XCircle size={16}/>}</div>
    </div>}
    {tab === "review" && <div className="review-list" role="tabpanel">{mission.review.map(item => <div key={item}><Check size={15}/><span>{item}</span></div>)}</div>}
  </section>;
}

function MissionControl({ initial, mode, onExit }: { initial: MissionSnapshot; mode: ExecutionMode; onExit: () => Promise<void> }) {
  const [mission, setMission] = useState(initial);
  const [connection, setConnection] = useState<"connected"|"reconnecting">(mode === "replay" ? "connected" : "reconnecting");
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const verified = missionIsVerified(mission);
  useEffect(() => {
    if (mode !== "live") return;
    return missionApi.events(mission.id, event => setMission(current => ({ ...current, ...event.payload })), setConnection);
  }, [mission.id, mode]);
  const exit = async () => {
    setStopping(true);
    setStopError(null);
    try { await onExit(); }
    catch (error) { setStopError(error instanceof Error ? error.message : "Could not stop mission"); setStopping(false); }
  };
  return <main className="control-shell">
    {mode === "replay" && <div className="replay-banner"><RotateCcw size={14}/><strong>REPLAY — RECORDED COORDINATOR EVIDENCE</strong><span>{replayMetadata.coordinatorEvidence} · agent timeline is {replayMetadata.agentTimeline} · not live execution</span></div>}
    <nav className="control-nav"><div className="brand"><Hexagon size={19}/><span>PLURIBUS</span><i>/</i><b>Mission Control</b></div><div className="nav-actions"><span className={`connection ${connection}`}><Wifi size={13}/>{mode === "replay" ? "recorded" : connection}</span><button onClick={exit} disabled={stopping}><Square size={13}/>{stopping ? "Stopping…" : mode === "live" ? "Stop mission" : "Exit replay"}</button></div></nav>
    {stopError && <div className="mission-error" role="alert">Stop failed: {stopError}. Workers may still be running.</div>}
    <header className="mission-header">
      <div><div className="mission-meta"><code>{mission.id}</code><span>baseline {mission.baseline}</span></div><h1>{mission.objective}</h1><p><Box size={14}/>{mission.repository}</p></div>
      <div className={`result ${verified ? "" : "pending"}`}><span>MISSION RESULT</span><strong>{verified ? <CheckCircle2 size={20}/> : <Activity size={20}/>} {missionStatusLabel(mission)}</strong><small>exit {mission.verification.exitCode} · protected paths {mission.protectedPathsUnchanged ? "passed" : "failed"}</small></div>
    </header>
    <div className="stage-rail">{mission.stages.map((stage, index) => <div className={`stage ${stage.state}`} key={stage.label}><span>{stage.state === "done" ? <Check size={12}/> : index + 1}</span><b>{stage.label}</b>{index < mission.stages.length - 1 && <i/>}</div>)}</div>
    <div className="mission-grid"><AgentRoster mission={mission}/><HiveMemory mission={mission}/><EvidencePanel mission={mission}/></div>
    <footer><span>Started {new Date(mission.startedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span><span><Activity size={12}/>{connection === "connected" ? "Evidence ledger synchronized" : "Evidence stream reconnecting"}</span></footer>
  </main>;
}

export default function App() {
  const startsInReplay = import.meta.env.VITE_DEMO_MODE === "replay";
  const [mission, setMission] = useState<MissionSnapshot | null>(startsInReplay ? replayMission : null);
  const [mode, setMode] = useState<ExecutionMode>(startsInReplay ? "replay" : "live");
  const liveRequest = useMemo(() => fixedRequest, []);
  const launchLive = async () => { const created = await missionApi.create(liveRequest); const started = await missionApi.start(created.id); setMode("live"); setMission(started); };
  const exitMission = async () => {
    if (!mission) return;
    if (mode === "live") await missionApi.stop(mission.id);
    setMission(null);
  };
  if (mission) return <MissionControl initial={mission} mode={mode} onExit={exitMission}/>;
  return <LaunchScreen onReplay={() => { setMode("replay"); setMission(replayMission); }} onLive={launchLive}/>;
}
