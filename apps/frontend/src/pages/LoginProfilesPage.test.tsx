import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginProfilesPage } from "./LoginProfilesPage";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({api: {listAccessGroups: vi.fn(async () => ({items: []})), createAccessGroup: vi.fn(), setAccessGroup: vi.fn(), listLoginProfiles: vi.fn(), createLoginProfile: vi.fn(), createLoginProfileVersion: vi.fn(), publishLoginProfile: vi.fn(), startLoginRecording: vi.fn(), getLoginRecording: vi.fn(), cancelLoginRecording: vi.fn(), disableLoginProfile: vi.fn()}}));

describe("Site login registration", () => {
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
