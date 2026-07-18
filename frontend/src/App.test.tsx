import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

describe("Mission Control", () => {
  it("renders the launch surface", () => {
    render(<App />);
    expect(screen.getByText(/mission control/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Launch Hive" })).toBeInTheDocument();
  });

  it("opens an unmistakably labeled evidence replay", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Open recorded replay" }));
    expect(screen.getByText("REPLAY — RECORDED COORDINATOR EVIDENCE")).toBeInTheDocument();
    expect(screen.getByText("Agent roster")).toBeInTheDocument();
    expect(screen.getByText("Hive memory")).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
  });

  it("shows causal knowledge use separately from delivery", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Open recorded replay" }));
    await userEvent.click(screen.getByRole("button", { name: /share knowledge/i }));
    expect(screen.getByText("causal use recorded")).toBeInTheDocument();
    expect(screen.getAllByText(/Consumed ✓ builder_1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Delivered →/).length).toBeGreaterThan(0);
  });

  it("turns the replay into a three-step demo story", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Open recorded replay" }));

    expect(screen.getByRole("heading", { name: "4 Codex agents. One verified result." })).toBeInTheDocument();
    expect(screen.getByText("Parallel work, one coordinated outcome")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /share knowledge/i }));
    expect(screen.getByText("Knowledge became a code change")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /verify independently/i }));
    expect(screen.getByText("Coordinator verified the result itself")).toBeInTheDocument();
  });
});
