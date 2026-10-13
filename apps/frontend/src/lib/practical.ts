import {ParameterDeclaration, FieldCatalog} from "../components/RecipeField";
export function datePeriod(preset: "today" | "month" | "previous", now = new Date()) {
  const date = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  const start = preset === "today" ? now : new Date(now.getFullYear(), now.getMonth() - (preset === "previous" ? 1 : 0), 1);
  const end = preset === "previous" ? new Date(now.getFullYear(), now.getMonth(), 0) : now;
  return {period_start: date(start), period_end: date(end)};
}
export function commonParameters(recipes: Record<string, unknown>[]) {
  if (recipes.length < 2) return [] as [string, ParameterDeclaration][];
  const declarations = recipes.map(recipe => recipe.variables as Record<string, ParameterDeclaration> ?? {});
  const signature = (value: ParameterDeclaration) => JSON.stringify({type: value.type ?? "string", format: value.format, required: value.required !== false, allow_empty: !!value.allow_empty, field: Object.entries(value.field ?? {}).sort(([a], [b]) => a.localeCompare(b))});
  return Object.entries(declarations[0]).filter(([name, declaration]) => name !== "base_url" && !declaration.secret && declarations.every(current => current[name] && !current[name].secret && signature(current[name]) === signature(declaration)));
}
export function intersectCatalogs(catalogs: (FieldCatalog | undefined)[]): FieldCatalog | undefined {
  if (!catalogs.length || catalogs.some(catalog => !catalog || catalog.error)) return undefined;
  return {error: null, options: catalogs[0]!.options.filter(option => !option.disabled && catalogs.every(catalog => catalog!.options.some(current => !current.disabled && current.value === option.value && current.label === option.label)))};
}
export function accessIdentity(profile: {id: number; current_version: number; group_id?: number | null}) {return profile.group_id ? `group-${profile.group_id}` : `profile-${profile.id}-v${profile.current_version}`;}
export function initialSiteUrl(recipe: Record<string, unknown>) {
  try {
    if (typeof recipe.site_url !== "string") return undefined;
    const value = recipe.site_url.trim();
    if (value.length > 2048 || /\s/.test(value) || value.includes("?")) return undefined;
    const authority = value.match(/^[A-Za-z][A-Za-z0-9+.-]*:\/\/([^/?#]*)/)?.[1];
    if (!authority || authority.includes("@")) return undefined;
    const url = new URL(value);
    url.hostname = url.hostname.toLowerCase().replace(/\.$/, "");
    if (!url.hostname.startsWith("[") && !/^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/.test(url.hostname)) return undefined;
    if (url.protocol === "http:" && !/^(?:localhost\.?|127\.0\.0\.1\.?|\[::1\])(?::[0-9]*)?$/i.test(authority)) return undefined;
    if (url.username || url.password || url.search || (url.hash && !/^#\/[A-Za-z0-9_/-]*$/.test(url.hash)) || url.port === "0" || !(url.protocol === "https:" || (url.protocol === "http:" && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)))) return undefined;
    return url.toString();
  } catch {return undefined;}
}
export function flowDestination(recipe: Record<string, unknown>, inputs: Record<string, unknown>, fallback?: string) {
  const steps = Array.isArray(recipe.steps) ? recipe.steps as Record<string, unknown>[] : [];
  const navigation = steps.find(step => step.action === "navigate");
  if (typeof navigation?.url === "string") {
    const url = navigation.url.replace(/{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}/g, (match, name: string) => typeof inputs[name] === "string" ? inputs[name] as string : match);
    if (!url.includes("{{")) return url;
  }
  return typeof inputs.base_url === "string" ? inputs.base_url : initialSiteUrl(recipe) ?? fallback ?? "Destino definido na receita";
}
