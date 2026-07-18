import { cpSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";

const demoDir = fileURLToPath(new URL(".", import.meta.url));
const root = resolve(demoDir, "..");
const seed = join(demoDir, "seed-health-api");
const target = mkdtempSync(join(tmpdir(), "pluribus-health-api-"));
const modeIndex = process.argv.indexOf("--mode");
const mode = modeIndex >= 0 ? process.argv[modeIndex + 1] : "replay";
if (!new Set(["live", "replay"]).has(mode)) throw new Error("--mode must be live or replay");

cpSync(seed, target, { recursive: true });
const git = (...args) => {
  const result = spawnSync("git", args, { cwd: target, stdio: "inherit" });
  if (result.status !== 0) throw new Error(`git ${args[0]} failed`);
};
git("init", "--initial-branch=main");
git("config", "user.name", "Pluribus Demo");
git("config", "user.email", "demo@localhost");
git("add", "--all");
git("commit", "-m", "chore: establish demo baseline");
const baseline = spawnSync("git", ["rev-parse", "HEAD"], { cwd: target, encoding: "utf8" }).stdout.trim();
const codexCheck = spawnSync("codex", ["--version"], { encoding: "utf8" });
const codexPreflight = codexCheck.status === 0 ? `READY · ${codexCheck.stdout.trim()}` : "UNAVAILABLE";
console.log(`
Demo repository: ${target}`);
console.log(`Mode: ${mode.toUpperCase()}${mode === "replay" ? " (recorded evidence, visibly labeled)" : ""}
`);

const npmCli = process.platform === "win32"
  ? join(resolve(process.execPath, ".."), "node_modules", "npm", "bin", "npm-cli.js")
  : null;
const command = npmCli && existsSync(npmCli) ? process.execPath : "npm";
const args = [
  ...(npmCli ? [npmCli] : []),
  "--prefix", join(root, "frontend"), "run", "dev", "--", "--host", "127.0.0.1"
];
const child = spawn(command, args, {
  cwd: root,
  stdio: "inherit",
  env: {
    ...process.env,
    VITE_DEMO_MODE: mode,
    VITE_DEMO_REPOSITORY: target,
    VITE_DEMO_BASELINE: baseline,
    VITE_CODEX_PREFLIGHT: codexPreflight
  }
});
child.on("exit", code => process.exit(code ?? 0));
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => child.kill(signal));
