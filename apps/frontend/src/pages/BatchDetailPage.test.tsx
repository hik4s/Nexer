import {describe, it, expect, vi} from "vitest";
import {render, screen, waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {BatchDetailPage} from "./BatchDetailPage";
import {api, ExecutionBatch} from "../lib/api";
vi.mock("../lib/api", () => ({api: {getBatch: vi.fn(), cancelBatch: vi.fn(), cancelExecution: vi.fn()}}));
vi.mock("../hooks/useExecutionEvents", () => ({useExecutionEvents: () => ({events: [], connected: true})}));
describe("Batch progress", () => {
  it("cancels only the selected flow and preserves a successful peer", async () => {
    const batch = {id: 7, name: "Meu lote", status: "RUNNING", created_at: "", executions: [{id: 10, name: "Flow A", status: "RUNNING", cancel_requested: false, items: [{id: 1, stage: "DOWNLOADING", status: "RUNNING"}]}, {id: 11, name: "Flow B", status: "SUCCEEDED", cancel_requested: false, items: []}]} as ExecutionBatch;
    vi.mocked(api.getBatch).mockResolvedValue(batch);
    vi.mocked(api.cancelExecution).mockResolvedValue(batch.executions[0]);
    render(<MemoryRouter initialEntries={["/batches/7"]}><QueryClientProvider client={new QueryClient()}><Routes><Route path="/batches/:id" element={<BatchDetailPage />} /></Routes></QueryClientProvider></MemoryRouter>);
    expect(await screen.findByText("Flow A")).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Cancelar fluxo 11"})).toBeDisabled();
    await userEvent.click(screen.getByRole("button", {name: "Cancelar fluxo 10"}));
    await waitFor(() => expect(api.cancelExecution).toHaveBeenCalledWith(10));
    expect(api.cancelBatch).not.toHaveBeenCalled();
  });
});
