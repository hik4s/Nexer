import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuthProvider } from "./auth";
import { App } from "./App";

vi.mock("./lib/api", () => ({
  api: {
    listRoutines: vi.fn(async () => ({items: []})),
    getAuthSession: vi.fn().mockResolvedValue({ authenticated: true, username: "operador" }),
    login: vi.fn(),
    logout: vi.fn(),
    getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
    listAutomations: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    listExecutions: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    listBatches: vi.fn().mockResolvedValue({ items: [], total: 0 }),
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
    expect(await screen.findByRole("link", { name: "Meus fluxos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Execuções" })).toBeInTheDocument();
    expect(screen.getByText("Ferramentas e ajustes")).toBeInTheDocument();
  });

  it("renders the executions route", async () => {
    renderRoute("/executions");
    expect(await screen.findByRole("heading", { name: "Execuções", level: 1 })).toBeInTheDocument();
  });
});
