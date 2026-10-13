import {afterEach, describe, expect, it, vi} from "vitest";
import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {MemoryRouter} from "react-router-dom";
import {ExecutionsPage} from "./ExecutionsPage";
import {api} from "../lib/api";

vi.mock("../lib/api", () => ({api: {
  listExecutions: vi.fn(), listBatches: vi.fn(), deleteExecution: vi.fn(), deleteBatch: vi.fn(),
}}));
afterEach(() => vi.restoreAllMocks());

const execution = (id: number, status: string, batch_id: number | null = null) => ({
  id, name: `Execução ${id}`, status, batch_id, items: [{id}], created_at: "2026-10-13",
});

function mount() {
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}><ExecutionsPage /></QueryClientProvider></MemoryRouter>);
}

describe("Histórico gerenciável", () => {
  it("only deletes finished individual execution after explicit confirmation", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    let records = [execution(1, "SUCCEEDED"), execution(2, "RUNNING"), execution(3, "FAILED", 5)];
    vi.mocked(api.listExecutions).mockImplementation(async () => ({items: records, total: records.length, limit: 50, offset: 0} as Awaited<ReturnType<typeof api.listExecutions>>));
    vi.mocked(api.deleteExecution).mockImplementation(async id => {records = records.filter(record => record.id !== id);});
    mount();
    const button = await screen.findByRole("button", {name: "Excluir execução"});
    expect(screen.getAllByRole("button", {name: "Excluir execução"})).toHaveLength(1);
    await user.click(button);
    expect(api.deleteExecution).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    await user.click(button);
    expect(api.deleteExecution).toHaveBeenCalledWith(1);
    expect(await screen.findByRole("status")).toHaveTextContent("Arquivos preservados");
  });

  it("only deletes finished batches and refreshes their list", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.listExecutions).mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});
    let records = [{id: 7, name: "Lote finalizado", status: "SUCCEEDED", executions: [execution(1, "SUCCEEDED")]},
                   {id: 8, name: "Lote ativo", status: "RUNNING", executions: [execution(2, "RUNNING")]}];
    vi.mocked(api.listBatches).mockImplementation(async () => ({items: records, total: records.length} as Awaited<ReturnType<typeof api.listBatches>>));
    vi.mocked(api.deleteBatch).mockImplementation(async id => {records = records.filter(record => record.id !== id);});
    mount();
    await user.click(screen.getByRole("button", {name: "Lotes"}));
    const button = await screen.findByRole("button", {name: "Excluir lote"});
    expect(screen.getAllByRole("button", {name: "Excluir lote"})).toHaveLength(1);
    await user.click(button);
    expect(api.deleteBatch).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("status")).toHaveTextContent("Lote e históricos excluídos");
  });
});
