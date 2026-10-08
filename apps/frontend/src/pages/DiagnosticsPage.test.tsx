import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DiagnosticsPage } from "./DiagnosticsPage";

import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    getDiagnostics: vi.fn(),
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <DiagnosticsPage />
    </QueryClientProvider>,
  );
}

describe("DiagnosticsPage", () => {
  it("shows authentication configuration diagnostics", async () => {
    vi.mocked(api.getDiagnostics).mockResolvedValue({
      status: "ok",
      database: { status: "ok" },
      workers: { online: 1, total: 2 },
      authentication: { configured: 3, renewal_configured: 1 },
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "3 receitas configuradas" })).toBeInTheDocument();
    });

    expect(screen.getByText("3 receitas configuradas")).toBeInTheDocument();
    expect(screen.getByText("1 com renovação")).toBeInTheDocument();
  });
});
