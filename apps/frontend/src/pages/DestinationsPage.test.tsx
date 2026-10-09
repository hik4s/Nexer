import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DestinationsPage } from "./DestinationsPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    listDestinations: vi.fn(),
    createDestination: vi.fn(),
    updateDestination: vi.fn(),
    deleteDestination: vi.fn(),
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <DestinationsPage />
    </QueryClientProvider>,
  );
}

describe("DestinationsPage", () => {
  it("lists destinations", async () => {
    vi.mocked(api.listDestinations).mockResolvedValue({
      items: [{
        id: 1,
        code: "LOCAL",
        name: "Saída local",
        path_reference: "C:/Nexer/outputs",
        enabled: true,
        last_test_status: null,
        last_test_at: null,
      }],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("LOCAL")).toBeInTheDocument();
    });

    expect(screen.getByText("Saída local")).toBeInTheDocument();
    expect(screen.getByText("C:/Nexer/outputs")).toBeInTheDocument();
  });

  it("edits and deletes a destination", async () => {
    const destination = {
      id: 3,
      code: "NETWORK",
      name: "Rede",
      path_reference: "\\\\server\\reports",
      enabled: true,
      last_test_status: null,
      last_test_at: null,
    };

    vi.mocked(api.listDestinations).mockResolvedValue({
      items: [destination],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.mocked(api.updateDestination).mockResolvedValue({
      ...destination,
      name: "Rede atualizada",
      enabled: false,
    });
    vi.mocked(api.deleteDestination).mockResolvedValue(undefined);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("NETWORK")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByRole("heading", { name: "Editar destino" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("NETWORK")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Nome"));
    await user.type(screen.getByLabelText("Nome"), "Rede atualizada");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Atualizar destino" }));

    await waitFor(() => {
      expect(api.updateDestination).toHaveBeenCalledWith(3, {
        code: "NETWORK",
        name: "Rede atualizada",
        path_reference: "\\\\server\\reports",
        enabled: false,
      });
    });

    vi.spyOn(window, "confirm").mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Excluir" }));

    await waitFor(() => {
      expect(api.deleteDestination).toHaveBeenCalledWith(3);
    });
  });

  it("creates a destination", async () => {
    const networkPath = String.raw`\\server\reports`;

    vi.mocked(api.listDestinations).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    vi.mocked(api.createDestination).mockResolvedValue({
      id: 2,
      code: "NETWORK",
      name: "Rede",
      path_reference: networkPath,
      enabled: true,
      last_test_status: null,
      last_test_at: null,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Novo destino" })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Código"), "NETWORK");
    await user.type(screen.getByLabelText("Nome"), "Rede");
    await user.type(
      screen.getByLabelText("Referência do caminho"),
      networkPath,
    );
    await user.click(screen.getByRole("button", { name: "Salvar destino" }));

    await waitFor(() => {
      expect(api.createDestination).toHaveBeenCalledWith({
        code: "NETWORK",
        name: "Rede",
        path_reference: networkPath,
        enabled: true,
      });
    });
  });
});
