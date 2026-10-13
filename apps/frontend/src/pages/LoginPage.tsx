import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../lib/api";
import { Brand } from "../components/Brand";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pairingCode, setPairingCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [renewalStatus, setRenewalStatus] = useState<string | null>(null);
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  async function generatePairingCode() {
    setError(null);
    setRenewalStatus("Gerando novo código...");
    setGenerating(true);
    setPairingCode("");
    try {
      await api.requestPairingCode();
      setRenewalStatus("Novo código gerado. Copie o código na janela local do Nexer ou no console.");
    } catch (cause) {
      setRenewalStatus(null);
      setError(cause instanceof TypeError
        ? "Nexer local não está acessível. Inicie o aplicativo local e tente novamente. Fechar o terminal de uma execução manual encerra o serviço."
        : cause instanceof Error ? cause.message : "Não foi possível gerar um novo código. Tente novamente.");
    } finally {
      setGenerating(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    setRenewalStatus(null);
    const code = pairingCode;
    setPairingCode("");
    try {
      if (!(await login(code))) {
        setError("Código inválido, utilizado ou expirado. Clique em Gerar novo token.");
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
        <Brand className="login-brand" />
        <div className="login-heading"><p className="eyebrow">Pareamento local</p><h1>Entrar no Nexer</h1><p className="muted">Use o código exibido localmente pelo Nexer. Ele vale por cinco minutos e só pode ser usado uma vez.</p></div>
        <form className="login-form" onSubmit={submit}>
          <label>Código de pareamento<input type="password" autoComplete="off" value={pairingCode} onChange={(e) => setPairingCode(e.target.value)} placeholder="Cole o código exibido pelo Nexer" autoFocus required maxLength={128} /></label>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <button type="submit" className="primary-button login-button" disabled={submitting || generating}>{submitting ? "Pareando..." : "Entrar"}</button>
          <button type="button" className="secondary-button login-button" disabled={submitting || generating} onClick={generatePairingCode}>{generating ? "Gerando..." : "Gerar novo token"}</button>
          {renewalStatus ? <p className="muted" role="status">{renewalStatus}</p> : null}
        </form>
        <p className="login-note">Seus logins de sites serão solicitados separadamente para cada execução.</p>
      </section>
    </main>
  );
}
