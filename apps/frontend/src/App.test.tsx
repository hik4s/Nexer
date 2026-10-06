import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";
import { api } from "./lib/api";

vi.mock("./lib/api", () => ({
  api: {
    getHealth: vi.fn(),
  },
}));

function renderApp() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RelatPy Dashboard", () => {
  it("shows the healthy API status", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({ status: "ok" });

    renderApp();

    expect(screen.getByText("RelatPy Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Verificando ambiente…")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Ambiente saudável")).toBeInTheDocument();
    });

    expect(screen.getByText("API operacional")).toBeInTheDocument();
  });

  it("shows an error state when the API is unavailable", async () => {
    vi.mocked(api.getHealth).mockRejectedValue(
      new Error("API unavailable"),
    );

    renderApp();

    await waitFor(() => {
      expect(screen.getByText("Não foi possível verificar a API")).toBeInTheDocument();
    });
  });
});
