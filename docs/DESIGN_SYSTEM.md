# Pluribus Design System

> Version 1.0 · Enterprise evidence interfaces · Source branch: `feat/pluribus-design-system`

The Pluribus design system turns the Mission Control visual language into reusable rules and CSS primitives. It is designed for operator consoles, verification surfaces, agent orchestration tools, and evidence-heavy product interfaces.

It borrows three useful ideas from Adyen's enterprise presentation—high-contrast dark stages, one unmistakable green signal, and disciplined square geometry—while keeping Pluribus's own identity and information model.

## 1. Design principles

### Evidence before decoration

Every visible element must explain state, provenance, causality, or operator action. Decorative statistics, generic illustrations, gradients, glassmorphism, and ornamental icons are not part of the system.

### One signal color

Signal green identifies positive state, live/recorded system markers, selected evidence, causal flow, and the primary action. It must not become a general background decoration.

### Dark stage, light workspace

Use the dark inverse surface for orientation, mission context, terminal output, and high-level status. Use white and paper surfaces for dense reading and comparison.

### Square, mechanical geometry

Corners are square by default. Hierarchy comes from contrast, spacing, borders, and typography—not large radius cards or soft shadows. The only standard elevation is the solid green offset shadow used on a singular hero action surface.

### Human claim vs coordinator proof

Agent claims and coordinator-observed evidence must remain visually distinct. Success green is reserved for verified state, never for unverified optimism.

## 2. Installation

Import the complete system once before product-specific composition styles:

```css
@import "./design-system/index.css";
```

The current Mission Control does this from `frontend/src/styles.css`.

Files:

```text
frontend/src/design-system/
├── index.css       # public CSS entry point
├── tokens.css      # color, type, spacing, geometry, motion
├── foundation.css  # reset, focus, selection, reduced motion
└── primitives.css  # reusable UI classes
```

## 3. Color system

### Brand palette

| Token | Value | Role |
|---|---:|---|
| `--ds-color-ink-950` | `#07110f` | Primary dark stage, terminal, inverse button |
| `--ds-color-ink-900` | `#101c19` | Softer mission header surface |
| `--ds-color-ink-700` | `#293934` | Borders on dark surfaces |
| `--ds-color-ink-500` | `#61706a` | Secondary text |
| `--ds-color-paper-100` | `#edf0eb` | App canvas |
| `--ds-color-paper-50` | `#f7f8f4` | Warm light surface |
| `--ds-color-white` | `#ffffff` | Dense content panels |
| `--ds-color-signal-500` | `#00df79` | Primary signal green |
| `--ds-color-signal-600` | `#00b865` | Strong green border/icon |
| `--ds-color-signal-50` | `#d9ffeb` | Verified-state tint |
| `--ds-color-warning-500` | `#c88300` | Degraded/non-blocking warning |
| `--ds-color-danger-500` | `#d33c45` | Failed or destructive state |

Use semantic aliases such as `--ds-color-bg-canvas`, `--ds-color-text-primary`, `--ds-color-border`, and `--ds-color-accent` in application code. Raw palette tokens are for system maintenance and rare visual tuning.

### Contrast rules

- White text on `ink-950` for primary inverse content.
- `ink-950` text on signal green for actions and verified result blocks.
- Secondary text must use `ink-500` or darker on white/paper.
- Do not place signal green text on white for body copy; use `signal-600` only for compact identifiers.
- Danger and warning colors communicate state only. They are never category decoration.

## 4. Typography

### Families

- **Sans:** `--ds-font-sans` for interface, headings, actions, and narrative.
- **Mono:** `--ds-font-mono` for IDs, commands, evidence paths, durations, labels, and machine state.

The system uses local-first stacks and does not depend on a network font request.

### Hierarchy

| Level | Token | Use |
|---|---|---|
| Hero | `--ds-font-size-hero` | Launch statement only |
| Mission display | `--ds-font-size-9` | Mission objective and major page title |
| Section heading | `--ds-font-size-7` | Panel titles |
| Body | `--ds-font-size-5` | Narrative copy |
| Compact UI | `--ds-font-size-3` / `4` | Cards and controls |
| Machine label | `--ds-font-size-1` / `2` | Uppercase mono metadata |

Large headings use tight leading and negative tracking. Body copy uses `--ds-line-body`. Mono labels use uppercase and wide tracking, but sentences and paths remain sentence case.

## 5. Spacing and layout

Spacing follows a 4px base scale:

```text
1=4px · 2=8px · 3=12px · 4=16px · 5=20px · 6=24px
8=32px · 10=40px · 12=48px · 16=64px · 20=80px · 24=96px
```

Rules:

- Use 12–20px gaps inside dense evidence components.
- Use 32–56px between major sections.
- Use `--ds-content-max: 1380px` for centered presentation surfaces.
- Dense desktop workspaces may use three columns; collapse to two below 1180px and one below 860px.
- Progress rails may scroll horizontally on narrow screens. Never compress labels until they overlap.

## 6. Geometry and elevation

- Default radius: `--ds-radius-none`.
- Optional precision radius: `--ds-radius-xs` (2px), only for controls that require a small rendering allowance.
- Default border: one pixel.
- Strong divider: two pixels.
- Standard hero elevation: `--ds-shadow-signal`.
- No blurred card shadows, glass blur, gradient surfaces, or floating pill clusters.

## 7. Reusable primitives

### Labels and display type

```html
<p class="ds-label">Coordinator proof</p>
<h1 class="ds-display">All required checks passed</h1>
<p class="ds-body">Agent claims are excluded from this result.</p>
```

### Buttons

```html
<button class="ds-button ds-button--primary">Launch mission</button>
<button class="ds-button ds-button--secondary">Open replay</button>
<button class="ds-button ds-button--inverse">Stop mission</button>
```

Use one primary action per region. Secondary actions should not compete with the signal block.

### Panels

```html
<section class="ds-panel">...</section>
<section class="ds-panel ds-panel--inverse">...</section>
```

Panels use borders and surface contrast, not generic card shadows.

### Status

```html
<span class="ds-status ds-status--success">Completed</span>
<span class="ds-status ds-status--warning">Degraded</span>
<span class="ds-status ds-status--danger">Failed</span>
```

Use `.ds-badge` for high-level state markers and `.ds-status` for compact row-level state.

### Terminal and machine output

```html
<pre class="ds-terminal"><code>npm test
3 passed</code></pre>
```

Terminal output remains dark even in a light workspace, preserving the distinction between evidence output and explanatory UI.

### Layout helpers

```html
<div class="ds-frame">...</div>
<div class="ds-cluster">...</div>
<div class="ds-stack">...</div>
```

These helpers cover framing and simple flow. Product-specific grids remain in the product stylesheet.

## 8. Component anatomy

### Mission result

1. Machine label: `MISSION RESULT`
2. Dominant state: `VERIFIED`, `FAILED`, or `PARTIALLY VERIFIED`
3. Coordinator evidence summary: exit code and protected-path result

Only a coordinator-observed verified result receives a full signal-green block.

### Agent row

1. Role icon in a square signal block
2. Human-readable role and compact machine ID
3. Assigned task and detail
4. Branch/worktree provenance
5. Duration and status

Role colors do not vary. Differentiation comes from icon and text, keeping green reserved as the system signal.

### Evidence patch

1. Patch ID and evidence status
2. Human summary
3. Author and type
4. Source/evidence locator
5. Delivery and causal-consumption labels
6. Optional expanded effect and changed files

Delivery and causal consumption must be separate visual statements.

### Verification panel

1. Coordinator-observed result
2. Executable, arguments, duration, and working directory
3. Raw output in terminal treatment
4. Protected-path proof

Never summarize away the raw output when evidence review is the purpose of the screen.

## 9. Responsive behavior

### Desktop · above 1180px

- Full three-column Mission Control.
- Mission objective and result block share a header row.
- All evidence remains visible without horizontal page scrolling.

### Compact desktop/tablet · 861–1180px

- Agent and Hive panels share the first row.
- Evidence spans the full second row.

### Mobile · 320–860px

- Single-column panel stack.
- Mission result follows the objective.
- Stage rail scrolls horizontally with 148px fixed stages.
- Product name remains visible.
- Optional connection detail may hide, but the replay/live identity and exit action remain available.
- Raw terminal output may scroll inside its own container; the page itself must not overflow horizontally.

## 10. Motion

Motion is functional and short:

- Fast state transitions: `--ds-duration-fast` (120ms).
- Normal transitions: `--ds-duration-normal` (180ms).
- Standard easing: `--ds-ease-standard`.
- Primary button hover may move upward by 2px.
- Avoid ambient floating, looping glow, parallax, and unrelated entrance animation.
- `prefers-reduced-motion` is respected by the foundation layer.

## 11. Accessibility

- Keyboard focus uses a 3px signal-green outline with 2px offset.
- Never communicate state by color alone; pair color with icon and text.
- Keep buttons at least 46px high for primary interactions.
- Use real buttons for tabs and patch selection.
- Preserve `aria-labelledby`, tab roles, and alert roles in product components.
- Avoid hiding the product/page identity at mobile widths.
- Target zero browser console errors and zero horizontal document overflow.

## 12. Do / don't

### Do

- Use one accent color consistently.
- Let typography and solid contrast carry hierarchy.
- Show source paths, commands, timestamps, and exit status in mono.
- Keep raw proof near the summarized result.
- Use warm paper and white surfaces for long-form evidence.
- Test desktop and 390px mobile rendering.

### Don't

- Add gradients, neon glow, glassmorphism, or decorative noise.
- Use large rounded cards or pill-shaped containers as the default.
- Assign a rainbow color to each agent role.
- Present agent claims as verified evidence.
- Shrink dense data until labels become unreadable.
- invent decorative metrics or icons.
- Copy Adyen logos, copy, imagery, or brand assets.

## 13. Release checklist

Before reusing the system in another Pluribus surface:

```text
[ ] Import design-system/index.css before product styles
[ ] Use semantic tokens instead of raw hex values
[ ] Use one primary signal action per region
[ ] Keep coordinator evidence visually distinct from agent claims
[ ] Verify keyboard focus and reduced motion
[ ] Test at 1440px and 390px
[ ] Confirm horizontal document overflow is false
[ ] Confirm console errors and runtime exceptions are zero
[ ] Run tests, typecheck, production build, and npm audit
```
