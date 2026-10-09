import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuthProvider } from "./auth";
import { App } from "./App";

vi.mock("./lib/api", () => ({
  api: {
    getAuthSession: vi.fn().mockResolvedValue({ authenticated: true, username: "operador" }),
    login: vi.fn(),
    logout: vi.fn(),
    getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
    listAutomations: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    listExecutions: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    getDiagnostics: vi.fn().mockResolvedValue({ status: "ok", database: { status: "ok" }, workers: { online: 0, total: 0 } }),
  },
}));

function renderRoute(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Nexer navigation", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("shows the main sections", async () => {
    renderRoute("/");
    expect(await screen.findByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Automações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Execuções" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Nova execução" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Diagnóstico" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Destinos" })).toBeInTheDocument();
  });

  it("renders the executions route", async () => {
    renderRoute("/executions");
    expect(await screen.findByRole("heading", { name: "Execuções", level: 1 })).toBeInTheDocument();
  });
});
