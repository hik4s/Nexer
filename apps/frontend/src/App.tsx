import { Dashboard } from "./pages/Dashboard";
import "./styles.css";

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
      </header>
      <Dashboard />
    </div>
  );
}
