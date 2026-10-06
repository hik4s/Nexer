import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { NewExecutionPage } from "./NewExecutionPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    listAutomations: vi.fn(),
    createExecution: vi.fn(),
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <NewExecutionPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("NewExecutionPage", () => {
  it("creates an execution from a published automation", async () => {
    vi.mocked(api.listAutomations).mockResolvedValue({
      items: [{
        id: 4,
        code: "PILOTO",
        name: "Piloto",
        description: null,
        system: null,
        status: "PUBLISHED",
        current_version: 1,
      }],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.mocked(api.createExecution).mockResolvedValue({
      id: 10,
      name: "Teste",
      requested_by: null,
      period_start: null,
      period_end: null,
      status: "QUEUED",
      send_to_network: false,
      keep_local_copy: true,
      overwrite_existing: false,
      test_mode: true,
      inputs: {},
      created_at: new Date().toISOString(),
      started_at: null,
      finished_at: null,
      cancel_requested: false,
      items: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("PILOTO — Piloto")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Nome da execução"), "Teste");
    await user.selectOptions(screen.getByLabelText("Automação"), "4");
    await user.click(screen.getByRole("button", { name: "Criar execução" }));

    await waitFor(() => {
      expect(api.createExecution).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Teste",
          automation_ids: [4],
          test_mode: true,
          inputs: {},
        }),
      );
    });
  });
});
