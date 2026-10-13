import {describe, expect, it} from "vitest";
import {initialSiteUrl, commonParameters, datePeriod, accessIdentity, intersectCatalogs} from "./practical";
describe("Practical preparation", () => {
  it("uses local calendar boundaries across year and leap month", () => {
    expect(datePeriod("previous", new Date(2026, 0, 2))).toEqual({period_start: "2025-12-01", period_end: "2025-12-31"});
    expect(datePeriod("previous", new Date(2024, 2, 1))).toEqual({period_start: "2024-02-01", period_end: "2024-02-29"});
    expect(datePeriod("month", new Date(2026, 9, 13))).toEqual({period_start: "2026-10-01", period_end: "2026-10-13"});
  });
  it("shares only identical rules and excludes secrets and initial URLs", () => {
    const a = {variables: {company: {type: "string"}, quantity: {type: "integer", field: {min: 1}}, password: {secret: true}, base_url: {}, regional: {field: {control: "select"}}}};
    const b = {variables: {...a.variables, quantity: {type: "integer", field: {min: 2}}}};
    expect(commonParameters([a, b]).map(([name]) => name)).toEqual(["company", "regional"]);
    expect(accessIdentity({id: 1, current_version: 2, group_id: 8})).toBe("group-8");
  });
  it("requires loaded catalogs and matches enabled values and labels across sites", () => {
    const first = {error: null, options: [{value: "A", label: "Empresa A", disabled: false}]};
    expect(intersectCatalogs([first, undefined])).toBeUndefined();
    expect(intersectCatalogs([first, {error: null, options: [{value: "A", label: "Outra empresa", disabled: false}]}])?.options).toEqual([]);
    expect(intersectCatalogs([first, first])?.options).toEqual(first.options);
  });
});

describe("Site application routes", () => {
  it("preserves the requested SGIND report route", () => {
    const value = "https://indicadoresenergisaess.scl.corp/sgind/#/relatatendtodasocorrencias";
    expect(initialSiteUrl({site_url: value})).toBe(value);
  });
  it("rejects embedded credentials and query or token fragments", () => {
    for (const value of ["https://user:canary@site.invalid/", "https://site.invalid/?token=canary", "https://site.invalid/#token=canary", "https://site.invalid/#/report?token=canary", "http://site.invalid/"])
      expect(initialSiteUrl({site_url: value})).toBeUndefined();
  });
});

describe("Site URL validation agrees with the API", () => {
  it("rejects invalid hostnames and abbreviated loopback addresses before preparation", () => {
    for (const value of ["https://site_name.invalid/", "http://127.1/"])
      expect(initialSiteUrl({site_url: value})).toBeUndefined();
  });
});
