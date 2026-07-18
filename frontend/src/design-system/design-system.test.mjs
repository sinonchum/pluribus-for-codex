import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const cssSource = name => readFileSync(resolve(process.cwd(), "src", "design-system", name), "utf8");
const foundation = cssSource("foundation.css");
const primitives = cssSource("primitives.css");
const tokens = cssSource("tokens.css");

const requiredTokens = [
  "--ds-color-bg-canvas",
  "--ds-color-bg-surface",
  "--ds-color-bg-inverse",
  "--ds-color-text-primary",
  "--ds-color-text-inverse",
  "--ds-color-accent",
  "--ds-color-success",
  "--ds-color-warning",
  "--ds-color-danger",
  "--ds-font-sans",
  "--ds-font-mono",
  "--ds-space-4",
  "--ds-focus-ring",
  "--ds-content-max",
];

const requiredPrimitives = [
  ".ds-label",
  ".ds-display",
  ".ds-body",
  ".ds-panel",
  ".ds-button",
  ".ds-button--primary",
  ".ds-button--secondary",
  ".ds-badge",
  ".ds-status--success",
  ".ds-terminal",
  ".ds-frame",
];

describe("Pluribus design system contract", () => {
  it("defines the required semantic tokens", () => {
    for (const token of requiredTokens) expect(tokens).toContain(`${token}:`);
  });

  it("exports the documented primitive classes", () => {
    for (const className of requiredPrimitives) expect(primitives).toContain(className);
  });

  it("does not reference undefined design-system tokens", () => {
    const allCss = `${tokens}\n${foundation}\n${primitives}`;
    const definitions = new Set([...tokens.matchAll(/(--ds-[\w-]+)\s*:/g)].map(match => match[1]));
    const references = new Set([...allCss.matchAll(/var\((--ds-[\w-]+)/g)].map(match => match[1]));
    expect([...references].filter(reference => !definitions.has(reference))).toEqual([]);
  });
});
