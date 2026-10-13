import { useEffect } from "react";

export type CredentialFields = {username: HTMLInputElement | null; password: HTMLInputElement | null};
export function clearCredentials(fields: CredentialFields) {
  if (fields.username) fields.username.value = "";
  if (fields.password) fields.password.value = "";
}
export function readCredentials(fields: CredentialFields) {
  const username = fields.username?.value ?? "", password = fields.password?.value ?? "";
  if (!username || !password) throw new Error("Informe usuário e senha para o perfil de login.");
  return {username, password};
}
export function SiteCredentialsFields({name, fields, disabled = false, onChange}: {name: string; fields: CredentialFields; disabled?: boolean; onChange?: () => void}) {
  useEffect(() => {
    const username = fields.username, password = fields.password;
    return () => {if (username) username.value = ""; if (password) password.value = "";};
  }, [fields]);
  useEffect(() => {if (disabled) clearCredentials(fields);}, [disabled, fields]);
  return <fieldset className="recipe-options">
    <legend>Acesso — {name}</legend>
    <p className="muted">As credenciais são usadas somente nesta execução, sem gravação na receita ou no banco.</p>
    <div className="form-grid">
      <label>Usuário — {name}<input ref={element => {fields.username = element;}} required={!disabled} disabled={disabled} autoComplete="off" maxLength={1024} onInput={onChange} /></label>
      <label>Senha — {name}<input ref={element => {fields.password = element;}} type="password" required={!disabled} disabled={disabled} autoComplete="off" maxLength={1024} onInput={onChange} /></label>
    </div>
    {disabled ? <p className="muted">O modo de teste simula o fluxo sem realizar login.</p> : null}
  </fieldset>;
}
