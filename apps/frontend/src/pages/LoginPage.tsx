import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pairingCode, setPairingCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const code = pairingCode;
    setPairingCode("");
    try {
      if (!(await login(code))) {
        setError("Código inválido, utilizado ou expirado. Gere um novo código no console local.");
        return;
      }
      navigate(destination, { replace: true });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand login-brand"><div className="brand-mark" aria-hidden="true">N</div><div><strong>Nexer</strong><span>Automation Workspace</span></div></div>
        <div className="login-heading"><p className="eyebrow">Pareamento local</p><h1>Entrar no Nexer</h1><p className="muted">Use o código exibido no console local ao iniciar o Nexer. Ele vale por cinco minutos e só pode ser usado uma vez.</p></div>
        <form className="login-form" onSubmit={submit}>
          <label>Código de pareamento<input type="password" autoComplete="off" value={pairingCode} onChange={(e) => setPairingCode(e.target.value)} placeholder="Cole o código do console local" autoFocus required maxLength={128} /></label>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <button type="submit" className="primary-button login-button" disabled={submitting}>{submitting ? "Pareando..." : "Entrar"}</button>
        </form>
        <p className="login-note">As credenciais SGIND/IQOS serão solicitadas separadamente para cada execução.</p>
      </section>
    </main>
  );
}
