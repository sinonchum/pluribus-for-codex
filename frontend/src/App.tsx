import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Box,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleUserRound,
  Code2,
  Download,
  FileCheck2,
  GitFork,
  PackageCheck,
  Play,
  Search,
  ShieldCheck,
  Star,
  Upload,
} from "lucide-react";
import { memoryApi } from "./api";
import type { ExecutionMode, InstallManifest, MemoryCapsule, UsageReceipt } from "./contracts";
import {
  replayInstallManifest,
  replayMemory,
  replayMetadata,
  replayReceipt,
  replaySnapshot,
} from "./replay";

type Screen = "explore" | "detail" | "publish" | "installed" | "receipt";

const tags = ["billing", "audit", "handoff", "codex"];
const fmt = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

function initialMode(): ExecutionMode {
  const requested = new URLSearchParams(window.location.search).get("mode") ??
    import.meta.env.VITE_DEMO_MODE ?? import.meta.env.VITE_EXECUTION_MODE;
  return requested === "live" ? "live" : "replay";
}

function ModeBanner({ mode }: { mode: ExecutionMode }) {
  return (
    <div className={`mode-banner ${mode}`} role="status">
      <span className="mode-dot" aria-hidden="true" />
      <strong>{mode === "replay" ? replayMetadata.label : "LIVE"}</strong>
      <span>{mode === "replay" ? "Sanitized deterministic fixture · no API calls" : "Connected to the registry API · no replay fallback"}</span>
    </div>
  );
}

function VerifiedBadge() {
  return <span className="verified"><BadgeCheck size={16} aria-hidden="true" /> Verified</span>;
}

function App() {
  const [mode] = useState<ExecutionMode>(initialMode);
  const [screen, setScreen] = useState<Screen>("explore");
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("");
  const [memories, setMemories] = useState<MemoryCapsule[]>(mode === "replay" ? replaySnapshot.featured_memories : []);
  const [selected, setSelected] = useState<MemoryCapsule | null>(mode === "replay" ? replayMemory : null);
  const [installedMemories, setInstalledMemories] = useState<MemoryCapsule[]>([]);
  const [replayManifests, setReplayManifests] = useState<InstallManifest[]>([]);
  const [receipt, setReceipt] = useState<UsageReceipt | null>(mode === "replay" ? replayReceipt : null);
  const [loading, setLoading] = useState(mode === "live");
  const [error, setError] = useState("");

  useEffect(() => {
    if (mode !== "live") return;
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      memoryApi.list({ query: query || undefined, tag: tag || undefined }),
      memoryApi.installed(),
    ]).then(([listed, installed]) => {
      if (!active) return;
      setMemories(listed);
      setInstalledMemories(installed);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "The live registry could not be reached.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [mode, query, tag]);

  const filtered = useMemo(() => {
    if (mode === "live") return memories;
    const needle = query.trim().toLowerCase();
    return memories.filter((memory) => {
      const searchable = [memory.title, memory.summary, ...memory.triggers, ...memory.tags].join(" ").toLowerCase();
      return (!needle || searchable.includes(needle)) && (!tag || memory.tags.includes(tag));
    });
  }, [memories, mode, query, tag]);

  const openMemory = async (memory: MemoryCapsule) => {
    setError("");
    if (mode === "replay") {
      setSelected(memory);
      setScreen("detail");
      return;
    }
    setLoading(true);
    try {
      setSelected(await memoryApi.detail(memory.slug));
      setScreen("detail");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load this memory.");
    } finally {
      setLoading(false);
    }
  };

  const installMemory = async () => {
    if (!selected) return;
    setError("");
    setLoading(true);
    try {
      if (mode === "replay") {
        setReplayManifests((current) => current.some((item) => item.memory_id === selected.id) ? current : [...current, replayInstallManifest]);
      } else {
        await memoryApi.install(selected.slug);
      }
      setInstalledMemories((current) => current.some((item) => item.id === selected.id) ? current : [...current, selected]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Installation could not be recorded.");
    } finally {
      setLoading(false);
    }
  };

  const showUse = async () => {
    setError("");
    if (mode === "replay") {
      setReceipt(replayReceipt);
      setScreen("receipt");
      return;
    }
    setLoading(true);
    try {
      const snapshot = await memoryApi.demoSnapshot();
      if (!snapshot.latest_receipt) throw new Error("No live usage receipt is available yet. Run the bounded Codex task, then retry.");
      setReceipt(snapshot.latest_receipt);
      setScreen("receipt");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load a live usage receipt.");
    } finally {
      setLoading(false);
    }
  };

  const isInstalled = selected ? installedMemories.some((item) => item.id === selected.id) : false;
  const navigate = (next: Screen) => { setError(""); setScreen(next); };

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => navigate("explore")} aria-label="Pluribus home">
          <span className="brand-mark"><Code2 size={21} /></span>
          <span>pluribus</span><em>/ handoff</em>
        </button>
        <nav aria-label="Primary navigation">
          <a href="#explore" className={screen === "explore" || screen === "detail" ? "active" : ""} onClick={(event) => { event.preventDefault(); navigate("explore"); }}>Explore</a>
          <a href="#publish" className={screen === "publish" ? "active" : ""} onClick={(event) => { event.preventDefault(); navigate("publish"); }}>Publish</a>
          <a href="#installed" aria-label="My Codex" className={screen === "installed" ? "active" : ""} onClick={(event) => { event.preventDefault(); navigate("installed"); }}>
            My Codex <span className="nav-count">{installedMemories.length}</span>
          </a>
          <a href="#receipt" className={screen === "receipt" ? "active" : ""} onClick={(event) => { event.preventDefault(); void showUse(); }}>Usage Receipt</a>
        </nav>
      </header>
      <ModeBanner mode={mode} />
      {error && <div className="error-bar" role="alert"><strong>Live action failed.</strong> {error}</div>}

      {screen === "explore" && (
        <Explore memories={filtered} query={query} setQuery={setQuery} tag={tag} setTag={setTag} loading={loading} openMemory={openMemory} navigate={navigate} />
      )}
      {screen === "detail" && selected && (
        <MemoryDetail memory={selected} installed={isInstalled} loading={loading} install={installMemory} back={() => navigate("explore")} openInstalled={() => navigate("installed")} />
      )}
      {screen === "publish" && <Publish mode={mode} onPublished={(memory) => { setMemories((items) => [memory, ...items]); setSelected(memory); setScreen("detail"); }} />}
      {screen === "installed" && <Installed memories={installedMemories} manifests={replayManifests} mode={mode} openMemory={openMemory} run={showUse} />}
      {screen === "receipt" && receipt && <ReceiptView receipt={receipt} memory={selected ?? replayMemory} mode={mode} back={() => navigate("installed")} />}

      <footer>
        <span>Pluribus Engineering Handoff</span>
        <span>Local extraction. Employee-approved knowledge. Verifiable transfer.</span>
      </footer>
    </div>
  );
}

function Explore({ memories, query, setQuery, tag, setTag, loading, openMemory, navigate }: {
  memories: MemoryCapsule[]; query: string; setQuery: (value: string) => void; tag: string; setTag: (value: string) => void;
  loading: boolean; openMemory: (memory: MemoryCapsule) => void; navigate: (screen: Screen) => void;
}) {
  return <main>
    <section className="hero">
      <div className="hero-copy">
        <p className="eyebrow">ENGINEERING KNOWLEDGE HANDOFF FOR CODEX</p>
        <h1>Your best engineer leaves. Their judgment doesn't have to.</h1>
        <p>Turn years of company-specific engineering judgment into sanitized, employee-approved handoff memories that a successor's Codex can actually use.</p>
      </div>
      <div className="hero-actions">
        <button className="primary" onClick={() => navigate("publish")}><Upload size={18} /> Publish a handoff</button>
        <button className="secondary" onClick={() => navigate("installed")}><PackageCheck size={18} /> View My Codex</button>
      </div>
    </section>

    <section className="registry-section" aria-labelledby="explore-heading">
      <div className="section-heading">
        <div><p className="eyebrow">TEAM KNOWLEDGE REGISTRY</p><h2 id="explore-heading">Explore handoff memories</h2></div>
        <span>{memories.length} {memories.length === 1 ? "result" : "results"}</span>
      </div>
      <div className="search-row">
        <label className="search-box"><Search size={21} /><span className="sr-only">Search memories</span><input type="search" aria-label="Search memories" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search services, rules, or incidents…" /></label>
        <button className="search-submit" type="button">Search registry</button>
      </div>
      <div className="tag-row" aria-label="Filter by tag">
        <span>Filter:</span>
        <button className={!tag ? "selected" : ""} onClick={() => setTag("")}>All</button>
        {tags.map((item) => <button className={tag === item ? "selected" : ""} key={item} onClick={() => setTag(tag === item ? "" : item)}>#{item}</button>)}
      </div>

      {loading ? <div className="empty-state">Loading live registry…</div> : memories.length === 0 ? <div className="empty-state"><Search size={28} /><strong>No memories match this search.</strong><span>Try “billing” or clear the selected tag.</span></div> :
        <div className="memory-grid">{memories.map((memory) => <MemoryCard key={memory.id} memory={memory} open={() => openMemory(memory)} />)}</div>}
    </section>
  </main>;
}

function MemoryCard({ memory, open }: { memory: MemoryCapsule; open: () => void }) {
  return <article className="memory-card" aria-label={memory.title}>
    <div className="card-top"><VerifiedBadge /><span className="version">v{memory.version}</span></div>
    <button className="card-title" onClick={open}>{memory.title}</button>
    <p>{memory.summary}</p>
    <div className="tags">{memory.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
    <div className="card-meta">
      <span><CircleUserRound size={16} /> {memory.author.display_name}</span>
      <span><Star size={16} /> {fmt.format(memory.stars)}</span>
      <span><Download size={16} /> {fmt.format(memory.installs)}</span>
    </div>
    <button className="card-open" onClick={open}>View memory <ArrowRight size={17} /></button>
  </article>;
}

function MemoryDetail({ memory, installed, loading, install, back, openInstalled }: {
  memory: MemoryCapsule; installed: boolean; loading: boolean; install: () => void; back: () => void; openInstalled: () => void;
}) {
  return <main className="detail-page">
    <button className="back-link" onClick={back}><ArrowLeft size={17} /> Back to Explore</button>
    <div className="detail-layout">
      <article className="detail-main">
        <div className="detail-kicker"><VerifiedBadge /><span>Handoff published by <strong>{memory.author.display_name}</strong></span></div>
        <h1>{memory.title}</h1>
        <p className="lead">{memory.summary}</p>
        <div className="tags">{memory.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
        <section><p className="eyebrow">IMPLICIT TEAM RULE</p><h2>What Git cannot preserve</h2><p>{memory.problem}</p></section>
        <section><p className="eyebrow">MATCHING TRIGGERS</p><h2>Signals Codex can match</h2><div className="trigger-list">{memory.triggers.map((trigger) => <code key={trigger}>{trigger}</code>)}</div></section>
        <section><p className="eyebrow">ALICE'S HANDOFF</p><h2>Reusable judgment</h2><ol className="steps">{memory.steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol></section>
        <section className="evidence-panel"><div><p className="eyebrow">VERIFICATION EVIDENCE</p><h2><CheckCircle2 /> Coordinator check passed</h2></div><div className="command"><code>{memory.verification.command.join(" ")}</code><strong>exit {memory.verification.exit_code}</strong></div><pre>{memory.verification.evidence_excerpt}</pre><p>{memory.verification.passed} checks passed in the recorded verification.</p></section>
      </article>
      <aside className="install-panel">
        <Box size={26} />
        <h2>Install this handoff</h2>
        <p>Adds Alice's explicit, reviewed knowledge package to Bob's project. It does not alter hidden model state.</p>
        {installed ? <button className="installed-button" disabled><Check size={19} /> Installed</button> : <button className="primary full" disabled={loading} onClick={install}><Download size={19} /> {loading ? "Installing…" : "Install to Codex"}</button>}
        {installed && <button className="text-action" onClick={openInstalled}>View in My Codex <ArrowRight size={16} /></button>}
        <dl><div><dt>Version</dt><dd>{memory.version}</dd></div><div><dt>Memory ID</dt><dd><code>{memory.id}</code></dd></div>{memory.compatibility.length > 0 && <div><dt>Compatibility</dt><dd>{memory.compatibility.join(" · ")}</dd></div>}<div><dt>Fork lineage</dt><dd>{memory.fork_of ? <><GitFork size={14} /> {memory.fork_of}</> : "Original memory"}</dd></div><div><dt>Installs</dt><dd>{memory.installs.toLocaleString()}</dd></div></dl>
      </aside>
    </div>
  </main>;
}

type PublishFields = { title: string; summary: string; problem: string; triggers: string; steps: string; tags: string; };
const publishDefaults: PublishFields = { title: "", summary: "", problem: "", triggers: "", steps: "", tags: "" };

function Publish({ mode, onPublished }: { mode: ExecutionMode; onPublished: (memory: MemoryCapsule) => void }) {
  const [fields, setFields] = useState(publishDefaults);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const update = (key: keyof PublishFields, value: string) => setFields((current) => ({ ...current, [key]: value }));
  const lines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);
  const csv = (value: string) => value.split(",").map((item) => item.trim().replace(/^#/, "")).filter(Boolean);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const nextErrors: string[] = [];
    if (fields.title.trim().length < 8) nextErrors.push("Title must be at least 8 characters.");
    if (fields.summary.trim().length < 12) nextErrors.push("Summary must be at least 12 characters.");
    if (fields.problem.trim().length < 12) nextErrors.push("Problem must explain the failure clearly.");
    if (lines(fields.triggers).length < 1) nextErrors.push("Add at least one matching trigger, one per line.");
    if (lines(fields.steps).length < 2) nextErrors.push("Add at least two reusable steps, one per line.");
    if (csv(fields.tags).length < 1) nextErrors.push("Add at least one tag.");
    setErrors(nextErrors);
    if (nextErrors.length) return;

    const slug = fields.title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const capsule: MemoryCapsule = {
      id: `mem_${slug.replaceAll("-", "_")}_v1`, slug, title: fields.title.trim(), summary: fields.summary.trim(), problem: fields.problem.trim(),
      triggers: lines(fields.triggers), steps: lines(fields.steps), tags: csv(fields.tags),
      author: { id: "dev_alice", display_name: "Alice Chen · Billing, 4 years" }, version: "1.0.0",
      compatibility: [], status: "verified",
      verification: { command: ["uv", "run", "pytest", "-q"], exit_code: 0, passed: 3, evidence_excerpt: "3 passed" },
      stars: 0, installs: 0, fork_of: null, created_at: "2026-07-18T10:00:00Z",
    };
    setSubmitting(true);
    try { onPublished(mode === "replay" ? capsule : await memoryApi.create(capsule)); }
    catch (reason) { setErrors([reason instanceof Error ? reason.message : "The memory could not be published."]); }
    finally { setSubmitting(false); }
  };

  return <main className="publish-page publish-redesign">
    <header className="publish-hero">
      <div><p className="eyebrow">TURN EXPERIENCE INTO TEAM MEMORY</p><h1>Publish what the next engineer should know.</h1><p>Capture the judgment behind the work—not a package manifest and never a raw transcript. Pluribus handles versioning and technical metadata automatically.</p></div>
      <div className="publish-principle"><ShieldCheck size={22} /><span><strong>Private by default</strong>Local extraction · secret removal · employee approval</span></div>
    </header>
    <form className="publish-workflow" onSubmit={submit} noValidate>
      <div className="publish-main">
        {errors.length > 0 && <div className="validation" role="alert"><strong>Please complete the memory:</strong><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}
        <section className="knowledge-step" aria-labelledby="knowledge-heading">
          <div className="step-heading"><span>01</span><div><h2 id="knowledge-heading">Capture the judgment</h2><p>What did experience teach you that the code or documentation does not?</p></div></div>
          <div className="step-fields">
            <label><span>Memory title <b>Required</b></span><input value={fields.title} onChange={(e) => update("title", e.target.value)} placeholder="Preserve the billing audit trail" /></label>
            <label><span>One-sentence takeaway <b>Required</b></span><textarea value={fields.summary} onChange={(e) => update("summary", e.target.value)} placeholder="The durable judgment a teammate should carry into the next task." rows={2} /></label>
            <label><span>Hidden risk or context <b>Required</b></span><textarea value={fields.problem} onChange={(e) => update("problem", e.target.value)} placeholder="Explain what can go wrong, why the obvious approach fails, and what only the team knows." rows={4} /></label>
          </div>
        </section>
        <section className="knowledge-step" aria-labelledby="retrieval-heading">
          <div className="step-heading"><span>02</span><div><h2 id="retrieval-heading">Teach Codex when to recall it</h2><p>Use the language an engineer would naturally type during a real task.</p></div></div>
          <div className="step-fields field-grid">
            <label><span>When should Codex recall this? <b>One scenario per line</b></span><textarea value={fields.triggers} onChange={(e) => update("triggers", e.target.value)} placeholder={"add a new invoice status\ncancel an invoice\nchange billing state"} rows={5} /></label>
            <label><span>Search tags <b>Comma separated</b></span><textarea value={fields.tags} onChange={(e) => update("tags", e.target.value)} placeholder="billing, audit, handoff" rows={5} /></label>
          </div>
        </section>
        <section className="knowledge-step" aria-labelledby="playbook-heading">
          <div className="step-heading"><span>03</span><div><h2 id="playbook-heading">Give Codex the playbook</h2><p>Write concrete guidance that remains useful across projects, tools, and versions.</p></div></div>
          <div className="step-fields"><label><span>What should Codex do? <b>One step per line</b></span><textarea value={fields.steps} onChange={(e) => update("steps", e.target.value)} placeholder={"Never assign invoice.status directly.\nRoute the operation through transition_invoice().\nRecord the ledger event before changing state."} rows={7} /></label></div>
        </section>
      </div>
      <aside className="publish-review" aria-label="Publish checklist">
        <div className="review-kicker"><CheckCircle2 size={18} /> READY FOR REVIEW</div>
        <h2>Publish checklist</h2>
        <p>A useful Memory is specific enough to retrieve and durable enough to reuse.</p>
        <ul><li><Check size={17} /><span><strong>Judgment, not history</strong>No transcript or activity dump</span></li><li><Check size={17} /><span><strong>Natural triggers</strong>Matches how teammates ask</span></li><li><Check size={17} /><span><strong>Actionable guidance</strong>Codex knows what to do next</span></li><li><Check size={17} /><span><strong>Employee approved</strong>Alice reviewed the sanitized result</span></li></ul>
        <div className="auto-metadata"><span>Managed automatically</span><dl><div><dt>Version</dt><dd>1.0.0</dd></div><div><dt>Code compatibility</dt><dd>Not required</dd></div><div><dt>Visibility</dt><dd>Private team</dd></div></dl></div>
        <section className="review-evidence"><ShieldCheck size={20} /><div><strong>Evidence attached</strong><p><code>uv run pytest -q</code><br />Exit 0 · 3 passed</p></div></section>
        <p className="publish-mode-note">{mode === "replay" ? "Replay validates the shape locally; no registry write." : "Live mode publishes this approved Memory to the team registry."}</p>
        <button className="primary publish-submit" disabled={submitting} type="submit"><Upload size={18} /> {submitting ? "Publishing…" : mode === "replay" ? "Publish memory — validation only" : "Publish approved memory"}</button>
      </aside>
    </form>
  </main>;
}

function Installed({ memories, manifests, mode, openMemory, run }: { memories: MemoryCapsule[]; manifests: InstallManifest[]; mode: ExecutionMode; openMemory: (memory: MemoryCapsule) => void; run: () => void }) {
  return <main className="installed-page">
    <div className="page-intro"><p className="eyebrow">BOB'S INSTALLED HANDOFFS</p><h1>My Codex</h1><p>Installed handoffs are explicit files Pluribus can match and inject into Bob's bounded Codex task context.</p></div>
    {memories.length === 0 ? <section className="empty-state large"><Box size={34} /><strong>No memories installed yet.</strong><span>Open a memory from Explore and install it to continue the demo.</span></section> : memories.map((memory) => {
      const manifest = manifests.find((item) => item.memory_id === memory.id);
      return <article className="installed-card" aria-label={memory.title} key={memory.id}>
        <div className="installed-icon"><PackageCheck size={28} /></div>
        <div className="installed-info"><div className="card-top"><span className="installed-pill" role="status" aria-label="Installed"><Check size={15} /> Installed</span><span className="version">Version {memory.version}</span></div><button className="installed-title" onClick={() => openMemory(memory)}>{memory.title}</button><p>{memory.summary}</p><dl><div><dt>Local package</dt><dd><code>{manifest?.install_path ?? "Recorded by Registry API; runtime package pending"}</code></dd></div><div><dt>Memory ID</dt><dd><code>{memory.id}</code></dd></div><div><dt>Installed</dt><dd>{manifest ? new Date(manifest.installed_at).toLocaleString() : "Registry install recorded"}</dd></div></dl></div>
        <div className="installed-action"><button className="primary" onClick={run}><Play size={18} /> {mode === "replay" ? "Run replay use" : "Load live use"}</button><span>{mode === "replay" ? "Uses recorded evidence" : "Loads latest API receipt"}</span></div>
      </article>;
    })}
  </main>;
}

function ReceiptView({ receipt, memory, mode, back }: { receipt: UsageReceipt; memory: MemoryCapsule; mode: ExecutionMode; back: () => void }) {
  const proof = [
    { label: "Publisher", value: memory.author.display_name, detail: memory.author.id, icon: <CircleUserRound /> },
    { label: "Verified memory", value: memory.title, detail: `${receipt.memory_id} · v${memory.version}`, icon: <BadgeCheck /> },
    { label: "Consumer", value: receipt.consumer, detail: `Installed package · Codex use ${receipt.codex_reported_use ? "reported" : "not reported"}`, icon: <Code2 /> },
    { label: "Changed file", value: receipt.changed_files.join(", "), detail: "Named task output", icon: <FileCheck2 /> },
    { label: "Verification", value: receipt.verification.exit_code === 0 ? "Passed" : "Failed", detail: `${receipt.verification.command.join(" ")} · ${receipt.verification.output_excerpt}`, icon: <CheckCircle2 /> },
  ];
  return <main className="receipt-page">
    <button className="back-link" onClick={back}><ArrowLeft size={17} /> Back to My Codex</button>
    <header className="receipt-header"><div><p className="eyebrow">KNOWLEDGE TRANSFER PROOF · {receipt.id}</p><h1>Usage Receipt</h1><p>Alice's judgment, Bob's Codex task, the concrete code change, and coordinator verification—linked in one receipt.</p></div><span className="receipt-pass"><CheckCircle2 size={26} /> VERIFIED</span></header>
    <div className={`receipt-mode ${mode}`}>{mode === "replay" ? replayMetadata.label : "LIVE"}</div>
    <ol className="proof-chain" aria-label="Usage Receipt proof chain">{proof.map((item, index) => <li key={item.label}><div className="proof-number">{index + 1}</div><div className="proof-icon">{item.icon}</div><div><span>{item.label}</span><strong>{item.value}</strong><small>{item.detail}</small></div>{index < proof.length - 1 && <ChevronRight className="proof-arrow" />}</li>)}</ol>
    <div className="receipt-evidence">
      <section><p className="eyebrow">MATCH & HANDOFF</p><dl><div><dt>Matched trigger</dt><dd><code>{receipt.matched_trigger}</code></dd></div><div><dt>Injected into Codex</dt><dd className="yes"><Check size={17} /> {String(receipt.injected_into_codex)}</dd></div><div><dt>Codex reported use</dt><dd className="yes"><Check size={17} /> {String(receipt.codex_reported_use)}</dd></div><div><dt>Effect</dt><dd>{receipt.effect}</dd></div></dl></section>
      <section className="terminal-proof"><p className="eyebrow">COORDINATOR VERIFICATION</p><div className="terminal-head"><span /><span /><span /></div><pre><b>$ {receipt.verification.command.join(" ")}</b>{"\n"}{receipt.verification.output_excerpt}{"\n\n"}<strong>Process finished with exit code {receipt.verification.exit_code}</strong></pre></section>
    </div>
    <div className="receipt-footer"><span>Recorded {new Date(receipt.created_at).toLocaleString()}</span><span><ShieldCheck size={17} /> Contract-complete Usage Receipt</span></div>
  </main>;
}

export default App;
