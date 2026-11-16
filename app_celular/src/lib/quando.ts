// "agora", "há 5 min", "há 2 h", "ontem", "12/11": a hora das mensagens do chat.
// Diferença entre o relógio do juiz (cabeçalho X-Agora) e o do celular: as mensagens têm a hora do juiz.
let desvio = 0;
export function acertarRelogio(agoraDoJuiz: number) {
  if (Number.isFinite(agoraDoJuiz)) desvio = agoraDoJuiz - Date.now();
}

export function quandoFoi(iso: string, agora = Date.now() + desvio): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const min = Math.floor((agora - t) / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `há ${min} min`;
  const horas = Math.floor(min / 60);
  if (horas < 24) return `há ${horas} h`;
  if (horas < 48) return 'ontem';
  const d = new Date(t);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
}
