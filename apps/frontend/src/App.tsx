import { useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import { AutomationsPage } from "./pages/AutomationsPage";
import { Dashboard } from "./pages/Dashboard";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { DestinationsPage } from "./pages/DestinationsPage";
import { ExecutionDetailPage } from "./pages/ExecutionDetailPage";
import { ExecutionsPage } from "./pages/ExecutionsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewExecutionPage } from "./pages/NewExecutionPage";
import { StudioPage } from "./pages/StudioPage";
import "./styles.css";

const navigation = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/automations", label: "Automações" },
  { to: "/executions", label: "Execuções" },
  { to: "/executions/new", label: "Nova execução" },
  { to: "/diagnostics", label: "Diagnóstico" },
  { to: "/destinations", label: "Destinos" },
  { to: "/studio", label: "Studio" },
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
        <div className="brand"><div className="brand-mark" aria-hidden="true">N</div><div><strong>Nexer</strong><span>Automation Workspace</span></div></div>
        <nav className="nav" aria-label="Navegação principal">
          {navigation.map((item) => <NavLink className={({ isActive }) => "nav-link" + (isActive ? " nav-link--active" : "")} end={item.end} to={item.to} key={item.to}>{item.label}</NavLink>)}
        </nav>
        <button type="button" className="secondary-button logout-button" onClick={handleLogout} disabled={loggingOut}>{loggingOut ? "Saindo..." : "Sair"}</button>
      </header>
      {logoutError ? <p className="form-error" role="alert">{logoutError}</p> : null}
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/automations" element={<AutomationsPage />} />
        <Route path="/executions" element={<ExecutionsPage />} />
        <Route path="/executions/new" element={<NewExecutionPage />} />
        <Route path="/executions/:id" element={<ExecutionDetailPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
        <Route path="/destinations" element={<DestinationsPage />} />
        <Route path="/studio" element={<StudioPage />} />
      </Routes>
    </div>
  );
}

export function App() {
  return <Routes><Route path="/login" element={<LoginPage />} /><Route path="/*" element={<ProtectedLayout />} /></Routes>;
}
