import { useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import { Brand } from "./components/Brand";
import { Icon, IconName } from "./components/Icon";
import { AutomationsPage } from "./pages/AutomationsPage";
import { Dashboard } from "./pages/Dashboard";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { DeveloperEyePage } from "./pages/DeveloperEyePage";
import { DestinationsPage } from "./pages/DestinationsPage";
import { ExecutionDetailPage } from "./pages/ExecutionDetailPage";
import { ExecutionsPage } from "./pages/ExecutionsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewExecutionPage } from "./pages/NewExecutionPage";
import { StudioPage } from "./pages/StudioPage";
import { LoginProfilesPage } from "./pages/LoginProfilesPage";
import { NewBatchPage } from "./pages/NewBatchPage";
import { BatchDetailPage } from "./pages/BatchDetailPage";
import { NewFlowPage } from "./pages/NewFlowPage";
import "./styles.css";

const navigation: {to: string; label: string; end?: boolean; icon: IconName}[] = [
  { to: "/", label: "Meus fluxos", end: true, icon: "home" },
  { to: "/site-logins", label: "Acessos", icon: "key" },
  { to: "/executions", label: "Execuções", icon: "history" },
];

function ProtectedLayout() {
  const { authenticated, ready, logout } = useAuth();
  const location = useLocation();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLogoutError(null);
    setLoggingOut(true);
    try {
      await logout();
    } catch {
      setLogoutError("Não foi possível encerrar a sessão no backend. Verifique a conexão e tente novamente.");
    } finally {
      setLoggingOut(false);
    }
  }

  if (!ready) return <main className="login-shell"><p>Verificando sessão do Nexer...</p></main>;
  if (!authenticated) return <Navigate to="/login" replace state={{ from: location }} />;

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand-home" aria-label="Nexer — início"><Brand /></NavLink>
        <p className="nav-section-label">Workspace</p>
        <nav className="nav" aria-label="Navegação principal">
          {navigation.map((item) => <NavLink className={({ isActive }) => "nav-link" + (isActive ? " nav-link--active" : "")} end={item.end} to={item.to} key={item.to}><Icon name={item.icon} />{item.label}</NavLink>)}
        </nav>
        <details className="advanced-navigation"><summary>Ferramentas e ajustes</summary><nav className="nav" aria-label="Ferramentas"><NavLink className="nav-link" to="/flows/new"><Icon name="flows" />Criar fluxo</NavLink><NavLink className="nav-link" to="/studio"><Icon name="studio" />Studio avançado</NavLink><NavLink className="nav-link" to="/automations"><Icon name="flows" />Catálogo técnico</NavLink><NavLink className="nav-link" to="/destinations"><Icon name="folder" />Destinos</NavLink><NavLink className="nav-link" to="/diagnostics"><Icon name="pulse" />Diagnóstico</NavLink><NavLink className="nav-link" to="/developer-eye"><Icon name="studio" />Eye Developer</NavLink></nav></details>
        <div className="workspace-note"><span className="status status--success" aria-hidden="true" /><span>Workspace local<small>Registre. Personalize. Execute.</small></span></div>
        <button type="button" className="secondary-button logout-button" onClick={handleLogout} disabled={loggingOut}>{loggingOut ? "Saindo..." : "Sair"}</button>
      </header>
      <div className="workspace-content">
      {logoutError ? <p className="form-error" role="alert">{logoutError}</p> : null}
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/automations" element={<AutomationsPage />} />
        <Route path="/executions" element={<ExecutionsPage />} />
        <Route path="/executions/new" element={<NewExecutionPage />} />
        <Route path="/executions/:id" element={<ExecutionDetailPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
        <Route path="/developer-eye" element={<DeveloperEyePage />} />
        <Route path="/destinations" element={<DestinationsPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/site-logins" element={<LoginProfilesPage />} />
        <Route path="/batches/new" element={<NewBatchPage />} />
        <Route path="/flows/new" element={<NewFlowPage />} />
        <Route path="/batches/:id" element={<BatchDetailPage />} />
      </Routes>
      </div>
    </div>
  );
}

export function App() {
  return <Routes><Route path="/login" element={<LoginPage />} /><Route path="/*" element={<ProtectedLayout />} /></Routes>;
}
