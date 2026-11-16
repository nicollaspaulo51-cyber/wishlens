// Jogar: placar e tema do dia em cima, o mapa no meio e o botão Fotografar sempre à mão, embaixo.
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Mapa } from '../../componentes/Mapa';
import { PainelDoDia } from '../../componentes/PainelDoDia';
import { Aviso, Botao } from '../../componentes/ui';
import { api, type Mapa as DadosMapa, type Tema } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { Brilho, Surge, useContagem, useEntrada } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';

const KM_PARA_ATUALIZAR = 0.3;

// Os pontos contam até o valor novo e dão um pulo quando mudam
function Pontos({ valor }: { valor: number }) {
  const c = useCores();
  const mostrado = useContagem(valor);
  const pulo = useEntrada(0, valor);
  return (
    <Animated.Text style={{ fontFamily: FONTE_TITULO, fontSize: 20, color: c.tinta,
      transform: [{ scale: pulo.interpolate({ inputRange: [0, 0.5, 1], outputRange: [1, 1.25, 1], extrapolate: 'clamp' }) }] }}>
      {mostrado}<Text style={{ fontSize: 13, color: c.apagado }}> pts</Text>
    </Animated.Text>
  );
}

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
  const sombra = { shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 5 };
  return (
    <View style={{ flex: 1, backgroundColor: c.suave }}>
      {/* O mapa ocupa a tela toda; o resto flutua por cima */}
      <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
        {posicao ? (
          <Mapa posicao={posicao} dados={mapa} temas={porId} mostrar={ativos} />
        ) : (
          <View style={{ flex: 1, justifyContent: 'flex-end', padding: 16, paddingBottom: 48, gap: 12 }}>
            <Ionicons name="navigate-circle-outline" size={44} color={c.destaque} />
            <Text style={{ color: c.tinta, fontSize: 16, lineHeight: 22 }}>{semGps ?? 'Procurando você no mapa...'}</Text>
            {semGps ? <Botao titulo="Ligar a localização" tipo="secundario" aoTocar={pedirGps} /> : null}
          </View>
        )}
      </View>

      <SafeAreaView edges={['top']} pointerEvents="box-none" style={{ paddingHorizontal: 12, paddingTop: 8, gap: 8 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }} pointerEvents="box-none">
          <View style={[{ backgroundColor: c.superficie, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 6 }, sombra]}>
            <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 20, color: c.tinta, letterSpacing: -0.5 }}>WishLens</Text>
          </View>
          {e ? (
            <View accessible accessibilityLabel={`${e.pontos_hoje} pontos hoje, ${e.posicao ? `${e.posicao}º lugar` : 'sem posição ainda'}`}
              style={[{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: c.superficie, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 6 }, sombra]}>
              <Pontos valor={e.pontos_hoje} />
              <View style={{ width: 1, height: 18, backgroundColor: c.linha }} />
              <Ionicons name="trophy" size={15} color={c.destaque} />
              <Text style={{ fontFamily: FONTE_TITULO, fontSize: 18, color: c.tinta }}>{e.posicao ? `${e.posicao}º` : '—'}</Text>
            </View>
          ) : null}
        </View>
        {estado.erro && !e ? <Aviso texto={estado.erro} aoTentar={estado.recarregar} /> : null}
        {e ? (
          <>
            {/* O tema do dia é a figurinha holográfica: borda branca, um leve giro e o brilho que passa */}
            <Surge ordem={1}>
              <View style={[{ borderRadius: 12, borderWidth: 4, borderColor: '#FFFFFF', transform: [{ rotate: '-1.2deg' }] }, sombra]}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: c.sol, borderRadius: 8,
                  paddingHorizontal: 12, paddingVertical: 8, overflow: 'hidden' }}>
                  <Text style={{ fontSize: 30 }} accessibilityElementsHidden>{e.tema_do_dia.emoji}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: c.solTinta, fontSize: 12, fontWeight: '600' }}>Tema de hoje</Text>
                    <Text style={{ color: c.solTinta, fontFamily: FONTE_TITULO, fontSize: 19, lineHeight: 22 }}>{e.tema_do_dia.nome}</Text>
                  </View>
                  <Text accessibilityLabel="vale o dobro" style={{ fontFamily: FONTE_TITULO, fontSize: 26, color: c.solTinta }}>×2</Text>
                  <Brilho />
                </View>
              </View>
            </Surge>
            <Surge ordem={2} estilo={sombra}><PainelDoDia estado={e} /></Surge>
          </>
        ) : null}
        {mudou ? (
          <Surge chave={mudou} estilo={[{ alignSelf: 'center', backgroundColor: c.tinta, borderRadius: 16, paddingHorizontal: 14, paddingVertical: 8 }, sombra]}>
            <Text accessibilityLiveRegion="polite" style={{ color: c.fundo, fontWeight: '700' }}>{mudou}</Text>
          </Surge>
        ) : null}
      </SafeAreaView>

      {posicao && temas.dados ? (
        <View style={{ position: 'absolute', left: 12, right: 12, bottom: 40, flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}
          accessibilityLabel="Mostrar no mapa" pointerEvents="box-none">
          {temas.dados.temas.map((t) => {
            const ligado = ativos.includes(t.id);
            return (
              <Pressable key={t.id} accessibilityRole="checkbox" accessibilityState={{ checked: ligado }}
                accessibilityLabel={`Mostrar ${t.nome} no mapa`}
                onPress={() => setMostrar(ligado ? ativos.filter((x) => x !== t.id) : [...ativos, t.id])}
                style={[{ width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center',
                  backgroundColor: c.superficie, borderWidth: 3, borderColor: ligado ? t.cor : c.linha, opacity: ligado ? 1 : 0.6 }, sombra]}>
                <Text style={{ fontSize: 20, opacity: ligado ? 1 : 0.4 }}>{t.emoji}</Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}
