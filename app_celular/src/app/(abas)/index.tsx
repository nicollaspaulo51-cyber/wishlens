// Jogar: placar e tema do dia em cima, o mapa no meio e o botão Fotografar sempre à mão, embaixo.
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Mapa } from '../../componentes/Mapa';
import { PainelDoDia } from '../../componentes/PainelDoDia';
import { Topografia } from '../../componentes/efeitos/Topografia';
import { SeletorAba } from '../../componentes/SeletorAba';
import { Aviso, Botao } from '../../componentes/ui';
import { api, type Mapa as DadosMapa, type Tema } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useModo } from '../../lib/modo';
import { Surge, useContagem, useTransicao } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';
import { Icone, IconeTema } from '../../componentes/icones/Icone';

const KM_PARA_ATUALIZAR = 0.3;

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
      <Text className="font-numero text-[20px] text-tinta">
        {mostrado}<Text className="font-texto text-[13px] text-apagado"> pts</Text>
      </Text>
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
  const modo = useModo();
  const modoAgora = useRef(modo);
  modoAgora.current = modo;
  const aba = temas.dados?.abas?.find((a) => a.id === modo);
  // A explicação da aba aparece por 4 s quando você troca de aba (a completa fica no seletor)
  const [dica, setDica] = useState(false);
  const primeira = useRef(true);
  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }
    setDica(true);
    const t = setTimeout(() => setDica(false), 4000);
    return () => clearTimeout(t);
  }, [modo]);

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
      setTimeout(() => setMudou(null), 5000);
    }
    posAntes.current = agora;
  }, [estado.dados?.posicao]);

  const e = estado.dados;
  const pontosAba = e ? e.pontos_abas?.[modo] ?? (modo === 'livre' ? e.pontos_hoje : 0) : 0;
  return (
    <View className="flex-1 bg-suave">
      {/* O mapa ocupa a tela toda; o resto flutua por cima */}
      <View className="absolute top-[0px] left-[0px] right-[0px] bottom-[0px]">
        {posicao ? (
          <Mapa posicao={posicao} dados={mapa} temas={porId} mostrar={ativos} temaDoDia={modo === 'livre' ? e?.tema_do_dia.id : undefined} />
        ) : (
          <View className="flex-1 justify-end p-[16px] pb-[48px] gap-[12px]">
            <Icone nome="bussola" tamanho={44} cor={c.agua} />
            <Text className="font-texto text-tinta text-[16px] leading-[22px]" >{semGps ?? 'Procurando você no mapa...'}</Text>
            {semGps ? <Botao titulo="Ligar a localização" tipo="localizacao" aoTocar={pedirGps} /> : null}
          </View>
        )}
      </View>

      <SafeAreaView edges={['top']} pointerEvents="box-none" className="px-[12px] pt-[8px] gap-[8px]">
        <View className="flex-row flex-wrap gap-2 justify-between items-center overflow-hidden" pointerEvents="box-none">
          <Topografia />
          <View style={{ backgroundColor: c.superficie, borderRadius: 6, borderWidth: 1, borderColor: c.linha, paddingHorizontal: 14, paddingVertical: 6 }}>
            <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 20, color: c.tinta, letterSpacing: -0.5 }}>WishLens</Text>
          </View>
          {e ? (
            <View accessible accessibilityLabel={`${pontosAba} pontos hoje nesta aba${modo === 'livre' ? `, ${e.posicao ? `${e.posicao}º lugar` : 'sem posição ainda'}` : ''}`}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: c.superficie, borderRadius: 6, borderWidth: 1, borderColor: c.linha, paddingHorizontal: 14, paddingVertical: 6 }}>
              <Pontos key={modo} valor={pontosAba} />
              {modo === 'livre' ? (
                <>
                  <View className="w-[1px] h-[18px] bg-linha" />
                  <Icone nome="trofeu" tamanho={15} cor={c.destaque} />
                  <Text className="font-numero text-[18px] text-tinta">{e.posicao ? `${e.posicao}º` : '—'}</Text>
                </>
              ) : null}
            </View>
          ) : null}
        </View>
        <SeletorAba pontos={e?.pontos_abas} />
        {estado.erro && !e ? <Aviso texto={estado.erro} aoTentar={estado.recarregar} /> : null}
        {aba && dica ? (
          <Surge chave={aba.id} estilo={{ backgroundColor: c.superficie, borderRadius: 6, padding: 12, gap: 8, flexDirection: 'row', alignItems: 'center',
            borderWidth: 1, borderColor: c.linha }}>
            <IconeTema id={aba.id} cor={c.tinta} tamanho={20} />
            <Text className="flex-1 font-texto text-tinta text-[14px] leading-[19px]" accessibilityLiveRegion="polite" >
              <Text className="font-texto-forte" >{aba.nome}:</Text> vale {aba.conta}.
            </Text>
          </Surge>
        ) : null}
        {e && modo === 'livre' ? (
          <>
            <Surge ordem={1}>
              <View className="flex-row items-center gap-[10px] bg-ficha border border-linha rounded-ficha px-[12px] py-[8px] overflow-hidden">
                <IconeTema id={e.tema_do_dia.id} tamanho={32} cor={c.tinta} />
                <View className="flex-1">
                  <Text className="font-texto-forte text-apagado text-[12px]" >Tema de hoje</Text>
                  <Text className="text-tinta font-titulo text-[19px] leading-[22px]">{e.tema_do_dia.nome}</Text>
                </View>
                <Text accessibilityLabel="vale o dobro" className="font-numero text-[26px] text-destaque">×2</Text>
              </View>
            </Surge>
            <Surge ordem={2}><PainelDoDia estado={e} /></Surge>
          </>
        ) : null}
        {mudou ? (
          <Surge chave={mudou} estilo={{ alignSelf: 'center', backgroundColor: c.superficie, borderRadius: 6, borderWidth: 1, borderColor: c.linha, paddingHorizontal: 14, paddingVertical: 8 }}>
            <Text className="font-texto-forte text-tinta" accessibilityLiveRegion="polite" >{mudou}</Text>
          </Surge>
        ) : null}
      </SafeAreaView>

      {posicao && temas.dados && modo === 'livre' ? (
        <View className="absolute left-[12px] right-[12px] bottom-[40px] flex-row flex-wrap gap-[6px]"
          accessibilityLabel="Mostrar no mapa" pointerEvents="box-none">
          {temas.dados.temas.map((t) => {
            const ligado = ativos.includes(t.id);
            return (
              <Pressable key={t.id} accessibilityRole="checkbox" accessibilityState={{ checked: ligado }}
                accessibilityLabel={`Mostrar ${t.nome} no mapa`}
                onPress={() => setMostrar(ligado ? ativos.filter((x) => x !== t.id) : [...ativos, t.id])}
                style={{ width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center',
                  backgroundColor: c.superficie, borderWidth: 1, borderColor: c.linha, opacity: ligado ? 1 : 0.6 }}>
                <View style={{ opacity: ligado ? 1 : 0.4 }}><IconeTema id={t.id} tamanho={22} cor={ligado ? c.tinta : c.apagado} /></View>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}
