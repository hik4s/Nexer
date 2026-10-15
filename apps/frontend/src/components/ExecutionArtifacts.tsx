import {useMutation, useQuery} from '@tanstack/react-query';
import {api, type ExecutionArtifact} from '../lib/api';

export function ExecutionArtifacts({executionId, status}: {executionId: number; status: string}) {
  const active = status === 'QUEUED' || status === 'RUNNING';
  const files = useQuery({queryKey:['execution-artifacts',executionId,status],
    queryFn:()=>api.listExecutionArtifacts(executionId), retry:false, refetchInterval:active ? 1000 : false});
  const download = useMutation({mutationFn:async(file: ExecutionArtifact)=>{
    const blob = await api.downloadExecutionArtifact(executionId,file.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    try {
      link.href=url; link.download=file.filename; document.body.appendChild(link); link.click();
    } finally {
      link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  }});
  return <section className="card" aria-label="Arquivos da execução">
    <h2>Arquivos</h2>
    {files.isPending ? <p className="muted">Consultando arquivos…</p> : null}
    {files.isError ? <p role="alert">Não foi possível consultar os arquivos desta execução.</p> : null}
    {files.data?.items.length === 0 ? <p className="muted">{active ? 'Os arquivos aparecerão após a conclusão das automações.' : 'Nenhum arquivo validado disponível nesta execução.'}</p> : null}
    <ul>{files.data?.items.map(file=><li key={file.id}>
      <span>{file.filename} · {file.size} bytes</span>{' '}
      <button type="button" className="secondary-button" disabled={download.isPending}
        onClick={()=>download.mutate(file)}>Baixar {file.filename}</button>
    </li>)}</ul>
    {download.isError ? <p role="alert">O arquivo está indisponível ou foi alterado. Verifique sua sessão e os arquivos locais.</p> : null}
  </section>;
}
