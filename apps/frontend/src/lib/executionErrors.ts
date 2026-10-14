import {downloadErrorMessage} from './downloadGeneration';
export function executionErrorMessage(code:string|null):string {
  const messages:Record<string,string>={
    QUERY_BASELINE_UNAVAILABLE:'Não foi possível identificar a confirmação e o resultado anteriores à consulta.',
    QUERY_IDENTITY_INVALID:'O site não apresentou uma identificação válida da consulta.',
    QUERY_CONFIRMATION_TIMEOUT:'Uma nova consulta não foi confirmada no prazo. A ação não será repetida automaticamente.',
    QUERY_RESULT_TIMEOUT:'O resultado desta consulta não ficou disponível no prazo.',
    QUERY_CONTEXT_MISMATCH:'A página ou o contexto mudou durante a consulta.',
    QUERY_SUPERSEDED:'Outra consulta substituiu a solicitação atual. A execução foi interrompida.',
    QUERY_OUTCOME_AMBIGUOUS:'Os sinais de conclusão da consulta são ambíguos. Revise os estados configurados.',
    QUERY_NO_DATA:'Consulta concluída sem dados; etapas seguintes não executadas.',
    QUERY_SITE_ERROR:'O site informou um erro na consulta; etapas seguintes não executadas.',
    QUERY_AUTHORIZATION_REVOKED:'O acesso foi interrompido enquanto o resultado da consulta era aguardado.',
    QUERY_EXECUTION_FAILED:'Não foi possível verificar o resultado da consulta. Revise a configuração.',
  };
  return messages[code??'']??downloadErrorMessage(code);
}
