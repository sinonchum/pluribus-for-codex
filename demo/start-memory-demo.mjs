#!/usr/bin/env node

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HOST = "127.0.0.1";
const DEFAULT_PORT = 5173;
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const REPLAY_LABEL = "REPLAY — RECORDED EVIDENCE";

function usage() {
  return `Usage:
  node demo/start-memory-demo.mjs --mode replay [--port 5173]
  node demo/start-memory-demo.mjs --mode live [--api-base http://127.0.0.1:8000] [--port 5173]

Options:
  --mode live|replay  Required. Replay is deterministic and uses no backend.
  --api-base URL      Live API base (or VITE_API_BASE_URL; default ${DEFAULT_API_BASE}).
  --port PORT         Frontend Vite port (default ${DEFAULT_PORT}).
  --help              Show this help.
`;
}

function fail(message) {
  console.error(`Error: ${message}\n\n${usage()}`);
  process.exit(2);
}

function parseArgs(argv) {
  const options = {};

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }

    const equalsIndex = argument.indexOf("=");
    const name = equalsIndex === -1 ? argument : argument.slice(0, equalsIndex);
    if (!["--mode", "--api-base", "--port"].includes(name)) {
      fail(`unknown argument ${argument}`);
    }

    const value = equalsIndex === -1 ? argv[++index] : argument.slice(equalsIndex + 1);
    if (!value || value.startsWith("--")) {
      fail(`${name} requires a value`);
    }
    if (options[name] !== undefined) {
      fail(`${name} may only be provided once`);
    }
    options[name] = value;
  }

  return options;
}

function validateApiBase(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    fail(`--api-base must be an absolute http(s) URL; received ${value}`);
  }
  if (!new Set(["http:", "https:"]).has(url.protocol)) {
    fail(`--api-base must use http or https; received ${value}`);
  }
  return value.replace(/\/$/, "");
}

const options = parseArgs(process.argv.slice(2));
if (options.help) {
  console.log(usage());
  process.exit(0);
}

const mode = options["--mode"];
if (!mode) {
  fail("--mode is required; choose live or replay explicitly");
}
if (!new Set(["live", "replay"]).has(mode)) {
  fail(`--mode must be live or replay; received ${mode}`);
}
if (mode === "replay" && options["--api-base"]) {
  fail("--api-base is only valid with --mode live; Replay never contacts a backend");
}

const portText = options["--port"] ?? String(DEFAULT_PORT);
const port = Number(portText);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  fail(`--port must be an integer from 1 to 65535; received ${portText}`);
}

const apiBase = mode === "live"
  ? validateApiBase(options["--api-base"] ?? process.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE)
  : undefined;
const demoDir = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(demoDir, "..");
const frontendDir = join(rootDir, "frontend");
const packageJson = join(frontendDir, "package.json");
if (!existsSync(packageJson)) {
  fail(`frontend package not found at ${packageJson}`);
}
const viteCli = join(frontendDir, "node_modules", "vite", "bin", "vite.js");
if (!existsSync(viteCli)) {
  fail("Vite is not installed; run npm --prefix frontend ci first");
}

const childArgs = [
  viteCli,
  "--host",
  HOST,
  "--port",
  String(port),
  "--strictPort",
];
const childEnv = {
  ...process.env,
  VITE_DEMO_MODE: mode,
};
if (apiBase) {
  childEnv.VITE_API_BASE_URL = apiBase;
} else {
  delete childEnv.VITE_API_BASE_URL;
}

console.log("Pluribus Memory Registry demo");
console.log(`Mode: ${mode === "replay" ? REPLAY_LABEL : "LIVE"}`);
console.log(`Frontend: http://${HOST}:${port}`);
if (mode === "replay") {
  console.log("Backend: not used (deterministic recorded evidence)");
} else {
  console.log(`API base: ${apiBase}`);
  console.log("Live errors remain live errors; this launcher never falls back to Replay.");
}

const child = spawn(process.execPath, childArgs, {
  cwd: frontendDir,
  env: childEnv,
  stdio: "inherit",
  shell: false,
});

let shuttingDown = false;
let childExited = false;
function forwardSignal(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  child.kill(signal);
  const forceExit = setTimeout(() => {
    if (!childExited) child.kill("SIGKILL");
  }, 5000);
  forceExit.unref();
}

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => forwardSignal(signal));
}

child.on("error", (error) => {
  console.error(`Failed to start the frontend: ${error.message}`);
  process.exitCode = 1;
});
child.on("exit", (code, signal) => {
  childExited = true;
  if (signal && !shuttingDown) {
    console.error(`Frontend exited from ${signal}.`);
  }
  process.exitCode = code ?? (signal ? 1 : 0);
});
