import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { AuthProvider } from "./auth";
import { App } from "./App";
import { api } from "./lib/api";

vi.mock("./lib/api", () => ({
  api: {
    getHealth: vi.fn(),
    getAuthSession: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter><AuthProvider><App /></AuthProvider></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Nexer authentication and dashboard", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.mocked(api.getAuthSession).mockResolvedValue({ authenticated: false, username: null });
    vi.mocked(api.login).mockResolvedValue({ authenticated: true, username: "operador" });
    vi.mocked(api.logout).mockResolvedValue({ authenticated: false, username: null });
  });

  it("redirects unauthenticated users to login", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "Entrar no Nexer" })).toBeInTheDocument();
  });

  it("allows a user to enter the protected dashboard", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({ status: "ok" });
    renderApp();
    await screen.findByLabelText("Código de pareamento");
    await import("@testing-library/user-event").then(async ({ default: userEvent }) => {
      const user = userEvent.setup();
      await user.type(screen.getByLabelText("Código de pareamento"), "synthetic-pairing-code");
      await user.click(screen.getByRole("button", { name: "Entrar" }));
    });
    expect(await screen.findByText("Nexer Dashboard")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Ambiente saudável")).toBeInTheDocument());
    expect(screen.getByText("API operacional")).toBeInTheDocument();
  });

  it("keeps the session visible when backend logout fails", async () => {
    vi.mocked(api.getAuthSession).mockResolvedValue({ authenticated: true, username: "operador" });
    vi.mocked(api.getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(api.logout).mockRejectedValue(new Error("API unavailable"));
    renderApp();
    expect(await screen.findByText("Nexer Dashboard")).toBeInTheDocument();
    const { default: userEvent } = await import("@testing-library/user-event");
    await userEvent.setup().click(screen.getByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível encerrar a sessão no backend");
    expect(screen.getByText("Nexer Dashboard")).toBeInTheDocument();
  });

  it("shows an error state when the API is unavailable", async () => {
    vi.mocked(api.getAuthSession).mockResolvedValue({ authenticated: true, username: "operador" });
    vi.mocked(api.getHealth).mockRejectedValue(new Error("API unavailable"));
    renderApp();
    await waitFor(() => expect(screen.getByText("Não foi possível verificar a API")).toBeInTheDocument());
  });
});
