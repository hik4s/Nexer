import { useRef } from "react";
import {isSupportedSiteFormat, toNativeDateTime, toSiteDateTime, type SiteDateFormat} from "../lib/siteDates";

export type FieldRules = {
  control?: string; min?: number | string; max?: number | string; step?: number | "any";
  min_length?: number; max_length?: number; pattern?: string;
  input_mode?: "none" | "text" | "decimal" | "numeric" | "tel" | "search" | "email" | "url";
  rows?: number; required?: boolean; site_format?: SiteDateFormat;
};
export type ParameterDeclaration = {
  label?: string; type?: string; required?: boolean; secret?: boolean; format?: string;
  allow_empty?: boolean; field?: FieldRules;
};
export type FieldOption = {value: string; label: string; disabled: boolean};
export type FieldCatalog = {options: FieldOption[]; error: string | null};

export function parameterLabel(name: string) {
  return ({company: "Empresa", regional: "Regional", base_url: "Endereço inicial", period_start: "Data inicial", period_end: "Data final"} as Record<string, string>)[name] ?? name;
}
export function fieldLabel(name: string, declaration: ParameterDeclaration) {
  return (typeof declaration.label === "string" ? declaration.label.trim() : "") || parameterLabel(name);
}
export function fieldValueLabel(value: unknown, declaration: ParameterDeclaration = {}, catalog?: FieldCatalog): string {
  if (Array.isArray(value)) return value.map(item => fieldValueLabel(item, declaration, catalog)).join(", ") || "Sem seleção";
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  const text = String(value);
  const option = catalog?.options.find(option => option.value === text);
  if (option) return option.label;
  if ((declaration.field?.control === "date" || declaration.format === "date") && /^\d{4}-\d{2}-\d{2}$/.test(text)) return text.split("-").reverse().join("/");
  return text;
}

export function RecipeField({name, declaration, value, catalog, onChange, idPrefix = ""}: {
  name: string; declaration: ParameterDeclaration; value: string | undefined;
  catalog?: FieldCatalog; onChange: (value: string) => void; idPrefix?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const rules = declaration.field ?? {};
  const control = rules.control ?? (declaration.format === "date" ? "date" : ["number", "integer"].includes(declaration.type ?? "") ? "number" : "text");
  const label = fieldLabel(name, declaration);
  const required = declaration.required !== false && !declaration.allow_empty;
  const options = catalog?.options ?? [];
  const unavailable = !catalog || Boolean(catalog.error);
  const hint = unavailable ? "Carregue as opções do site para escolher." : options.length === 0 ? "Nenhuma opção disponível no site para estes filtros." : null;
  const id = `parameter-${idPrefix}${name}`;
  if (control === "radio") return (
    <fieldset className="recipe-options">
      <legend>{label}</legend>
      {hint ? <p className="muted">{hint}</p> : null}
      {options.map(option => <label className="checkbox-label" key={option.value}>
        <input type="radio" name={id} value={option.value} checked={value === option.value} required={required} disabled={option.disabled}
          onChange={() => onChange(option.value)} />{option.label}
      </label>)}
    </fieldset>
  );
  if (control === "checkbox") return (
    <div className="recipe-checkbox">
      <label className="checkbox-label"><input type="checkbox" ref={element => {if (element) element.indeterminate = value === undefined;}}
        required={rules.required} checked={value === "true"} onChange={event => onChange(String(event.target.checked))} />{label}</label>
      {value === undefined ? <button type="button" className="secondary-button" onClick={() => onChange("false")}>Definir {label} como desmarcado</button> : null}
    </div>
  );
  if (control === "select" || control === "multiselect") {
    let selected: string[] = [];
    if (control === "multiselect") { try {selected = JSON.parse(value ?? "[]");} catch { /* unset */ } }
    return <div><label htmlFor={id}>{label}
      <select id={id} multiple={control === "multiselect"} disabled={unavailable} required={required}
        value={control === "multiselect" ? selected : value ?? ""}
        onChange={event => onChange(control === "multiselect" ? JSON.stringify([...event.target.selectedOptions].map(option => option.value)) : event.target.value)}>
        {control === "select" ? <option value="">Selecione…</option> : null}
        {options.filter(option => control === "multiselect" || option.value !== "").map((option, index) => <option value={option.value} key={`${option.value}:${index}`} disabled={option.disabled}>{option.label}</option>)}
      </select>
    </label>
      {hint ? <span className="muted">{hint}</span> : null}
      {control === "multiselect" && value === undefined && declaration.allow_empty ? <button type="button" className="secondary-button" onClick={() => onChange("[]")}>Confirmar {label} sem seleção</button> : null}
    </div>;
  }
  if (declaration.type === "boolean") return <label htmlFor={id}>{label}
    <select id={id} required={required} value={value ?? ""} onChange={event => onChange(event.target.value)}>
      <option value="">Selecione…</option><option value="true">Sim</option><option value="false">Não</option>
    </select>
  </label>;
  if (["date","datetime-local"].includes(control) && isSupportedSiteFormat(rules.site_format)) {
    const format = rules.site_format;
    const native = toNativeDateTime(value ?? "", format, control === "datetime-local");
    return <div className="recipe-date-field">
      <label htmlFor={id}>{label}
        <input id={id} type={control} step={control === "datetime-local" ? 1 : undefined}
          required={required} min={rules.min} max={rules.max}
          value={native ?? ""}
          onChange={event => {
            const result = toSiteDateTime(event.target.value, format);
            if (result !== null) onChange(result);
          }}/>
      </label>
      <span className="muted">Formato enviado ao site: {format}</span>
      {native === null ? <p role="alert">O valor anterior não corresponde à data esperada. Selecione uma data válida.</p> : null}
    </div>;
  }
  const common = {
    id, required, minLength: rules.min_length, maxLength: rules.max_length,
    value: value ?? "", onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(event.target.value),
    onBlur: (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {if (declaration.allow_empty) onChange(event.target.value);},
  };
  return <div><label htmlFor={id}>{label}
    {control === "textarea" ? <textarea {...common} rows={rules.rows ?? 4} /> :
      <input {...common} ref={inputRef} type={control} min={rules.min} max={rules.max} step={rules.step ?? (declaration.type === "number" ? "any" : undefined)} pattern={rules.pattern} inputMode={rules.input_mode}
        placeholder={declaration.type === "array" ? 'Lista JSON, como ["opção 1", "opção 2"]' : undefined} />}
  </label>
    {["range", "color"].includes(control) && value === undefined ? <button type="button" className="secondary-button" onClick={() => onChange(inputRef.current?.value ?? "")}>Confirmar {label}</button> : null}
  </div>;
}
