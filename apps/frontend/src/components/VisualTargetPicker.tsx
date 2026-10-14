import {useEffect, useRef, useState} from 'react';
import {api, type TargetKind, type TargetPicking} from '../lib/api';

type Props = {url: string; kind: TargetKind; label: string; invalidationKey: string; disabled?: boolean;
  onPicked: (selector: string) => void; onBusy: (busy: boolean) => void};

export function VisualTargetPicker({url, kind, label, invalidationKey, disabled, onPicked, onBusy}: Props) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const mounted = useRef(true), generation = useRef(0), opening = useRef(false);
  const session = useRef<string | null>(null), timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controller = useRef<AbortController | null>(null);
  const callbacks = useRef({onPicked, onBusy}); callbacks.current = {onPicked, onBusy};
  function stop(notify = true) {
    generation.current++; opening.current = false;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null; controller.current?.abort(); controller.current = null;
    const id = session.current; session.current = null;
    if (id) void api.cancelTargetPicking(id).catch(() => {});
    if (notify) {setBusy(false); callbacks.current.onBusy(false);}
  }
  useEffect(() => {mounted.current = true; return () => {mounted.current = false; stop(false); callbacks.current.onBusy(false);};}, []);
  useEffect(() => {
    if (opening.current || session.current) {stop(); setMessage('A edição mudou. A seleção anterior foi cancelada.');}
  }, [url, kind, invalidationKey]);

  async function start() {
    if (opening.current || session.current) return;
    const token = ++generation.current;
    opening.current = true; setBusy(true); callbacks.current.onBusy(true); setMessage('Abrindo o Edge…');
    const current = () => mounted.current && token === generation.current;
    function receive(result: TargetPicking) {
      if (!current()) return;
      if (result.status === 'DONE' && result.target) {
        session.current = null; generation.current++; controller.current?.abort();
        callbacks.current.onPicked(result.target.selector);
        setBusy(false); callbacks.current.onBusy(false);
        setMessage('Alvo selecionado. Revise e aplique a correção.');
      } else if (result.status !== 'RECORDING') {
        stop(); setMessage(result.status === 'CANCELLED' ? 'Seleção cancelada. Sua edição foi preservada.' : 'Não foi possível selecionar o alvo. Revise a página ou corrija o seletor manualmente.');
      } else {
        setMessage(result.phase === 'PREPARING' ? 'No Edge, prepare a página da etapa e clique em Selecionar alvo.' : 'No Edge, clique no novo alvo da etapa.');
        timer.current = setTimeout(() => {void poll(result.id);}, 500);
      }
    }
    async function poll(id: string) {
      if (!current()) return;
      try {receive(await api.getTargetPicking(id, controller.current?.signal));}
      catch {if (current()) {stop(); setMessage('Não foi possível acompanhar a seleção. Sua edição foi preservada.');}}
    }
    try {
      const result = await api.startTargetPicking(url, kind);
      if (!current()) {void api.cancelTargetPicking(result.id).catch(() => {}); return;}
      opening.current = false; session.current = result.id; controller.current = new AbortController(); receive(result);
    } catch {if (current()) {stop(); setMessage('Não foi possível abrir a seleção. Verifique o endereço e a API.');}}
  }
  return <div className="visual-target-picker"><div className="button-row">
    <button type="button" className="secondary-button" disabled={busy || disabled} aria-label={`Selecionar no Edge · ${label}`} onClick={() => void start()}>Selecionar no Edge</button>
    {busy ? <button type="button" className="secondary-button" aria-label={`Cancelar seleção · ${label}`} onClick={() => {stop(); setMessage('Seleção cancelada. Sua edição foi preservada.');}}>Cancelar seleção</button> : null}
  </div>{message ? <p role="status" className="muted">{message}</p> : null}</div>;
}
