import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({api: {listRoutines: vi.fn(async () => ({items: []})), deleteRoutine: vi.fn(), deleteAutomation: vi.fn(), getHealth: vi.fn(), listAutomations: vi.fn(), getAutomationVersion: vi.fn(), createExecution: vi.fn(), getReportOptions: vi.fn()}}));

describe("Registered reports", () => {
  it("confirms flow removal and archives a referenced flow without losing selection state", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.getHealth).mockResolvedValue({status: "ok"});
    let items = [{id: 4, code: "REPORT", name: "Relatório registrado", status: "PUBLISHED", current_version: 1, description: null, system: null}];
    vi.mocked(api.listAutomations).mockImplementation(async () => ({items, total: items.length, limit: 50, offset: 0}));
    vi.mocked(api.deleteAutomation).mockImplementation(async () => {items = []; return {archived: true};});
    render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}><Dashboard /></QueryClientProvider></MemoryRouter>);
    await user.click(await screen.findByRole("button", {name: "Excluir fluxo"}));
    expect(confirm).toHaveBeenCalled();
    expect(api.deleteAutomation).toHaveBeenCalledWith(4);
    expect(await screen.findByRole("status")).toHaveTextContent("Fluxo arquivado");
    expect(screen.queryByRole("button", {name: "Excluir fluxo"})).not.toBeInTheDocument();
    confirm.mockRestore();
  });
  it("filters flows while preserving the batch selection", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({status: "ok"});
    vi.mocked(api.listAutomations).mockResolvedValue({items: ["Financeiro", "Pessoal"].map((name, index) => ({id: index + 1, code: name.toUpperCase(), name, status: "PUBLISHED", current_version: 1, description: null, system: null})), total: 2, limit: 50, offset: 0});
    render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider></MemoryRouter>);
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText("Selecionar Financeiro para lote"));
    await user.type(screen.getByLabelText("Buscar fluxos"), "pessoal");
    expect(screen.queryByRole("button", {name: "Preparar Financeiro"})).toBeNull();
    expect(screen.getByRole("button", {name: "Preparar Pessoal"})).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Preparar lote/})).toHaveAttribute("href", "/batches/new?flows=1");
    await user.click(screen.getByRole("button", {name: "Limpar busca"}));
    expect(screen.getByLabelText("Selecionar Financeiro para lote")).toBeChecked();
  });
  it("opens a report form inside the dashboard with its published field rules", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({status: "ok"});
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 4, code: "REPORT", name: "Relatório registrado", status: "PUBLISHED", current_version: 1, description: null, system: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockResolvedValue({id: 1, automation_id: 4, version: 1, created_at: "", created_by: null, published: true, published_at: null, test_status: "PASSED",
      recipe: {variables: {company: {type: "string", required: true, field: {control: "text", max_length: 20}}, quantity: {type: "string", required: true, field: {control: "number", min: 1, max: 100, step: 0.5}}}}});
    render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}><Dashboard /></QueryClientProvider></MemoryRouter>);
    expect(await screen.findByRole("heading", {name: "Fluxos registrados"})).toBeInTheDocument();
    await userEvent.setup().click(await screen.findByRole("button", {name: "Preparar Relatório registrado"}));
    expect(await screen.findByLabelText("Empresa")).toHaveAttribute("maxlength", "20");
    expect(screen.getByLabelText("quantity")).toHaveAttribute("type", "number");
    expect(screen.getByLabelText("quantity")).toHaveAttribute("step", "0.5");
    expect(screen.getByLabelText("quantity")).toHaveValue(null);
  });
  it("loads current choices without selecting recorded values and refreshes dependent lists", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getHealth).mockResolvedValue({status: "ok"});
    vi.mocked(api.listAutomations).mockResolvedValue({items: [{id: 4, code: "REPORT", name: "Relatório registrado", status: "PUBLISHED", current_version: 1, description: null, system: null}], total: 1, limit: 50, offset: 0});
    vi.mocked(api.getAutomationVersion).mockResolvedValue({id: 1, automation_id: 4, version: 1, created_at: "", created_by: null, published: true, published_at: null, test_status: "PASSED",
      recipe: {variables: {base_url: {type: "string"}, company: {type: "string", field: {control: "select"}}, regional: {type: "string", field: {control: "select"}}}}});
    vi.mocked(api.getReportOptions).mockResolvedValue({fields: {
      company: {options: [{value: "new-company", label: "Empresa atual", disabled: false}], error: null},
      regional: {options: [{value: "south", label: "Sul", disabled: false}], error: null},
    }});
    render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}><Dashboard /></QueryClientProvider></MemoryRouter>);
    await user.click(await screen.findByRole("button", {name: "Preparar Relatório registrado"}));
    await user.type(await screen.findByLabelText("Endereço inicial"), "http://127.0.0.1:8000/form");
    expect(screen.getByLabelText("Empresa")).toBeDisabled();
    await user.click(screen.getByRole("button", {name: "Carregar opções do site"}));
    expect(await screen.findByRole("option", {name: "Empresa atual"})).toBeInTheDocument();
    expect(screen.getByLabelText("Empresa")).toHaveValue("");
    await user.selectOptions(screen.getByLabelText("Empresa"), "new-company");
    expect(screen.getByLabelText("Regional")).toBeDisabled();
    expect(screen.getByRole("button", {name: "Criar execução"})).toBeDisabled();
    await user.click(screen.getByRole("button", {name: "Carregar opções do site"}));
    expect(api.getReportOptions).toHaveBeenLastCalledWith(4, 1, {base_url: "http://127.0.0.1:8000/form", company: "new-company"});
    await screen.findByRole("option", {name: "Sul"});
    await user.selectOptions(screen.getByLabelText("Regional"), "south");
    expect(screen.getByRole("button", {name: "Criar execução"})).toBeEnabled();
  });
});
