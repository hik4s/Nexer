import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { NewExecutionPage } from "./NewExecutionPage";

import { api } from "../lib/api";
import { HealthCard } from "../components/HealthCard";
import { Icon } from "../components/Icon";

export function Dashboard() {
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [batchSelection, setBatchSelection] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const routines = useQuery({queryKey: ["routines"], queryFn: api.listRoutines, retry: false});
  const [routineError, setRoutineError] = useState("");
  const [flowMessage, setFlowMessage] = useState("");
  const [flowBusy, setFlowBusy] = useState<number | null>(null);
  async function removeFlow(id: number, name: string) {
    if (!window.confirm(`Excluir o fluxo "${name}" da biblioteca? Se existir histórico ou rotina vinculada, ele será arquivado. Esta ação não poderá ser desfeita pela interface.`)) return;
    setFlowBusy(id); setFlowMessage("");
    try {
      const result = await api.deleteAutomation(id);
      setBatchSelection(current => current.filter(item => item !== id));
      setSelectedReport(current => current === String(id) ? null : current);
      await reports.refetch();
      setFlowMessage(result.archived ? "Fluxo arquivado. O histórico foi preservado." : "Fluxo excluído definitivamente.");
    } catch (error) {setFlowMessage(error instanceof Error ? error.message : "Não foi possível excluir o fluxo.");}
    finally {setFlowBusy(null);}
  }
  async function removeRoutine(id: number, name: string) {
    if (!window.confirm(`Excluir a rotina "${name}"? Os fluxos da rotina serão preservados.`)) return;
    setRoutineError("");
    try {await api.deleteRoutine(id); await routines.refetch();} catch {setRoutineError("Não foi possível remover a rotina.");}
  }
  const reports = useQuery({queryKey: ["automations", "published"], queryFn: () => api.listAutomations({status: "PUBLISHED", limit: 50, offset: 0}), retry: false});
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.getHealth,
    staleTime: 15_000,
    retry: false,
  });
  const visibleReports = reports.data?.items.filter(report => `${report.name} ${report.code}`.toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR"))) ?? [];

  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Seu workspace</p>
          <h1>Meus fluxos</h1>
          <p className="muted">
            Menos repetição. Mais espaço para o que importa.
          </p>
        </div>
      </div>
      <section className="dashboard-hero" aria-labelledby="hero-title">
        <div><span className="hero-kicker">AUTOMAÇÕES DO SEU JEITO</span><h2 id="hero-title">Registre uma vez.<br />Execute novamente.</h2><p>Transforme tarefas do navegador em fluxos reutilizáveis.<br className="desktop-break" /> Você escolhe os dados, o Nexer repete o caminho.</p>
          <Link className="hero-button" to="/flows/new">Criar fluxo guiado <Icon name="arrow" /></Link>
        </div><img src="/brand/nexer-symbol-white.svg" alt="" className="hero-symbol" aria-hidden="true" />
      </section>
      <div className="quick-actions">
        <Link to="/flows/new" className="quick-action"><span className="action-icon"><Icon name="studio" /></span><div><strong>Registrar um fluxo</strong><span>Um passo de cada vez.</span></div><Icon name="arrow" /></Link>
        <Link to="/site-logins" className="quick-action"><span className="action-icon"><Icon name="key" /></span><div><strong>Cadastrar login</strong><span>Configure o acesso uma vez.</span></div><Icon name="arrow" /></Link>
        <Link to="/executions" className="quick-action"><span className="action-icon"><Icon name="history" /></span><div><strong>Acompanhar execuções</strong><span>Cada etapa, no seu ritmo.</span></div><Icon name="arrow" /></Link>
      </div>
      <section className="card favorites"><div className="section-heading"><div><p className="eyebrow">Um clique para preparar</p><h2>Rotinas favoritas</h2></div><span className="badge">{routines.data?.items.length ?? 0}</span></div>
        {routines.data?.items.length ? <div className="flow-library">{routines.data.items.map(routine => <article className="flow-tile" key={routine.id}><h3>{routine.name}</h3><p className="muted">{routine.items.length} fluxos · credenciais solicitadas ao executar</p><div className="flow-tile-bottom"><Link className="text-button" to={`/batches/new?routine=${routine.id}`}>Preparar rotina <Icon name="arrow" /></Link><button className="text-button" onClick={() => removeRoutine(routine.id, routine.name)}>Excluir rotina</button></div></article>)}</div> : <p className="muted">Salve um grupo de fluxos como favorito ao preparar um lote.</p>}
        {routineError ? <p role="alert">{routineError}</p> : null}
      </section>
      <section className="card registered-reports" aria-labelledby="registered-reports-title">
        <div className="section-heading"><div><p className="eyebrow">Biblioteca de fluxos</p><h2 id="registered-reports-title">Fluxos registrados</h2><p className="muted">Personalize os campos de um fluxo ou selecione vários para um lote.</p></div><span className="badge">{reports.data?.items.length ?? 0} disponíveis</span></div>
        <div className="search-field"><Icon name="search" /><input aria-label="Buscar fluxos" type="search" placeholder="Buscar por nome ou código…" value={search} onChange={event => setSearch(event.target.value)} />{search ? <button type="button" className="text-button" aria-label="Limpar busca" onClick={() => setSearch("")}>Limpar</button> : null}</div>
        {reports.isLoading ? <p>Carregando relatórios…</p> : reports.isError ? <p role="alert">Não foi possível carregar os relatórios.</p> : !reports.data?.items.length ? <p>Nenhum relatório publicado. Registre e publique a receita no Studio.</p> :
          <div className="flow-library">{visibleReports.map(report => <article className={`flow-tile${batchSelection.includes(report.id) ? " flow-tile--selected" : ""}`} key={report.id}>
            <div className="flow-tile-top"><span className="action-icon"><Icon name="flows" /></span><label className="flow-select"><input type="checkbox" aria-label={`Selecionar ${report.name} para lote`} checked={batchSelection.includes(report.id)} disabled={!batchSelection.includes(report.id) && batchSelection.length >= 20} onChange={event => setBatchSelection(current => event.target.checked ? [...current, report.id] : current.filter(id => id !== report.id))} /></label></div>
            <h3>{report.name}</h3><p className="muted flow-description">{report.description || "Fluxo reutilizável. Preencha os dados ao executar."}</p>
            <div className="flow-tile-bottom"><span className="version">v{report.current_version}</span><button type="button" className="text-button" disabled={flowBusy !== null} onClick={() => removeFlow(report.id, report.name)}>Excluir fluxo</button><button type="button" className="text-button" aria-pressed={selectedReport === String(report.id)} aria-label={`Preparar ${report.name}`} onClick={() => setSelectedReport(current => current === String(report.id) ? null : String(report.id))}>{selectedReport === String(report.id) ? "Fechar campos" : "Preparar fluxo"}<Icon name="arrow" /></button></div>
          </article>)}</div>}
        {flowMessage ? <p role="status">{flowMessage}</p> : null}
        {search && !visibleReports.length && !reports.isLoading ? <p className="empty-state">Nenhum fluxo encontrado para “{search}”.</p> : null}
        <div className="batch-selection-bar"><span>{batchSelection.length ? `${batchSelection.length} fluxo${batchSelection.length > 1 ? "s" : ""} selecionado${batchSelection.length > 1 ? "s" : ""}` : "Selecione os cartões para executar em lote."}</span>
          {batchSelection.length ? <><button type="button" className="text-button" onClick={() => setBatchSelection([])}>Limpar seleção</button><Link className="primary-button" to={`/batches/new?flows=${batchSelection.join(",")}`}>Preparar lote ({batchSelection.length})<Icon name="arrow" /></Link></> : null}
        </div>
        {selectedReport ? <NewExecutionPage key={selectedReport} initialAutomationId={selectedReport} embedded /> : null}
      </section>

      <div className="grid">
        <HealthCard
          isLoading={health.isLoading}
          isError={health.isError}
          isHealthy={health.data?.status === "ok"}
        />
        <section className="card workspace-tip">
          <span className="action-icon"><Icon name="key" /></span><div><h2>Seu próximo fluxo começa aqui</h2><p className="muted">Cadastre um login, associe à receita e informe as credenciais somente ao executar.</p><Link className="text-button" to="/site-logins">Gerenciar logins <Icon name="arrow" /></Link></div>
        </section>
      </div>
    </main>
  );
}
