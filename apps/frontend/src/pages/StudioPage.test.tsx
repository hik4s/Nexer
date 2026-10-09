import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { StudioPage } from "./StudioPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    listAutomations: vi.fn(),
    createAutomation: vi.fn(),
    createAutomationVersion: vi.fn(),
    testAutomationVersion: vi.fn(),
    publishAutomationVersion: vi.fn(),
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <StudioPage />
    </QueryClientProvider>,
  );
}

describe("StudioPage", () => {
  it("creates an automation and publishes a valid recipe version", async () => {
    vi.mocked(api.listAutomations).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    vi.mocked(api.createAutomation).mockResolvedValue({
      id: 7,
      code: "RELATORIO",
      name: "Relatório",
      description: null,
      system: null,
      status: "DRAFT",
      current_version: null,
    });
    vi.mocked(api.createAutomationVersion).mockResolvedValue({
      id: 11,
      automation_id: 7,
      version: 1,
      recipe: {},
      created_at: "2026-10-08T00:00:00",
      created_by: "studio",
      test_status: null,
      published: false,
      published_at: null,
    });
    vi.mocked(api.testAutomationVersion).mockResolvedValue({
      version: 1,
      test_status: "PASSED",
      automation_status: "DRAFT",
    });
    vi.mocked(api.publishAutomationVersion).mockResolvedValue({
      version: 1,
      published: true,
      automation_status: "PUBLISHED",
    });

    renderPage();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Código"), "RELATORIO");
    await user.type(screen.getByLabelText("Nome"), "Relatório");
    await user.click(screen.getByRole("button", { name: "Criar automação" }));

    await waitFor(() => {
      expect(api.createAutomation).toHaveBeenCalledWith({
        code: "RELATORIO",
        name: "Relatório",
        description: undefined,
        system: undefined,
      });
    });

    await user.click(screen.getByRole("button", { name: "Salvar versão" }));

    await waitFor(() => {
      expect(api.createAutomationVersion).toHaveBeenCalled();
    });

    await user.click(screen.getByRole("button", { name: "Testar versão" }));
    await waitFor(() => {
      expect(api.testAutomationVersion).toHaveBeenCalledWith(7, 1);
    });

    await user.click(screen.getByRole("button", { name: "Publicar versão" }));
    await waitFor(() => {
      expect(api.publishAutomationVersion).toHaveBeenCalledWith(7, 1);
    });

    expect(screen.getByText("Versão publicada.")).toBeInTheDocument();
  });
});
