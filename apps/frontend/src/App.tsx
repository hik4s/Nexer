import { NavLink, Route, Routes } from "react-router-dom";

import { AutomationsPage } from "./pages/AutomationsPage";
import { Dashboard } from "./pages/Dashboard";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { DestinationsPage } from "./pages/DestinationsPage";
import { ExecutionDetailPage } from "./pages/ExecutionDetailPage";
import { ExecutionsPage } from "./pages/ExecutionsPage";
import { NewExecutionPage } from "./pages/NewExecutionPage";
import "./styles.css";

const navigation = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/automations", label: "Automações" },
  { to: "/executions", label: "Execuções" },
  { to: "/executions/new", label: "Nova execução" },
  { to: "/diagnostics", label: "Diagnóstico" },
  { to: "/destinations", label: "Destinos" },
];

export function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">R</div>
          <div>
            <strong>RelatPy</strong>
            <span>Automation Workspace</span>
          </div>
        </div>

        <nav className="nav" aria-label="Navegação principal">
          {navigation.map((item) => (
            <NavLink
              className={({ isActive }) =>
                "nav-link" + (isActive ? " nav-link--active" : "")
              }
              end={item.end}
              to={item.to}
              key={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/automations" element={<AutomationsPage />} />
        <Route path="/executions" element={<ExecutionsPage />} />
        <Route path="/executions/new" element={<NewExecutionPage />} />
        <Route path="/executions/:id" element={<ExecutionDetailPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
        <Route path="/destinations" element={<DestinationsPage />} />
      </Routes>
    </div>
  );
}
