import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AutomationsPage } from "./AutomationsPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    listAutomations: vi.fn(),
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <AutomationsPage />
    </QueryClientProvider>,
  );
}

describe("AutomationsPage", () => {
  it("shows automation list and status", async () => {
    vi.mocked(api.listAutomations).mockResolvedValue({
      items: [
        {
          id: 1,
          code: "RECLAMACOES",
          name: "Reclamações",
          description: null,
          system: "SGIND",
          status: "PUBLISHED",
          current_version: 2,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderPage();

    expect(screen.getByText("Automações")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("RECLAMACOES")).toBeInTheDocument();
    });

    expect(screen.getByText("Publicada")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("shows empty state", async () => {
    vi.mocked(api.listAutomations).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Nenhuma automação cadastrada")).toBeInTheDocument();
    });
  });
});
