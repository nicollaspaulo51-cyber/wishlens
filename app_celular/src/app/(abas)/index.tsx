// Jogar: placar e tema do dia em cima, o mapa no meio e o botão Fotografar sempre à mão, embaixo.
import * as Location from 'expo-location';
import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Mapa } from '../../componentes/Mapa';
import { PainelDoDia } from '../../componentes/PainelDoDia';
import { Apagado, Aviso, Botao, Titulo } from '../../componentes/ui';
import { api, type Mapa as DadosMapa, type Tema } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useDados } from '../../lib/useDados';

const KM_PARA_ATUALIZAR = 0.3;

function distanciaKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180;
  const x = (b.lon - a.lon) * r * Math.cos(((a.lat + b.lat) / 2) * r);
  return Math.hypot(x, (b.lat - a.lat) * r) * 6371;
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

  const porId = useMemo(() => Object.fromEntries((temas.dados?.temas ?? []).map((t) => [t.id, t])) as Record<string, Tema>, [temas.dados]);
  const ativos = mostrar ?? Object.keys(porId);

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

  // Lugares e manchas: de novo só quando você andou mais de 300 m
  useEffect(() => {
    if (!posicao || (ultimaBusca.current && distanciaKm(ultimaBusca.current, posicao) < KM_PARA_ATUALIZAR)) return;
    ultimaBusca.current = posicao;
    api.mapa(posicao.lat, posicao.lon).then(setMapa).catch(() => { ultimaBusca.current = null; });
  }, [posicao]);

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
  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8, gap: 10 }}>
        <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <Titulo tamanho={26}>WishLens</Titulo>
          {e ? (
            <Text accessibilityLabel={`${e.pontos_hoje} pontos hoje, ${e.posicao ? `${e.posicao}º lugar` : 'sem posição ainda'}`}
              style={{ color: c.tinta, fontSize: 15 }}>
              <Text style={{ fontFamily: FONTE_TITULO, fontSize: 20 }}>{e.pontos_hoje}</Text> pts · {e.posicao ? `${e.posicao}º` : '—'}
            </Text>
          ) : null}
        </View>
        {estado.erro && !e ? <Aviso texto={estado.erro} aoTentar={estado.recarregar} /> : null}
        {e ? (
          <>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: c.sol, borderRadius: 12, padding: 12 }}>
              <Text style={{ fontSize: 26 }} accessibilityElementsHidden>{e.tema_do_dia.emoji}</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: c.solTinta, fontSize: 13 }}>Tema do dia: vale o dobro</Text>
                <Text style={{ color: c.solTinta, fontFamily: FONTE_TITULO, fontSize: 19 }}>{e.tema_do_dia.nome}</Text>
              </View>
              <Text style={{ fontFamily: FONTE_TITULO, fontSize: 20, color: c.solTinta }}>×2</Text>
            </View>
            <PainelDoDia estado={e} />
          </>
        ) : null}
        {mudou ? <Text accessibilityLiveRegion="polite" style={{ color: c.destaque, fontWeight: '700' }}>{mudou}</Text> : null}
      </View>

      <View style={{ flex: 1, marginTop: 10, overflow: 'hidden' }}>
        {posicao ? (
          <Mapa posicao={posicao} dados={mapa} temas={porId} mostrar={ativos} />
        ) : (
          <View style={{ flex: 1, padding: 16, gap: 12, backgroundColor: c.suave }}>
            <Apagado>{semGps ?? 'Procurando você no mapa...'}</Apagado>
            {semGps ? <Botao titulo="Ligar a localização" tipo="secundario" aoTocar={pedirGps} /> : null}
          </View>
        )}
        {posicao && temas.dados ? (
          <View style={{ position: 'absolute', top: 8, left: 8, right: 8, flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}
            accessibilityLabel="Mostrar no mapa">
            {temas.dados.temas.map((t) => {
              const ligado = ativos.includes(t.id);
              return (
                <Pressable key={t.id} accessibilityRole="checkbox" accessibilityState={{ checked: ligado }}
                  accessibilityLabel={`Mostrar ${t.nome} no mapa`}
                  onPress={() => setMostrar(ligado ? ativos.filter((x) => x !== t.id) : [...ativos, t.id])}
                  style={{ minWidth: 44, minHeight: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center',
                    backgroundColor: ligado ? c.superficie : 'rgba(255,255,255,0.55)', borderWidth: 2, borderColor: ligado ? t.cor : 'transparent' }}>
                  <Text style={{ fontSize: 20, opacity: ligado ? 1 : 0.4 }}>{t.emoji}</Text>
                </Pressable>
              );
            })}
          </View>
        ) : null}
        <View style={{ position: 'absolute', left: 16, right: 16, bottom: 16 }}>
          <Botao titulo="📷  Fotografar" aoTocar={() => router.push('/camera')} estilo={{ minHeight: 60, borderRadius: 30,
            shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 6 }} rotulo="Fotografar" />
        </View>
      </View>
    </SafeAreaView>
  );
}
