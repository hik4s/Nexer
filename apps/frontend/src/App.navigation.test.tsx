import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

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
    getDiagnostics: vi.fn().mockResolvedValue({
      status: "ok",
      database: { status: "ok" },
      workers: { online: 0, total: 0 },
    }),
  },
}));

function renderRoute(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RelatPy navigation", () => {
  it("shows the main sections", () => {
    renderRoute("/");

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Automações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Execuções" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Nova execução" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Diagnóstico" })).toBeInTheDocument();
  });

  it("renders the executions route", () => {
    renderRoute("/executions");

    expect(screen.getByRole("heading", { name: "Execuções" })).toBeInTheDocument();
  });
});
