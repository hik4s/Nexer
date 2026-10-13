import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "./LoginPage";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: { requestPairingCode: vi.fn() } }));
vi.mock("../auth", () => ({ useAuth: () => ({ login: vi.fn() }) }));
function renderPage() { return render(<MemoryRouter><LoginPage /></MemoryRouter>); }

describe("LoginPage pairing renewal", () => {
  beforeEach(() => vi.clearAllMocks());
  it("shows pending state and asks the user to copy the code from the local console", async () => {
    let resolve!: (value: {issued: boolean; expires_in: number}) => void;
    vi.mocked(api.requestPairingCode).mockReturnValue(new Promise((done) => { resolve = done; }));
    renderPage();
    fireEvent.change(screen.getByLabelText("Código de pareamento"), { target: { value: "synthetic-old-code" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar novo token" }));
    expect(screen.getByRole("button", { name: "Gerando..." })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Gerando");
    expect(screen.getByLabelText("Código de pareamento")).toHaveValue("");
    resolve({ issued: true, expires_in: 300 });
    expect(await screen.findByText("Novo código gerado. Copie o código na janela local do Nexer ou no console.")).toHaveAttribute("role", "status");
    expect(screen.getByRole("button", { name: "Gerar novo token" })).toBeEnabled();
    expect(screen.getByLabelText("Código de pareamento")).toHaveValue("");
  });
  it("explains when the local API cannot be reached", async () => {
    vi.mocked(api.requestPairingCode).mockRejectedValue(new TypeError("Failed to fetch"));
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Gerar novo token" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nexer local não está acessível");
    expect(screen.getByRole("button", { name: "Gerar novo token" })).toBeEnabled();
  });
  it("shows accessible failure and allows another attempt", async () => {
    vi.mocked(api.requestPairingCode).mockRejectedValue(new Error("Aguarde cinco segundos antes de gerar outro código."));
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Gerar novo token" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Aguarde cinco segundos");
    expect(screen.getByRole("button", { name: "Gerar novo token" })).toBeEnabled();
    vi.mocked(api.requestPairingCode).mockResolvedValue({ issued: true, expires_in: 300 });
    fireEvent.click(screen.getByRole("button", { name: "Gerar novo token" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Novo código gerado");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
