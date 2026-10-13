import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginProfilesPage } from "./LoginProfilesPage";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({api: {listAccessGroups: vi.fn(async () => ({items: []})), createAccessGroup: vi.fn(), setAccessGroup: vi.fn(), listLoginProfiles: vi.fn(), createLoginProfile: vi.fn(), createLoginProfileVersion: vi.fn(), publishLoginProfile: vi.fn(), startLoginRecording: vi.fn(), getLoginRecording: vi.fn(), cancelLoginRecording: vi.fn(), disableLoginProfile: vi.fn(), deleteLoginProfile: vi.fn()}}));

describe("Site login registration", () => {
  it("requires new targets and confirmation after changing a ready profile login URL", async () => {
    const configuration = {login_url: "https://site.invalid/old-login", allowed_origins: ["https://site.invalid"], username_target: {selector: "#old-user", frames: []}, password_target: {selector: "#old-pass", frames: []}, submit_target: {selector: "#old-submit", frames: []}, success_rule: {kind: "marker" as const, target: {selector: "#old-home", frames: []}}};
    const profile = {id: 9, name: "Site pronto", status: "READY", current_version: 1, published: true, configuration};
    vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [profile], total: 1, limit: 50, offset: 0});
    vi.mocked(api.createLoginProfileVersion).mockImplementation(async (_id, draft) => ({...profile, status: "DRAFT", current_version: 2, published: false, configuration: draft}));
    render(<QueryClientProvider client={new QueryClient()}><LoginProfilesPage /></QueryClientProvider>);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name: "Site pronto · v1 · Configuração pronta"}));
    const url = screen.getByLabelText("URL de login deste acesso");
    await user.clear(url);
    await user.type(url, "https://site.invalid/new-login");
    await user.click(screen.getByRole("button", {name: "Salvar perfil"}));
    await waitFor(() => expect(screen.getByRole("button", {name: "Identificar campos no Edge"})).toBeEnabled());
    expect(screen.getByRole("button", {name: "Publicar perfil"})).toBeDisabled();
    expect(screen.getAllByText("Ainda não identificado")).toHaveLength(3);
    expect(screen.getByLabelText("URL após entrar")).toHaveValue("");
    expect(configuration.password_target.selector).toBe("#old-pass");
  });
  it("lets the user correct the login URL and saves a new version", async () => {
    const original = {login_url: "https://indicadoresenergisaess.scl.corp/", allowed_origins: ["https://indicadoresenergisaess.scl.corp"], username_target: null, password_target: null, submit_target: null, success_rule: null};
    const profile = {id: 1, name: "SGIND", status: "DRAFT", current_version: 1, published: false, configuration: original};
    vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [profile], total: 1, limit: 50, offset: 0});
    vi.mocked(api.createLoginProfileVersion).mockResolvedValue({...profile, current_version: 2, configuration: {...original, login_url: "https://indicadoresenergisaess.scl.corp/sgind/"}});
    render(<QueryClientProvider client={new QueryClient()}><LoginProfilesPage /></QueryClientProvider>);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name: "SGIND · v1 · Rascunho"}));
    const url = screen.getByLabelText("URL de login deste acesso");
    await user.clear(url);
    await user.type(url, "https://indicadoresenergisaess.scl.corp/sgind/");
    expect(screen.getByRole("button", {name: "Identificar campos no Edge"})).toBeDisabled();
    await user.click(screen.getByRole("button", {name: "Salvar perfil"}));
    await waitFor(() => expect(api.createLoginProfileVersion).toHaveBeenCalledWith(1, {...original, login_url: "https://indicadoresenergisaess.scl.corp/sgind/"}));
    await waitFor(() => expect(screen.getByRole("button", {name: "Identificar campos no Edge"})).toBeEnabled());
    expect(original.login_url).toBe("https://indicadoresenergisaess.scl.corp/");
  });
  it("cancels the Edge selection when leaving the page", async () => {
    const profile = {id: 8, name: "Site", status: "DRAFT", current_version: 1, published: false, configuration: {login_url: "https://site.invalid/login", allowed_origins: ["https://site.invalid"], username_target: null, password_target: null, submit_target: null, success_rule: null}};
    vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [profile], total: 1, limit: 50, offset: 0});
    vi.mocked(api.startLoginRecording).mockResolvedValue({id: "recording-8", profile_id: 8, version: 1, status: "RECORDING", targets: {}, error: null});
    vi.mocked(api.getLoginRecording).mockResolvedValue({id: "recording-8", profile_id: 8, version: 1, status: "RECORDING", targets: {}, error: null});
    const {unmount} = render(<QueryClientProvider client={new QueryClient()}><LoginProfilesPage /></QueryClientProvider>);
    await userEvent.click(await screen.findByRole("button", {name: "Site · v1 · Rascunho"}));
    await userEvent.click(screen.getByRole("button", {name: "Identificar campos no Edge"}));
    await screen.findByRole("button", {name: "Cancelar seleção"});
    unmount();
    await waitFor(() => expect(api.cancelLoginRecording).toHaveBeenCalledWith(8, "recording-8"));
  });
  it("registers a site without requesting or saving credentials", async () => {
    vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});
    vi.mocked(api.createLoginProfile).mockResolvedValue({id: 1, name: "Meu site", status: "DRAFT", current_version: 1, published: false, configuration: {login_url: "http://127.0.0.1:8765/login", allowed_origins: ["http://127.0.0.1:8765"], username_target: null, password_target: null, submit_target: null, success_rule: null}});
    render(<QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}><LoginProfilesPage /></QueryClientProvider>);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Nome do site"), "Meu site");
    await user.type(screen.getByLabelText("URL de login"), "http://127.0.0.1:8765/login");
    await user.click(screen.getByRole("button", {name: "Cadastrar login"}));
    await waitFor(() => expect(api.createLoginProfile).toHaveBeenCalledWith({name: "Meu site", login_url: "http://127.0.0.1:8765/login"}));
    expect(await screen.findByRole("button", {name: "Identificar campos no Edge"})).toBeEnabled();
    expect(document.querySelector('input[type=password]')).toBeNull();
    expect(screen.getByRole("button", {name: "Publicar perfil"})).toBeDisabled();
  });
});


describe("Permanent profile deletion", () => {
  const profile = {id: 17, name: "Acesso removível", status: "DRAFT", current_version: 1, published: false, configuration: {login_url: "https://site.invalid/login", allowed_origins: ["https://site.invalid"], username_target: null, password_target: null, submit_target: null, success_rule: null}};
  async function selectProfile() {
    vi.mocked(api.deleteLoginProfile).mockReset();
    vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [profile], total: 1, limit: 50, offset: 0});
    render(<QueryClientProvider client={new QueryClient()}><LoginProfilesPage /></QueryClientProvider>);
    await userEvent.click(await screen.findByRole("button", {name: "Acesso removível · v1 · Rascunho"}));
  }
  it("requires confirmation and preserves selection when canceled", async () => {
    await selectProfile();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    await userEvent.click(screen.getByRole("button", {name: "Excluir perfil"}));
    expect(confirm).toHaveBeenCalled();
    expect(api.deleteLoginProfile).not.toHaveBeenCalled();
    expect(screen.getByLabelText("URL de login deste acesso")).toHaveValue(profile.configuration.login_url);
    confirm.mockRestore();
  });
  it("removes a confirmed profile and clears its editor after refetch", async () => {
    await selectProfile();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.deleteLoginProfile).mockImplementation(async () => {
      vi.mocked(api.listLoginProfiles).mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});
    });
    await userEvent.click(screen.getByRole("button", {name: "Excluir perfil"}));
    await waitFor(() => expect(api.deleteLoginProfile).toHaveBeenCalledWith(17));
    await waitFor(() => expect(screen.queryByLabelText("URL de login deste acesso")).toBeNull());
    await waitFor(() => expect(screen.queryByRole("button", {name: "Acesso removível · v1 · Rascunho"})).toBeNull());
    confirm.mockRestore();
  });
  it("shows linked-profile errors and retains the selected editor", async () => {
    await selectProfile();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.deleteLoginProfile).mockRejectedValue(new Error("Perfil vinculado. Desative o perfil."));
    await userEvent.click(screen.getByRole("button", {name: "Excluir perfil"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Perfil vinculado");
    expect(screen.getByLabelText("URL de login deste acesso")).toHaveValue(profile.configuration.login_url);
    confirm.mockRestore();
  });
  it("disables deletion during an active Edge selection", async () => {
    await selectProfile();
    const recording = {id: "delete-active", profile_id: 17, version: 1, status: "RECORDING", targets: {}, error: null};
    vi.mocked(api.startLoginRecording).mockResolvedValue(recording);
    vi.mocked(api.getLoginRecording).mockResolvedValue(recording);
    await userEvent.click(screen.getByRole("button", {name: "Identificar campos no Edge"}));
    await screen.findByRole("button", {name: "Cancelar seleção"});
    expect(screen.getByRole("button", {name: "Excluir perfil"})).toBeDisabled();
  });
});
