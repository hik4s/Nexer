import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("API error messages", () => {
  it("preserves the actionable login URL error returned by the backend", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({error: {
      code: "LOGIN_URL_INVALID", message: "Informe uma URL HTTPS sem parâmetros.", details: null,
    }}), {status: 422, headers: {"Content-Type": "application/json"}})));
    await expect(api.createLoginProfile({name: "Site", login_url: "http://site.invalid/login"}))
      .rejects.toThrow("Informe uma URL HTTPS sem parâmetros.");
  });

  it("keeps the status fallback when the response is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Unavailable", {status: 503})));
    await expect(api.listLoginProfiles()).rejects.toThrow("API_REQUEST_FAILED:503");
  });

  it("keeps the status fallback for an unexpected JSON structure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({detail: "Unexpected"}), {status: 422})));
    await expect(api.listLoginProfiles()).rejects.toThrow("API_REQUEST_FAILED:422");
  });
});
