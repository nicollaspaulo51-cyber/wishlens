// Mapa do jogo: você, os lugares de cada tema e as manchas da turma.
// Só software livre: MapLibre GL JS + OpenFreeMap (dados do OpenStreetMap), desenhado por TelaMapa
// (WebView no celular, iframe na web). Aqui ficam as decisões: grupos, quem pulsa, cores e balões.
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';

import type { Mapa as DadosMapa, Lugar, Tema } from '../lib/api';
import { agrupar, checarAgrupar, type Regiao } from '../lib/agrupar';
import { escurecerParaBranco, PALETA, useCores } from '../lib/cores';
import { useMovimentoReduzido } from '../lib/movimento';
import { TelaMapa, type TelaMapaRef } from './TelaMapa';

if (__DEV__) checarAgrupar();

export type PropsMapa = {
  posicao: { lat: number; lon: number };
  dados: DadosMapa | null;
  temas: Record<string, Tema>;
  mostrar: string[];
  temaDoDia?: string;
  recentrar?: number;
};

const PULSAM = 20;
const ATRASOS = [0, 530, 1060]; // três ritmos defasados: os pulsos não acontecem todos juntos

export const Mapa = memo(function Mapa({ posicao, dados, temas, mostrar, temaDoDia, recentrar }: PropsMapa) {
  const c = useCores();
  const escuro = c === PALETA.escuro;
  const reduzido = useMovimentoReduzido();
  const tela = useRef<TelaMapaRef>(null);
  const [pronto, setPronto] = useState(false);
  const [regiao, setRegiao] = useState<Regiao & { largura: number } | null>(null);
  const lugares = useMemo(() => (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)), [dados?.lugares, mostrar]);
  const manchas = useMemo(() => (dados?.manchas ?? []).filter((m) => mostrar.includes(m.tema)), [dados?.manchas, mostrar]);

  const inicio = useRef({ ...posicao, escuro });
  const aoReceber = useCallback((m: { tipo: string } & Record<string, unknown>) => {
    if (m.tipo === 'carregou') tela.current?.iniciar(inicio.current.lat, inicio.current.lon, inicio.current.escuro);
    else if (m.tipo === 'pronto') setPronto(true);
    else if (m.tipo === 'regiao') setRegiao(m as unknown as Regiao & { largura: number });
  }, []);

  // Recentrar na sua posição quando o botão da mira pede
  const pedidoAnterior = useRef(recentrar ?? 0);
  useEffect(() => {
    if (!pronto || recentrar === undefined || recentrar === pedidoAnterior.current) return;
    tela.current?.mandar({ tipo: 'ir', lat: posicao.lat, lon: posicao.lon });
    pedidoAnterior.current = recentrar;
  }, [recentrar, pronto, posicao]);

  // Nas abas os lugares podem estar a 5 ou 10 km: se nenhum aparece na tela, afasta até mostrar os 3 mais perto
  const chaveLugares = lugares.map((l) => l.mapa).join();
  const naTela = useCallback((l: Lugar) => !!regiao && Math.abs(l.lat - regiao.latitude) <= regiao.latitudeDelta / 2
    && Math.abs(l.lon - regiao.longitude) <= regiao.longitudeDelta / 2, [regiao]);
  const enquadrado = useRef('');
  useEffect(() => {
    if (!pronto || !regiao || !lugares.length || enquadrado.current === chaveLugares) return;
    enquadrado.current = chaveLugares;
    if (lugares.some(naTela)) return;
    const perto = [...lugares].sort((a, b) => a.distancia_km - b.distancia_km).slice(0, 3);
    tela.current?.mandar({ tipo: 'enquadrar', pontos: [posicao, ...perto.map((l) => ({ lat: l.lat, lon: l.lon }))] });
  }, [pronto, regiao, chaveLugares, lugares, naTela, posicao]);

  const itens = useMemo(() => regiao ? agrupar(lugares, regiao, regiao.largura) : lugares.map((lugar) => ({ tipo: 'lugar' as const, lugar })),
    [lugares, regiao]);

  // Pulsam os lugares soltos que estão na tela (até PULSAM, os mais perto de você), cada um na cor do seu tema
  const pulsam = useMemo(() => {
    if (reduzido !== false || !regiao) return new Set<string>();
    const escalaLon = Math.cos(posicao.lat * Math.PI / 180);
    const distancia = (l: Lugar) => Math.hypot(l.lat - posicao.lat, (l.lon - posicao.lon) * escalaLon);
    const soltos = itens.flatMap((item) => item.tipo === 'lugar' && naTela(item.lugar) ? [item.lugar] : []);
    return new Set(soltos.sort((a, b) => distancia(a) - distancia(b)).slice(0, PULSAM).map((l) => l.mapa));
  }, [itens, regiao, naTela, posicao, reduzido]);

  useEffect(() => {
    if (!pronto) return;
    const marcas = itens.map((item) => {
      if (item.tipo === 'grupo') {
        return { tipo: 'grupo', chave: `grupo-${item.lugares[0].mapa}`, lat: item.lat, lon: item.lon, quantos: item.quantos,
          cor: escurecerParaBranco(temas[item.tema]?.cor ?? c.agua, 4.5) };
      }
      const { lugar } = item;
      const tema = temas[lugar.tema];
      const cor = escurecerParaBranco(tema?.cor ?? c.agua);
      // o pulso tem a cor do próprio tema; o tema do dia se destaca só por pulsar mais forte
      return { tipo: 'lugar', chave: lugar.mapa, lat: lugar.lat, lon: lugar.lon, cor, corPulso: cor, emoji: tema?.emoji ?? '📍',
        titulo: lugar.nome, distancia: lugar.distancia_km, linha: tema ? `procure ${tema.nome.toLowerCase()}` : '',
        pulsa: pulsam.has(lugar.mapa), forte: lugar.tema === temaDoDia,
        atraso: ATRASOS[(Number.parseInt(lugar.mapa.slice(-2), 36) || 0) % ATRASOS.length] };
    });
    const guardioes = manchas.filter((m) => m.guardiao).map((m) => ({ tipo: 'guardiao', chave: `g-${m.celula}-${m.tema}`,
      lat: m.lat, lon: m.lon, linha: m.guardiao }));
    tela.current?.mandar({
      tipo: 'desenhar', escuro, lat: posicao.lat,
      cores: { tinta: c.tinta, apagado: c.apagado, agua: c.agua, aguaTinta: c.aguaTinta, superficie: c.superficie, linha: c.linha, ficha: c.suave },
      itens: [{ tipo: 'voce', chave: 'voce', lat: posicao.lat, lon: posicao.lon }, ...guardioes, ...marcas],
      manchas: manchas.map((m) => ({ lat: m.lat, lon: m.lon, preenche: m.guardiao ? `${c.destaque}40` : `${c.apagado}26`,
        borda: m.guardiao ? c.destaque : c.apagado })),
    });
  }, [pronto, itens, pulsam, manchas, temas, temaDoDia, posicao, c, escuro]);

  return (
    <View style={{ flex: 1 }}>
      <TelaMapa ref={tela} aoReceber={aoReceber} rotulo={`Mapa com ${lugares.length} lugares para procurar perto de você`} />
    </View>
  );
});
