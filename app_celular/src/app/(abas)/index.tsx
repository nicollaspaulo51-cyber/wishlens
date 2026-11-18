import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Mapa } from '../../componentes/Mapa';
import { PainelDoDia } from '../../componentes/PainelDoDia';
import { FolhaAbas } from '../../componentes/SeletorAba';
import { Aviso, Botao } from '../../componentes/ui';
import { api, type Mapa as DadosMapa, type Tema } from '../../lib/api';
import { escurecerParaBranco, useCores } from '../../lib/cores';
import { NOME_LIVRE, useModo } from '../../lib/modo';
import { useContagem, useTransicao } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';
import { Icone, IconeTema } from '../../componentes/icones/Icone';

const KM_PARA_ATUALIZAR = 0.3;
const controleMapa = { width: 44, height: 44, borderRadius: 6, alignItems: 'center', justifyContent: 'center' } as const;

function Pontos({ valor }: { valor: number }) {
  const mostrado = useContagem(valor, 250);
  const anterior = useRef(valor);
  const [ganho, setGanho] = useState(0);
  useLayoutEffect(() => {
    const diferenca = valor - anterior.current;
    anterior.current = valor;
    setGanho(Math.max(0, diferenca));
    if (diferenca <= 0) return;
    const prazo = setTimeout(() => setGanho(0), 900);
    return () => clearTimeout(prazo);
  }, [valor]);
  return (
    <View className="flex-row items-center gap-1.5">
      <Text className="font-numero text-[18px] text-tinta">{mostrado}</Text>
      <Text className="font-numero text-[11px] text-apagado">PTS</Text>
      {ganho > 0 ? <GanhoPontos key={valor} ganho={ganho} /> : null}
    </View>
  );
}

function GanhoPontos({ ganho }: { ganho: number }) {
  const opacidade = useTransicao(1, 150, { inicial: 0 });
  return <Animated.View style={{ opacity: opacidade }}><Text className="font-numero text-[13px] text-agua">+{ganho}</Text></Animated.View>;
}

function distanciaKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180;
  const x = (b.lon - a.lon) * r * Math.cos(((a.lat + b.lat) / 2) * r);
  return Math.hypot(x, (b.lat - a.lat) * r) * 6371;
}

// Últimos lugares de cada aba no celular. Só valem perto de onde foram buscados (até 3 km).
type Guardados = { lat: number; lon: number; lugares: DadosMapa['lugares'] };
const chaveLugares = (modo: string) => `wl_lugares_${modo}`;

async function lerLugares(modo: string, aqui: { lat: number; lon: number }) {
  try {
    const g = JSON.parse((await AsyncStorage.getItem(chaveLugares(modo))) ?? 'null') as Guardados | null;
    return g && g.lugares?.length && distanciaKm(g, aqui) < 3 ? g.lugares : null;
  } catch {
    return null;
  }
}

function guardarLugares(modo: string, aqui: { lat: number; lon: number }, lugares: DadosMapa['lugares']) {
  AsyncStorage.setItem(chaveLugares(modo), JSON.stringify({ lat: aqui.lat, lon: aqui.lon, lugares })).catch(() => {});
}

export default function Jogar() {
  const c = useCores();
  const estado = useDados(api.estado, [], 30);
  const temas = useDados(api.temas);
  const [posicao, setPosicao] = useState<{ lat: number; lon: number } | null>(null);
  const [semGps, setSemGps] = useState<string | null>(null);
  const [mapa, setMapa] = useState<DadosMapa | null>(null);
  const [mostrar, setMostrar] = useState<string[] | null>(null);
  const ultimaBusca = useRef<{ lat: number; lon: number } | null>(null);
  const posAntes = useRef<number | null>(null);
  const [mudou, setMudou] = useState<string | null>(null);
  const prazoPosicao = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [hojeAberta, setHojeAberta] = useState(false);
  const [recentrar, setRecentrar] = useState(0);
  const modo = useModo();
  const modoAgora = useRef(modo);
  modoAgora.current = modo;
  const abas = [NOME_LIVRE, ...(temas.dados?.abas ?? [])];
  const aba = abas.find((item) => item.id === modo) ?? NOME_LIVRE;

  const porId = useMemo(() => Object.fromEntries([...(temas.dados?.temas ?? []), ...(temas.dados?.abas ?? [])].map((t) => [t.id, t])) as Record<string, Tema>,
    [temas.dados]);
  const doLivre = useMemo(() => (temas.dados?.temas ?? []).map((t) => t.id), [temas.dados]);
  const ativos = useMemo(() => (modo === 'livre' ? mostrar ?? doLivre : [modo]), [modo, mostrar, doLivre]);

  async function pedirGps() {
    setSemGps(null);
    const { granted } = await Location.requestForegroundPermissionsAsync();
    if (!granted) {
      setSemGps('Sem a localização o mapa não mostra os lugares perto de você, mas as fotos continuam valendo.');
      return null;
    }
    return Location.watchPositionAsync({ accuracy: Location.Accuracy.Balanced, distanceInterval: 20 }, (p) =>
      setPosicao({ lat: p.coords.latitude, lon: p.coords.longitude }));
  }

  useEffect(() => {
    let assinatura: Location.LocationSubscription | null = null;
    pedirGps().then((a) => { assinatura = a; }).catch(() => setSemGps('Não consegui ler o GPS agora.'));
    return () => assinatura?.remove();
  }, []);

  // Lugares e manchas: de novo só quando você andou mais de 300 m, ou em 20 s se o OpenStreetMap não respondeu
  const [tentativa, setTentativa] = useState(0);
  // Trocou de aba: o mapa mostra os lugares dela (busca de novo, sem esperar andar 300 m)
  useEffect(() => {
    ultimaBusca.current = null;
    setMapa(null);
  }, [modo]);
  useEffect(() => {
    if (!posicao || (ultimaBusca.current && distanciaKm(ultimaBusca.current, posicao) < KM_PARA_ATUALIZAR)) return;
    ultimaBusca.current = posicao;
    // Sem cancelar na troca de posição: o GPS muda a cada 20 m e a resposta ainda vale
    const deNovo = () => {
      ultimaBusca.current = null;
      setTimeout(() => setTentativa((n) => n + 1), 20000);
    };
    const pedida = modo;
    const aqui = posicao;
    // Os últimos ícones desta aba, guardados no celular: aparecem na hora e ficam se a busca falhar
    lerLugares(modo, aqui).then((guardados) => {
      if (guardados && pedida === modoAgora.current) setMapa((antes) => (antes?.lugares.length ? antes : { lugares: guardados, manchas: antes?.manchas ?? [] }));
    });
    api.mapa(posicao.lat, posicao.lon, modo)
      .then((m) => {
        if (pedida !== modoAgora.current) return; // resposta de outra aba, que chegou atrasada
        if (m.lugares.length) guardarLugares(pedida, aqui, m.lugares);
        // sem lugares na resposta (OpenStreetMap fora ou vazio): os ícones que já estão no mapa continuam
        setMapa((antes) => (!m.lugares.length && antes?.lugares.length ? { ...m, lugares: antes.lugares } : m));
        if (m.lugares_ok === false) deNovo();
      })
      .catch(deNovo);
  }, [posicao, tentativa, modo]);

  // Aviso quando a posição no pódio muda enquanto o placar se atualiza sozinho
  useEffect(() => {
    const agora = estado.dados?.posicao ?? null;
    if (posAntes.current && agora && agora !== posAntes.current) {
      setMudou(agora < posAntes.current ? `Você subiu para ${agora}º lugar hoje` : `Alguém passou você: agora ${agora}º lugar`);
      if (prazoPosicao.current !== null) clearTimeout(prazoPosicao.current);
      prazoPosicao.current = setTimeout(() => setMudou(null), 5000);
    }
    posAntes.current = agora;
  }, [estado.dados?.posicao]);
  useEffect(() => () => { if (prazoPosicao.current !== null) clearTimeout(prazoPosicao.current); }, []);

  const e = estado.dados;
  const pontosAba = e ? e.pontos_abas?.[modo] ?? (modo === 'livre' ? e.pontos_hoje : 0) : 0;
  const livre = modo === 'livre';
  const temaDoDia = livre ? e?.tema_do_dia ?? porId[temas.dados?.tema_do_dia ?? ''] : undefined;
  const assunto = temaDoDia ?? aba;
  const lugarPodio = e?.posicao ? `${e.posicao}º` : '—';
  return (
    <View className="flex-1 bg-suave">
      {/* O mapa ocupa a tela toda; o resto flutua por cima */}
      <View className="absolute top-[0px] left-[0px] right-[0px] bottom-[0px]">
        {posicao ? (
          <Mapa posicao={posicao} dados={mapa} temas={porId} mostrar={ativos} temaDoDia={temaDoDia?.id} recentrar={livre ? recentrar : undefined} />
        ) : (
          <View className="flex-1 justify-end p-[16px] pb-[48px] gap-[12px]">
            <Icone nome="bussola" tamanho={44} cor={c.agua} />
            <Text className="font-texto text-tinta text-[16px] leading-[22px]" >{semGps ?? 'Procurando você no mapa...'}</Text>
            {semGps ? <Botao titulo="Ligar a localização" tipo="localizacao" aoTocar={pedirGps} /> : null}
          </View>
        )}
      </View>

      <SafeAreaView edges={['top']} pointerEvents="box-none" style={[StyleSheet.absoluteFill, { paddingHorizontal: 12, paddingTop: 8 }]}>
        <Pressable accessibilityRole="button" accessibilityState={{ expanded: hojeAberta }}
          accessibilityLabel={`${temaDoDia ? `Tema de hoje: ${assunto.nome}, vale o dobro` : `Aba: ${assunto.nome}`}. ${pontosAba} pontos nesta aba. ${e?.posicao ? `${lugarPodio} lugar no pódio geral` : 'Sem posição no pódio'}. Abrir Hoje`}
          onPress={() => setHojeAberta(true)}
          style={{ minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 12,
            backgroundColor: `${c.superficie}EB`, borderWidth: 1, borderColor: c.linha, borderRadius: 6 }}>
          <View className="flex-1 flex-row items-center gap-[6px]">
            <IconeTema id={assunto.id} tamanho={18} cor={temaDoDia ? c.destaque : c.tinta} />
            <Text numberOfLines={1} className="shrink font-texto-forte text-tinta">{assunto.nome}</Text>
            {temaDoDia ? <Text className="font-numero text-destaque">×2</Text> : null}
          </View>
          <View className="w-[1px] h-[18px] bg-linha" />
          <Pontos key={modo} valor={pontosAba} />
          <View className="w-[1px] h-[18px] bg-linha" />
          <Text className="font-numero text-[18px] text-tinta">{lugarPodio}</Text>
        </Pressable>
        <View pointerEvents="box-none" className="flex-1">
          {mudou ? (
            <View pointerEvents="none" className="absolute top-[4px] left-0 right-0 items-center rounded-[6px] border border-linha bg-ficha py-[3px]">
              <Text className="font-texto-forte text-[13px] text-tinta" accessibilityLiveRegion="polite">{mudou}</Text>
            </View>
          ) : null}
          {estado.erro && !e ? <Aviso texto={estado.erro} aoTentar={estado.recarregar} /> : null}
          {posicao && livre ? (
            // style e não className: a coluna precisa ficar colada à direita (com classes ela caiu na esquerda no Android)
            <View pointerEvents="box-none" style={{ position: 'absolute', right: 0, top: 0, bottom: 0, justifyContent: 'center', alignItems: 'flex-end', gap: 8 }}>
              {temas.dados?.temas.map((t) => {
                const ligado = ativos.includes(t.id);
                const cor = escurecerParaBranco(t.cor);
                return (
                  <Pressable key={t.id} accessibilityRole="checkbox" accessibilityState={{ checked: ligado }}
                    accessibilityLabel={`Mostrar ${t.nome} no mapa`}
                    onPress={() => setMostrar(ligado ? ativos.filter((id) => id !== t.id) : [...ativos, t.id])}
                    style={{ ...controleMapa, backgroundColor: ligado ? cor : c.superficie, borderWidth: 2, borderColor: ligado ? cor : t.cor }}>
                    <IconeTema id={t.id} tamanho={22} cor={ligado ? '#FFFFFF' : t.cor} />
                  </Pressable>
                );
              })}
              <Pressable accessibilityRole="button" accessibilityLabel="Recentrar em você" onPress={() => setRecentrar((vez) => vez + 1)}
                style={{ ...controleMapa, marginTop: 4, backgroundColor: c.superficie, borderWidth: 1, borderColor: c.linha }}>
                <Icone nome="mira" tamanho={22} cor={c.agua} />
              </Pressable>
            </View>
          ) : null}
        </View>
      </SafeAreaView>
      <FolhaAbas aberta={hojeAberta} fechar={() => setHojeAberta(false)} abas={abas} modo={modo} pontos={e?.pontos_abas} titulo="Hoje">
        {e ? <PainelDoDia estado={e} /> : null}
      </FolhaAbas>
    </View>
  );
}
