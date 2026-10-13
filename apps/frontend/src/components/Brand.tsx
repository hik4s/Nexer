export function Brand({className = ""}: {className?: string}) {
  return <div className={`brand ${className}`}><img className="brand-logo" src="/brand/nexer-horizontal.svg" alt="Nexer" width="180" height="61" /><span>Seu espaço de automação</span></div>;
}
