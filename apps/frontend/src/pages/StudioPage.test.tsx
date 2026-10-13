import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { StudioPage } from "./StudioPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    listAutomations: vi.fn(),
    listLoginProfiles: vi.fn(),
    getAutomationVersion: vi.fn(),
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
  beforeEach(() => {vi.resetAllMocks(); vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});});
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

    await user.click(screen.getByRole("button", { name: "Validar receita" }));
    await waitFor(() => {
      expect(api.testAutomationVersion).toHaveBeenCalledWith(7, 1);
    });

    await user.click(screen.getByRole("button", { name: "Publicar versão" }));
    await waitFor(() => {
      expect(api.publishAutomationVersion).toHaveBeenCalledWith(7, 1);
    });

    expect(screen.getByText("Versão publicada.")).toBeInTheDocument();
  });
  it("loads the selected published recipe and stops publishing once the editor changes", async () => {
    const recipe = {schema_version: 1, name: "Receita existente", variables: {}, steps: [{id: "open", action: "navigate", url: "http://127.0.0.1/report"}], output: {type: "file"}};
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 9, code: "SAVED", name: "Salvo", status: "PUBLISHED", current_version: 2, description: null, system: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockResolvedValue({id: 3, automation_id: 9, version: 2, recipe, published: true, created_at: "", created_by: null, published_at: null, test_status: "PASSED"});
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name: /SAVED/}));
    await waitFor(() => expect(screen.getByLabelText("JSON da receita")).toHaveValue(JSON.stringify(recipe, null, 2)));
    expect(api.getAutomationVersion).toHaveBeenCalledWith(9, 2);
    await user.type(screen.getByLabelText("JSON da receita"), " ");
    expect(screen.getByRole("button", {name: "Validar receita"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "Publicar versão"})).toBeDisabled();
  });

  it("imports a recording and edits display names without changing placeholders or saving filled values", async () => {
    const recipe = {schema_version: 1, name: "Gravação", variables: {input_001: {type: "string", required: true, field: {control: "email", max_length: 80}}}, steps: [{id: "fill", action: "fill", selector: "input", value: "{{input_001}}"}], output: {type: "file"}};
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 9, code: "SAVED", name: "Salvo", status: "DRAFT", current_version: null, description: null, system: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.createAutomationVersion).mockResolvedValue({id: 1, automation_id: 9, version: 1, recipe: {}, published: false, created_at: "", created_by: null, published_at: null, test_status: null});
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name: /SAVED/}));
    await user.upload(screen.getByLabelText("Importar gravação JSON"), new File([JSON.stringify(recipe)], "recording.json", {type: "application/json"}));
    const label = await screen.findByLabelText("Nome no formulário: input_001");
    await user.clear(label); await user.type(label, "Email do responsável");
    await user.click(screen.getByRole("button", {name: "Salvar versão"}));
    await waitFor(() => expect(api.createAutomationVersion).toHaveBeenCalledWith(9, {...recipe, variables: {input_001: {...recipe.variables.input_001, label: "Email do responsável"}}}));
    const saved = vi.mocked(api.createAutomationVersion).mock.calls[0][1];
    expect(JSON.stringify(saved)).not.toContain('"default"');
    expect(JSON.stringify(saved)).toContain("{{input_001}}");
  });

  it("keeps the current recipe when an imported file is invalid", async () => {
    vi.mocked(api.listAutomations).mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});
    renderPage();
    const user = userEvent.setup();
    const original = (screen.getByLabelText("JSON da receita") as HTMLTextAreaElement).value;
    await user.upload(screen.getByLabelText("Importar gravação JSON"), new File(["private-canary"], "broken.json", {type: "application/json"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível importar");
    expect(screen.getByRole("alert")).not.toHaveTextContent("private-canary");
    expect(screen.getByLabelText("JSON da receita")).toHaveValue(original);
  });
  it("does not replace a newer selection with a delayed recipe response", async () => {
    let resolveFirst!: (value: Awaited<ReturnType<typeof api.getAutomationVersion>>) => void;
    const first = new Promise<Awaited<ReturnType<typeof api.getAutomationVersion>>>(resolve => {resolveFirst = resolve;});
    const stored = (id: number) => ({id, automation_id: id, version: 1, recipe: {name: "Recipe " + id, variables: {}}, published: true, created_at: "", created_by: null, published_at: null, test_status: "PASSED"});
    vi.mocked(api.listAutomations).mockResolvedValue({items: [1, 2].map(id => ({id, code: "R" + id, name: "Flow " + id, status: "PUBLISHED", current_version: 1, description: null, system: null})), total: 2, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockImplementation(id => id === 1 ? first : Promise.resolve(stored(2)));
    renderPage(); const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name: /R1/}));
    await user.click(screen.getByRole("button", {name: /R2/}));
    await waitFor(() => expect(screen.getByLabelText("JSON da receita")).toHaveValue(JSON.stringify(stored(2).recipe, null, 2)));
    resolveFirst(stored(1));
    await waitFor(() => expect(screen.getByLabelText("JSON da receita")).toHaveValue(JSON.stringify(stored(2).recipe, null, 2)));
  });

});
