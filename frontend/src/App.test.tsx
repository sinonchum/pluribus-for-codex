import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

const MEMORY_TITLE = "Preserve billing audit trail during invoice transitions";
const REPLAY_LABEL = "REPLAY — RECORDED EVIDENCE";

function renderMarketplace() {
  const user = userEvent.setup();
  render(<App />);
  return user;
}

function expectReplayEvidenceLabel() {
  expect(screen.getAllByText(REPLAY_LABEL).length).toBeGreaterThan(0);
}

describe("Codex knowledge handoff marketplace", () => {
  it("makes the engineer-departure handoff story explicit", () => {
    renderMarketplace();
    expect(screen.getByText(/your best engineer leaves/i)).toBeInTheDocument();
    expect(screen.getByText(/their judgment doesn't have to/i)).toBeInTheDocument();
    expect(screen.getByText(/Alice Chen · Billing, 4 years/i)).toBeInTheDocument();
  });

  it("finds Alice's verified handoff when Bob searches Explore for billing", async () => {
    const user = renderMarketplace();

    await user.type(screen.getByRole("searchbox", { name: /search memories/i }), "billing");

    const result = await screen.findByRole("article", { name: MEMORY_TITLE });
    expect(within(result).getByText(MEMORY_TITLE)).toBeInTheDocument();
    expect(within(result).getByText(/verified/i)).toBeInTheDocument();
    expect(within(result).getByText("Alice Chen · Billing, 4 years")).toBeInTheDocument();
    expect(within(result).getByText(/1\.0\.0/)).toBeInTheDocument();
  });

  it("opens memory detail with the problem, reusable steps, and verification evidence", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("button", { name: new RegExp(MEMORY_TITLE, "i") }));

    expect(screen.getByRole("heading", { name: MEMORY_TITLE })).toBeInTheDocument();
    expect(screen.getByText(/direct invoice status assignments bypass/i)).toBeInTheDocument();
    expect(
      screen.getByText("Never assign invoice.status directly in Billing Service workflows."),
    ).toBeInTheDocument();
    expect(screen.getByText(/route the operation through transition_invoice/i)).toBeInTheDocument();
    expect(screen.getAllByText(/uv run pytest -q/)).toHaveLength(2);
    expect(screen.getByText(/3 passed/)).toBeInTheDocument();
  });

  it("changes Install to Codex to an installed state", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("button", { name: new RegExp(MEMORY_TITLE, "i") }));
    await user.click(screen.getByRole("button", { name: "Install to Codex" }));

    expect(screen.queryByRole("button", { name: "Install to Codex" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /installed/i })).toBeDisabled();
  });

  it("shows the installed memory and version in My Codex", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("button", { name: new RegExp(MEMORY_TITLE, "i") }));
    await user.click(screen.getByRole("button", { name: "Install to Codex" }));
    await user.click(screen.getByRole("link", { name: "My Codex" }));

    expect(screen.getByRole("heading", { name: "My Codex" })).toBeInTheDocument();
    const installedMemory = screen.getByRole("article", { name: MEMORY_TITLE });
    expect(within(installedMemory).getByText(MEMORY_TITLE)).toBeInTheDocument();
    expect(within(installedMemory).getByText(/version 1\.0\.0/i)).toBeInTheDocument();
    expect(within(installedMemory).getByRole("status", { name: "Installed" })).toBeInTheDocument();
  });

  it("renders the complete publisher-to-verification Usage Receipt chain", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("link", { name: "Usage Receipt" }));

    expect(screen.getByRole("heading", { name: "Usage Receipt" })).toBeInTheDocument();
    const chain = screen.getByRole("list", { name: /usage receipt proof chain/i });
    const steps = within(chain).getAllByRole("listitem");
    expect(steps).toHaveLength(5);
    expect(steps[0]).toHaveTextContent(/publisher.*Alice Chen/i);
    expect(steps[1]).toHaveTextContent(new RegExp(`memory.*${MEMORY_TITLE}`, "i"));
    expect(steps[2]).toHaveTextContent(/consumer.*Bob.*Successor Engineer/i);
    expect(steps[3]).toHaveTextContent(/changed file.*billing\/invoices\.py/i);
    expect(steps[4]).toHaveTextContent(/uv run pytest -q.*3 passed/i);
  });

  it("keeps the exact recorded-evidence label visible throughout Replay", async () => {
    const user = renderMarketplace();

    expectReplayEvidenceLabel();
    await user.click(screen.getByRole("button", { name: new RegExp(MEMORY_TITLE, "i") }));
    expectReplayEvidenceLabel();
    await user.click(screen.getByRole("link", { name: "My Codex" }));
    expectReplayEvidenceLabel();
    await user.click(screen.getByRole("link", { name: "Usage Receipt" }));
    expectReplayEvidenceLabel();
  });

  it("rejects an incomplete Memory Capsule and offers no transcript upload", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("link", { name: "Publish" }));
    expect(screen.queryByLabelText(/transcript/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /upload transcript/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /publish memory/i }));

    expect(screen.getByRole("heading", { name: /publish memory/i })).toBeInTheDocument();
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    expect(screen.queryByText(/published successfully/i)).not.toBeInTheDocument();
  });

  it("makes every critical marketplace destination directly navigable", () => {
    renderMarketplace();

    const navigation = screen.getByRole("navigation", { name: /primary/i });
    expect(within(navigation).getByRole("link", { name: "Explore" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "Publish" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "My Codex" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "Usage Receipt" })).toBeInTheDocument();
  });
});
