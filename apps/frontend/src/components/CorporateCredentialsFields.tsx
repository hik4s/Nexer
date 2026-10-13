export function CorporateCredentialsFields() {
  return (
    <section className="card form-card" aria-labelledby="corporate-credentials-title">
      <p className="eyebrow">Credenciais por execução</p>
      <h2 id="corporate-credentials-title">Sistemas corporativos</h2>
      <p className="muted">Cada sistema utiliza suas próprias credenciais. Os campos serão liberados após a validação da integração.</p>
      <div className="form-grid">
        <fieldset>
          <legend>SGIND — aguardando validação</legend>
          <p className="muted">Telas de login e início identificadas. Integração automática em preparação.</p>
          <label>Usuário SGIND<input disabled autoComplete="off" /></label>
          <label>Senha SGIND<input disabled type="password" autoComplete="off" /></label>
        </fieldset>
        <fieldset>
          <legend>IQOS — aguardando validação</legend>
          <p className="muted">Telas de login e início identificadas. Integração automática em preparação.</p>
          <label>Usuário IQOS<input disabled autoComplete="off" /></label>
          <label>Senha IQOS<input disabled type="password" autoComplete="off" /></label>
        </fieldset>
      </div>
      <p className="muted">As senhas serão usadas somente durante a execução, sem gravação em arquivos ou no banco.</p>
    </section>
  );
}
