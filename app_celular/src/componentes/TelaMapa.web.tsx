// Web (prévia no computador): a mesma página do mapa num iframe.
import { createElement, forwardRef, useEffect, useImperativeHandle, useRef } from 'react';

import { MAPA_HTML } from '../lib/mapaHtml';
import type { TelaMapaRef } from './TelaMapa';

export type { TelaMapaRef };
type Props = { aoReceber: (mensagem: { tipo: string } & Record<string, unknown>) => void; rotulo: string };
type JanelaMapa = Window & { receber: (m: object) => void; iniciar: (lat: number, lon: number, escuro: boolean) => void };

export const TelaMapa = forwardRef<TelaMapaRef, Props>(function TelaMapa({ aoReceber, rotulo }, ref) {
  const quadro = useRef<HTMLIFrameElement>(null);
  const janela = () => quadro.current?.contentWindow as JanelaMapa | null | undefined;
  useImperativeHandle(ref, () => ({
    mandar: (m) => janela()?.receber(m),
    iniciar: (lat, lon, escuro) => janela()?.iniciar(lat, lon, escuro),
  }));
  useEffect(() => {
    const ouvir = (evento: MessageEvent) => {
      if (evento.source !== janela() || typeof evento.data !== 'string') return;
      try { aoReceber(JSON.parse(evento.data)); } catch { /* mensagem que não é nossa */ }
    };
    window.addEventListener('message', ouvir);
    return () => window.removeEventListener('message', ouvir);
  }, [aoReceber]);
  return createElement('iframe', { ref: quadro, srcDoc: MAPA_HTML, title: rotulo,
    style: { border: 0, width: '100%', height: '100%', display: 'block' } });
});
