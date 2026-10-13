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
    getAutomationVersion: vi.fn(),
    getLoginProfileVersion: vi.fn(),
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
  it("requires a fresh summary after a programmatic checkbox choice", async () => {
    vi.clearAllMocks();
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 4, code: "CHECK", name: "Check", current_version: 1, status: "PUBLISHED", system: null, description: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockResolvedValue({id: 1, automation_id: 4, version: 1, recipe: {variables: {optional: {type: "boolean", required: false, field: {control: "checkbox"}}}}, published: true, published_at: null, created_at: "", created_by: null, test_status: "PASSED"});
    renderPage();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Nome da execução"), "Check");
    await user.selectOptions(screen.getByLabelText("Automação"), "4");
    await screen.findByRole("button", {name: "Definir optional como desmarcado"});
    await user.click(await screen.findByRole("button", {name: "Criar execução"}));
    expect(screen.getByRole("button", {name: "Confirmar e criar execução"})).toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "Definir optional como desmarcado"}));
    expect(screen.queryByRole("button", {name: "Confirmar e criar execução"})).toBeNull();
    expect(screen.getByRole("button", {name: "Criar execução"})).toBeInTheDocument();
    expect(api.createExecution).not.toHaveBeenCalled();
  });
  it.each([false, true])("creates an execution with recipe parameters: %s", async (parameterized) => {
    const variables = parameterized ? {
      base_url: {type: "string", required: true}, company: {type: "string", required: true},
      regional: {type: "string", required: true}, period_start: {type: "string", required: true},
      period_end: {type: "string", required: true}, enabled: {type: "boolean", required: true},
      choices: {type: "array", required: true},
      notes: {type: "string", required: true, allow_empty: true},
    } : {};
    vi.mocked(api.getAutomationVersion).mockResolvedValue({
      id: 1, automation_id: 4, version: 1, recipe: {variables}, created_at: "2026-10-10T00:00:00",
      created_by: "studio", test_status: "PASSED", published: true, published_at: "2026-10-10T00:00:00",
    });
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
    if (parameterized) {
      await user.type(await screen.findByLabelText("Endereço inicial"), "http://127.0.0.1:8765/report.html");
      await user.type(screen.getByLabelText("Empresa"), "Nova empresa");
      await user.type(screen.getByLabelText("Regional"), "south");
      await user.type(screen.getByLabelText("Período inicial"), "2032-01-02");
      await user.type(screen.getByLabelText("Período final"), "2032-01-31");
      await user.click(screen.getByLabelText("notes"));
      await user.selectOptions(screen.getByLabelText("enabled"), "false");
      await user.type(screen.getByLabelText("choices"), '[["new-option"]');
    }
    await user.click(screen.getByRole("button", { name: "Criar execução" }));
    await user.click(screen.getByRole("button", {name: "Confirmar e criar execução"}));

    await waitFor(() => {
      expect(api.createExecution).toHaveBeenCalled();
    });

    expect(vi.mocked(api.createExecution).mock.lastCall?.[0]).toEqual(
      expect.objectContaining({
        name: "Teste",
        automation_ids: [4],
        test_mode: true,
        inputs: parameterized ? {base_url: "http://127.0.0.1:8765/report.html", company: "Nova empresa", regional: "south", notes: "", enabled: false, choices: ["new-option"]} : {},
      }),
    );
    if (parameterized) {
      expect(vi.mocked(api.createExecution).mock.lastCall?.[0]).toEqual(expect.objectContaining({
        period_start: "2032-01-02T00:00:00", period_end: "2032-01-31T23:59:59",
      }));
    }
  });
  it("sends profile credentials outside inputs and leaves no secret in mutation cache", async () => {
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 4, code: "PRIVATE", name: "Privado", status: "PUBLISHED", current_version: 1, description: null, system: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockResolvedValue({id: 1, automation_id: 4, version: 1, recipe: {variables: {}, login_profile: {id: 2, version: 1}}, created_at: "", created_by: null, published: true, published_at: null, test_status: "PASSED"});
    vi.mocked(api.getLoginProfileVersion).mockResolvedValue({id: 2, name: "Meu site", status: "READY", current_version: 1, published: true, configuration: {login_url: "http://127.0.0.1/login", allowed_origins: ["http://127.0.0.1"], username_target: {selector: "#user", frames: []}, password_target: {selector: "#pass", frames: []}, submit_target: {selector: "#submit", frames: []}, success_rule: {kind: "url", url: "http://127.0.0.1/home"}}});
    let submitted = "";
    vi.mocked(api.createExecution).mockImplementation(async input => {
      submitted = JSON.stringify(input);
      return {id: 10, name: "Private", requested_by: null, period_start: null, period_end: null, status: "QUEUED", send_to_network: false, keep_local_copy: true, overwrite_existing: false, test_mode: false, inputs: {}, created_at: "", started_at: null, finished_at: null, cancel_requested: false, items: []};
    });
    render(<MemoryRouter><QueryClientProvider client={client}><NewExecutionPage /></QueryClientProvider></MemoryRouter>);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Nome da execução"), "Private");
    await user.selectOptions(await screen.findByLabelText("Automação"), "4");
    await user.click(screen.getByLabelText("Modo de teste"));
    await user.type(await screen.findByLabelText("Usuário — Meu site"), "user-canary");
    await user.type(screen.getByLabelText("Senha — Meu site"), "password-canary");
    await user.click(screen.getByRole("button", {name: "Criar execução"}));
    expect(screen.getByRole("heading", {name: "Resumo antes de iniciar"})).toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "Confirmar e criar execução"}));
    await waitFor(() => expect(JSON.parse(submitted).profile_credentials).toEqual({"profile-2-v1": {username: "user-canary", password: "password-canary"}}));
    expect(JSON.parse(submitted).inputs).toEqual({});
    expect(JSON.stringify(client.getMutationCache().getAll().map(mutation => mutation.state))).not.toContain("password-canary");
    expect(JSON.stringify(client.getQueryCache().getAll().map(query => query.state.data))).not.toContain("password-canary");
  });

});
