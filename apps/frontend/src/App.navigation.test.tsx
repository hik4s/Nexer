import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

vi.mock("./lib/api", () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
    listAutomations: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    }),
    listExecutions: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    }),
  },
}));

describe("RelatPy navigation", () => {
  it("shows the main sections", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Automações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Execuções" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Nova execução" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Diagnóstico" })).toBeInTheDocument();
  });

  it("renders the executions route", () => {
    render(
      <MemoryRouter initialEntries={["/executions"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Execuções" })).toBeInTheDocument();
  });
});
