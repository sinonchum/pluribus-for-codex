import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

const MEMORY_TITLE = "Fix duplicate pytest module collisions";
const REPLAY_LABEL = "REPLAY — RECORDED EVIDENCE";

function renderMarketplace() {
  const user = userEvent.setup();
  render(<App />);
  return user;
}

function expectReplayEvidenceLabel() {
  expect(screen.getAllByText(REPLAY_LABEL).length).toBeGreaterThan(0);
}

describe("Codex memory marketplace", () => {
  it("finds the fixed verified memory when a developer searches Explore for pytest", async () => {
    const user = renderMarketplace();

    await user.type(screen.getByRole("searchbox", { name: /search memories/i }), "pytest");

    const result = await screen.findByRole("article", { name: MEMORY_TITLE });
    expect(within(result).getByText(MEMORY_TITLE)).toBeInTheDocument();
    expect(within(result).getByText(/verified/i)).toBeInTheDocument();
    expect(within(result).getByText(/Alice Chen/i)).toBeInTheDocument();
    expect(within(result).getByText(/1\.0\.0/)).toBeInTheDocument();
  });

  it("opens memory detail with the problem, reusable steps, and verification evidence", async () => {
    const user = renderMarketplace();

    await user.click(screen.getByRole("button", { name: new RegExp(MEMORY_TITLE, "i") }));

    expect(screen.getByRole("heading", { name: MEMORY_TITLE })).toBeInTheDocument();
    expect(screen.getByText("Pytest raises import file mismatch during collection.")).toBeInTheDocument();
    expect(
      screen.getByText("Confirm the collision is caused by duplicate test module basenames."),
    ).toBeInTheDocument();
    expect(screen.getByText("Set pytest addopts to --import-mode=importlib.")).toBeInTheDocument();
    expect(screen.getByText(/pytest -q/)).toBeInTheDocument();
    expect(screen.getByText(/4 passed/)).toBeInTheDocument();
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
    expect(within(installedMemory).getByText(/installed/i)).toBeInTheDocument();
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
    expect(steps[2]).toHaveTextContent(/consumer.*dev_bob/i);
    expect(steps[3]).toHaveTextContent(/changed file.*pyproject\.toml/i);
    expect(steps[4]).toHaveTextContent(/pytest -q.*4 passed/i);
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
