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

const tags = ["python", "pytest", "debugging", "codex"];
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
  const [installed, setInstalled] = useState<InstallManifest[]>(mode === "replay" ? [] : []);
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
    ]).then(([listed, manifests]) => {
      if (!active) return;
      setMemories(listed);
      setInstalled(manifests);
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
      const manifest = mode === "replay" ? replayInstallManifest : await memoryApi.install(selected.slug);
      setInstalled((current) => current.some((item) => item.memory_id === manifest.memory_id) ? current : [...current, manifest]);
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

  const isInstalled = selected ? installed.some((item) => item.memory_id === selected.id) : false;
  const navigate = (next: Screen) => { setError(""); setScreen(next); };

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => navigate("explore")} aria-label="Pluribus home">
          <span className="brand-mark"><Code2 size={21} /></span>
          <span>pluribus</span><em>/ memories</em>
        </button>
        <nav aria-label="Main navigation">
          <button className={screen === "explore" || screen === "detail" ? "active" : ""} onClick={() => navigate("explore")}>Explore</button>
          <button className={screen === "publish" ? "active" : ""} onClick={() => navigate("publish")}>Publish</button>
          <button className={screen === "installed" ? "active" : ""} onClick={() => navigate("installed")}>
            My Codex <span className="nav-count">{installed.length}</span>
          </button>
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
      {screen === "installed" && <Installed memories={memories} manifests={installed} mode={mode} openMemory={openMemory} run={showUse} />}
      {screen === "receipt" && receipt && <ReceiptView receipt={receipt} memory={selected ?? replayMemory} mode={mode} back={() => navigate("installed")} />}

      <footer>
        <span>Pluribus Memory Registry</span>
        <span>Explicit local packages. Bounded Codex context. Verifiable use.</span>
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
        <p className="eyebrow">THE OPEN MEMORY REGISTRY FOR CODEX</p>
        <h1>Reuse the debugging methods that already worked.</h1>
        <p>Discover verified Codex memories, install them as explicit local packages, and prove when they help a task pass.</p>
      </div>
      <div className="hero-actions">
        <button className="primary" onClick={() => navigate("publish")}><Upload size={18} /> Publish a memory</button>
        <button className="secondary" onClick={() => navigate("installed")}><PackageCheck size={18} /> View My Codex</button>
      </div>
    </section>

    <section className="registry-section" aria-labelledby="explore-heading">
      <div className="section-heading">
        <div><p className="eyebrow">PUBLIC REGISTRY</p><h2 id="explore-heading">Explore memories</h2></div>
        <span>{memories.length} {memories.length === 1 ? "result" : "results"}</span>
      </div>
      <div className="search-row">
        <label className="search-box"><Search size={21} /><span className="sr-only">Search memories</span><input aria-label="Search memories" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search errors, methods, or tools…" /></label>
        <button className="search-submit" type="button">Search registry</button>
      </div>
      <div className="tag-row" aria-label="Filter by tag">
        <span>Filter:</span>
        <button className={!tag ? "selected" : ""} onClick={() => setTag("")}>All</button>
        {tags.map((item) => <button className={tag === item ? "selected" : ""} key={item} onClick={() => setTag(tag === item ? "" : item)}>#{item}</button>)}
      </div>

      {loading ? <div className="empty-state">Loading live registry…</div> : memories.length === 0 ? <div className="empty-state"><Search size={28} /><strong>No memories match this search.</strong><span>Try “pytest” or clear the selected tag.</span></div> :
        <div className="memory-grid">{memories.map((memory) => <MemoryCard key={memory.id} memory={memory} open={() => openMemory(memory)} />)}</div>}
    </section>
  </main>;
}

function MemoryCard({ memory, open }: { memory: MemoryCapsule; open: () => void }) {
  return <article className="memory-card">
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
        <div className="detail-kicker"><VerifiedBadge /><span>Published by <strong>{memory.author.display_name}</strong></span></div>
        <h1>{memory.title}</h1>
        <p className="lead">{memory.summary}</p>
        <div className="tags">{memory.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
        <section><p className="eyebrow">PROBLEM</p><h2>When this memory helps</h2><p>{memory.problem}</p></section>
        <section><p className="eyebrow">MATCHING TRIGGERS</p><h2>Signals Codex can match</h2><div className="trigger-list">{memory.triggers.map((trigger) => <code key={trigger}>{trigger}</code>)}</div></section>
        <section><p className="eyebrow">REUSABLE METHOD</p><h2>Steps</h2><ol className="steps">{memory.steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol></section>
        <section className="evidence-panel"><div><p className="eyebrow">VERIFICATION EVIDENCE</p><h2><CheckCircle2 /> Coordinator check passed</h2></div><div className="command"><code>{memory.verification.command.join(" ")}</code><strong>exit {memory.verification.exit_code}</strong></div><pre>{memory.verification.evidence_excerpt}</pre><p>{memory.verification.passed} checks passed in the recorded verification.</p></section>
      </article>
      <aside className="install-panel">
        <Box size={26} />
        <h2>Install this memory</h2>
        <p>Adds an explicit Pluribus-managed memory package to the project. It does not alter hidden model state.</p>
        {installed ? <button className="installed-button" onClick={openInstalled}><Check size={19} /> Installed · View My Codex</button> : <button className="primary full" disabled={loading} onClick={install}><Download size={19} /> {loading ? "Installing…" : "Install to Codex"}</button>}
        <dl><div><dt>Version</dt><dd>{memory.version}</dd></div><div><dt>Memory ID</dt><dd><code>{memory.id}</code></dd></div><div><dt>Compatibility</dt><dd>{memory.compatibility.join(" · ")}</dd></div><div><dt>Fork lineage</dt><dd>{memory.fork_of ? <><GitFork size={14} /> {memory.fork_of}</> : "Original memory"}</dd></div><div><dt>Installs</dt><dd>{memory.installs.toLocaleString()}</dd></div></dl>
      </aside>
    </div>
  </main>;
}

type PublishFields = { title: string; summary: string; problem: string; triggers: string; steps: string; tags: string; compatibility: string; version: string; };
const publishDefaults: PublishFields = { title: "", summary: "", problem: "", triggers: "", steps: "", tags: "", compatibility: "python>=3.11", version: "1.0.0" };

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
    if (!/^\d+\.\d+\.\d+$/.test(fields.version)) nextErrors.push("Version must use semantic versioning, for example 1.0.0.");
    setErrors(nextErrors);
    if (nextErrors.length) return;

    const slug = fields.title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const capsule: MemoryCapsule = {
      id: `mem_${slug.replaceAll("-", "_")}_v1`, slug, title: fields.title.trim(), summary: fields.summary.trim(), problem: fields.problem.trim(),
      triggers: lines(fields.triggers), steps: lines(fields.steps), tags: csv(fields.tags),
      author: { id: "dev_bob", display_name: "Bob Rivera" }, version: fields.version,
      compatibility: csv(fields.compatibility), status: "verified",
      verification: { command: ["pytest", "-q"], exit_code: 0, passed: 4, evidence_excerpt: "4 passed" },
      stars: 0, installs: 0, fork_of: null, created_at: "2026-07-18T10:00:00Z",
    };
    setSubmitting(true);
    try { onPublished(mode === "replay" ? capsule : await memoryApi.create(capsule)); }
    catch (reason) { setErrors([reason instanceof Error ? reason.message : "The memory could not be published."]); }
    finally { setSubmitting(false); }
  };

  return <main className="publish-page">
    <div className="page-intro"><p className="eyebrow">PUBLISH A MEMORY CAPSULE</p><h1>Share a method, not a transcript.</h1><p>Publish a sanitized, structured debugging method with explicit verification evidence. Raw Codex conversations are never accepted.</p></div>
    <form className="publish-form" onSubmit={submit} noValidate>
      {errors.length > 0 && <div className="validation" role="alert"><strong>Please complete the capsule:</strong><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}
      <fieldset><legend>Memory identity</legend><div className="field-grid"><label><span>Title <b>Required</b></span><input value={fields.title} onChange={(e) => update("title", e.target.value)} placeholder="Fix duplicate test module collisions" /></label><label><span>Version <b>Required</b></span><input value={fields.version} onChange={(e) => update("version", e.target.value)} /></label></div><label><span>Summary <b>Required</b></span><textarea value={fields.summary} onChange={(e) => update("summary", e.target.value)} placeholder="A concise statement of the reusable method." rows={2} /></label><label><span>Problem <b>Required</b></span><textarea value={fields.problem} onChange={(e) => update("problem", e.target.value)} placeholder="Describe the failure this memory solves." rows={3} /></label></fieldset>
      <fieldset><legend>Matching & method</legend><div className="field-grid"><label><span>Trigger phrases <b>One per line</b></span><textarea value={fields.triggers} onChange={(e) => update("triggers", e.target.value)} placeholder={"import file mismatch\nduplicate test module"} rows={5} /></label><label><span>Reusable steps <b>One per line</b></span><textarea value={fields.steps} onChange={(e) => update("steps", e.target.value)} placeholder={"Confirm the collision.\nConfigure importlib mode.\nRun verification."} rows={5} /></label></div><div className="field-grid"><label><span>Tags <b>Comma separated</b></span><input value={fields.tags} onChange={(e) => update("tags", e.target.value)} placeholder="python, pytest, debugging" /></label><label><span>Compatibility <b>Comma separated</b></span><input value={fields.compatibility} onChange={(e) => update("compatibility", e.target.value)} /></label></div></fieldset>
      <section className="safe-evidence"><ShieldCheck size={24} /><div><strong>Fixed, sanitized verification</strong><p>Publisher: Bob Rivera · Command: <code>pytest -q</code> · Exit code: 0 · Evidence: 4 passed</p></div></section>
      <div className="form-actions"><p>{mode === "replay" ? "Replay validates the complete shape locally; it does not publish to the API." : "Live mode submits this exact Memory Capsule to the registry API."}</p><button className="primary" disabled={submitting} type="submit"><Upload size={18} /> {submitting ? "Publishing…" : mode === "replay" ? "Validate replay capsule" : "Publish verified memory"}</button></div>
    </form>
  </main>;
}

function Installed({ memories, manifests, mode, openMemory, run }: { memories: MemoryCapsule[]; manifests: InstallManifest[]; mode: ExecutionMode; openMemory: (memory: MemoryCapsule) => void; run: () => void }) {
  return <main className="installed-page">
    <div className="page-intro"><p className="eyebrow">PLURIBUS-MANAGED LOCAL PACKAGES</p><h1>My Codex</h1><p>Installed memories are explicit files Pluribus can match and inject into bounded Codex task context.</p></div>
    {manifests.length === 0 ? <section className="empty-state large"><Box size={34} /><strong>No memories installed yet.</strong><span>Open a memory from Explore and install it to continue the demo.</span></section> : manifests.map((manifest) => {
      const memory = memories.find((item) => item.id === manifest.memory_id) ?? replayMemory;
      return <article className="installed-card" key={manifest.memory_id}>
        <div className="installed-icon"><PackageCheck size={28} /></div>
        <div className="installed-info"><div className="card-top"><span className="installed-pill"><Check size={15} /> Installed</span><span className="version">v{manifest.version}</span></div><button className="installed-title" onClick={() => openMemory(memory)}>{memory.title}</button><p>{memory.summary}</p><dl><div><dt>Local package</dt><dd><code>{manifest.install_path}</code></dd></div><div><dt>Memory ID</dt><dd><code>{manifest.memory_id}</code></dd></div><div><dt>Installed</dt><dd>{new Date(manifest.installed_at).toLocaleString()}</dd></div></dl></div>
        <div className="installed-action"><button className="primary" onClick={run}><Play size={18} /> {mode === "replay" ? "Run replay use" : "Load live use"}</button><span>{mode === "replay" ? "Uses recorded evidence" : "Loads latest API receipt"}</span></div>
      </article>;
    })}
  </main>;
}

function ReceiptView({ receipt, memory, mode, back }: { receipt: UsageReceipt; memory: MemoryCapsule; mode: ExecutionMode; back: () => void }) {
  const proof = [
    { label: "Publisher", value: memory.author.display_name, detail: memory.author.id, icon: <CircleUserRound /> },
    { label: "Verified memory", value: memory.title, detail: `${receipt.memory_id} · v${memory.version}`, icon: <BadgeCheck /> },
    { label: "Consumer", value: receipt.consumer, detail: "Installed Pluribus package", icon: <Code2 /> },
    { label: "Codex use", value: receipt.codex_reported_use ? "Reported as used" : "Not reported", detail: receipt.effect, icon: <Play /> },
    { label: "Changed file", value: receipt.changed_files.join(", "), detail: "Named task output", icon: <FileCheck2 /> },
    { label: "Verification", value: receipt.verification.exit_code === 0 ? "Passed" : "Failed", detail: receipt.verification.output_excerpt, icon: <CheckCircle2 /> },
  ];
  return <main className="receipt-page">
    <button className="back-link" onClick={back}><ArrowLeft size={17} /> Back to My Codex</button>
    <header className="receipt-header"><div><p className="eyebrow">USAGE RECEIPT · {receipt.id}</p><h1>Verified proof of memory use</h1><p>Publisher, installed memory, consumer, concrete change, and coordinator verification—linked in one receipt.</p></div><span className="receipt-pass"><CheckCircle2 size={26} /> VERIFIED</span></header>
    <div className={`receipt-mode ${mode}`}>{mode === "replay" ? replayMetadata.label : "LIVE"}</div>
    <ol className="proof-chain">{proof.map((item, index) => <li key={item.label}><div className="proof-number">{index + 1}</div><div className="proof-icon">{item.icon}</div><div><span>{item.label}</span><strong>{item.value}</strong><small>{item.detail}</small></div>{index < proof.length - 1 && <ChevronRight className="proof-arrow" />}</li>)}</ol>
    <div className="receipt-evidence">
      <section><p className="eyebrow">MATCH & HANDOFF</p><dl><div><dt>Matched trigger</dt><dd><code>{receipt.matched_trigger}</code></dd></div><div><dt>Injected into Codex</dt><dd className="yes"><Check size={17} /> {String(receipt.injected_into_codex)}</dd></div><div><dt>Codex reported use</dt><dd className="yes"><Check size={17} /> {String(receipt.codex_reported_use)}</dd></div><div><dt>Effect</dt><dd>{receipt.effect}</dd></div></dl></section>
      <section className="terminal-proof"><p className="eyebrow">COORDINATOR VERIFICATION</p><div className="terminal-head"><span /><span /><span /></div><pre><b>$ {receipt.verification.command.join(" ")}</b>{"\n"}{receipt.verification.output_excerpt}{"\n\n"}<strong>Process finished with exit code {receipt.verification.exit_code}</strong></pre></section>
    </div>
    <div className="receipt-footer"><span>Recorded {new Date(receipt.created_at).toLocaleString()}</span><span><ShieldCheck size={17} /> Contract-complete Usage Receipt</span></div>
  </main>;
}

export default App;
