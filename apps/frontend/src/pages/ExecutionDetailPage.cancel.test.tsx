import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ExecutionDetailPage } from "./ExecutionDetailPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: {
    getExecution: vi.fn(),
    cancelExecution: vi.fn(),
  },
  executionEventsUrl: vi.fn(() => "http://example.test/events"),
}));

vi.mock("../hooks/useExecutionEvents", () => ({
  useExecutionEvents: vi.fn(() => ({
    events: [],
    connected: true,
  })),
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/executions/7"]}>
        <Routes>
          <Route path="/executions/:id" element={<ExecutionDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const queued = {
  id: 7,
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
};

describe("ExecutionDetailPage cancellation", () => {
  it('explains an empty query without echoing site content', async()=>{
    vi.mocked(api.getExecution).mockResolvedValue({...queued,status:'FAILED',items:[
      {id:1,automation_id:11,automation_version:1,status:'FAILED',stage:'FAILED',error_detail:'QUERY_NO_DATA'},
      {id:2,automation_id:12,automation_version:1,status:'FAILED',stage:'FAILED',error_detail:'QUERY_SITE_ERROR'},
    ]} as Awaited<ReturnType<typeof api.getExecution>>);
    renderPage();
    await waitFor(()=>expect(screen.getByText('Consulta concluída sem dados; etapas seguintes não executadas.')).toBeInTheDocument());
    expect(screen.getByText(/site informou um erro/)).toBeInTheDocument();
  });
  it("shows safe download guidance without echoing unknown failure details", async () => {
    vi.mocked(api.getExecution).mockResolvedValue({...queued,status:'FAILED',items:[
      {id:1,automation_id:11,automation_version:1,status:'FAILED',stage:'FAILED',error_detail:'DOWNLOAD_MATCH_AMBIGUOUS'},
      {id:2,automation_id:12,automation_version:1,status:'FAILED',stage:'FAILED',error_detail:'private-canary'},
    ]} as Awaited<ReturnType<typeof api.getExecution>>);
    renderPage();
    await waitFor(()=>expect(screen.getByText('A central contém mais de um resultado para esta solicitação.')).toBeInTheDocument());
    expect(screen.getByText('A automação falhou. Revise o fluxo e tente novamente.')).toBeInTheDocument();
    expect(screen.queryByText(/private-canary/)).not.toBeInTheDocument();
  });
  it("cancels queued execution", async () => {
    vi.mocked(api.getExecution).mockResolvedValue(queued);
    vi.mocked(api.cancelExecution).mockResolvedValue({
      ...queued,
      status: "CANCELLED",
      cancel_requested: true,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cancelar execução" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Cancelar execução" }));

    await waitFor(() => {
      expect(api.cancelExecution).toHaveBeenCalledWith(7);
    });
  });
});
