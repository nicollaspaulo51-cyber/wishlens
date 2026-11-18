// Mapa nativo do celular (Google no Android, Apple no iPhone): você, os lugares de cada tema e as manchas da turma.
// Os blocos do tile.openstreetmap.org bloqueiam apps sem identificação ("Access blocked"), por isso o mapa do sistema.
// shortcut: no Expo Go o Google Maps já vem com chave; num APK próprio, pôr a chave em app.json (android.config.googleMaps).
import { memo, useEffect, useEffectEvent, useMemo, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import MapView, { Callout, Circle, Marker, type MapStyleElement, type Region } from 'react-native-maps';

import type { Mapa as DadosMapa, Lugar, Tema } from '../lib/api';
import { agrupar, checarAgrupar } from '../lib/agrupar';
import { escurecerParaBranco, FONTE_NUMERO, FONTE_TEXTO, FONTE_TEXTO_FORTE, PALETA, useCores, type Cores } from '../lib/cores';
import { useMovimentoReduzido } from '../lib/movimento';
import { Icone, IconeTema } from './icones/Icone';

if (__DEV__) checarAgrupar();

function estiloMapa(escuro: boolean): MapStyleElement[] {
  const fundo = escuro ? '#141A1F' : '#EEF1EF';
  return [
    { elementType: 'geometry', stylers: [{ color: fundo }] },
    { elementType: 'labels.text.fill', stylers: [{ color: escuro ? '#8A97A3' : '#5B6670' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: fundo }] },
    { featureType: 'road', elementType: 'geometry.fill', stylers: [{ color: escuro ? '#2A3540' : '#FFFFFF' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: escuro ? '#1A2229' : '#FFFFFF' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: escuro ? '#0E2433' : '#BFD9E6' }] },
    { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: escuro ? '#16261E' : '#DCE9DF' }] },
    { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
    // ícones de igreja, escola, árvore etc. do Google competiam com os marcadores do jogo
    { featureType: 'poi', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  ];
}

const ESTILO_ESCURO = estiloMapa(true);
const ESTILO_CLARO = estiloMapa(false);
const CENTRO = { x: 0.5, y: 0.5 };

export type PropsMapa = {
  posicao: { lat: number; lon: number };
  dados: DadosMapa | null;
  temas: Record<string, Tema>;
  mostrar: string[];
  temaDoDia?: string;
  recentrar?: number;
};

export const Mapa = memo(function Mapa({ posicao, dados, temas, mostrar, temaDoDia, recentrar }: PropsMapa) {
  const c = useCores();
  const escuro = c === PALETA.escuro;
  const lugares = useMemo(() => (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)), [dados?.lugares, mostrar]);
  const manchas = (dados?.manchas ?? []).filter((m) => mostrar.includes(m.tema));
  const [regiao, setRegiao] = useState<Region>(() => ({ latitude: posicao.lat, longitude: posicao.lon, latitudeDelta: 0.02, longitudeDelta: 0.02 }));
  const [largura, setLargura] = useState(0);
  const mapa = useRef<MapView>(null);
  const pedidoAnterior = useRef(recentrar ?? 0);
  const recentrarNaPosicao = useEffectEvent(() => {
    mapa.current?.animateToRegion({ ...regiao, latitude: posicao.lat, longitude: posicao.lon });
  });
  useEffect(() => {
    if (recentrar === undefined || recentrar === pedidoAnterior.current) return;
    recentrarNaPosicao();
    pedidoAnterior.current = recentrar;
  }, [recentrar]);
  // Nas abas os lugares podem estar a 5 ou 10 km: se nenhum aparece na tela, afasta até mostrar os 3 mais perto
  const chaveLugares = lugares.map((l) => l.mapa).join();
  const enquadrarLugares = useEffectEvent(() => {
    if (!lugares.length || lugares.some((l) => Math.abs(l.lat - regiao.latitude) <= regiao.latitudeDelta / 2
      && Math.abs(l.lon - regiao.longitude) <= regiao.longitudeDelta / 2)) return;
    const perto = [...lugares].sort((a, b) => a.distancia_km - b.distancia_km).slice(0, 3);
    mapa.current?.fitToCoordinates([{ latitude: posicao.lat, longitude: posicao.lon }, ...perto.map((l) => ({ latitude: l.lat, longitude: l.lon }))],
      { edgePadding: { top: 72, right: 68, bottom: 48, left: 48 }, animated: true });
  });
  useEffect(() => { enquadrarLugares(); }, [chaveLugares]);
  return (
    <View style={{ flex: 1 }} onLayout={(evento) => setLargura(evento.nativeEvent.layout.width)}>
      <MapView
        ref={mapa}
        style={{ flex: 1 }}
        initialRegion={regiao}
        onRegionChangeComplete={setRegiao}
        showsMyLocationButton={false}
        showsPointsOfInterests={false}
        customMapStyle={escuro ? ESTILO_ESCURO : ESTILO_CLARO}
        userInterfaceStyle={escuro ? 'dark' : 'light'}
        toolbarEnabled={false}
        accessibilityLabel={`Mapa com ${lugares.length} lugares para procurar perto de você`}
      >
        <Marker key={`voce-${c.agua}`} coordinate={{ latitude: posicao.lat, longitude: posicao.lon }}
          anchor={CENTRO} title="Você" tracksViewChanges={false}>
          <View style={{ width: 18, height: 18, borderRadius: 9, backgroundColor: c.agua, borderWidth: 2, borderColor: c.aguaTinta }} />
        </Marker>
        {manchas.map((m) => (
          <Circle key={`${m.celula}-${m.tema}`} center={{ latitude: m.lat, longitude: m.lon }} radius={250}
            fillColor={m.guardiao ? `${c.destaque}40` : `${c.apagado}26`} strokeColor={m.guardiao ? c.destaque : c.apagado} strokeWidth={1} />
        ))}
        {manchas.filter((m) => m.guardiao).map((m) => (
          <Marker key={`g-${m.celula}-${m.tema}`} coordinate={{ latitude: m.lat, longitude: m.lon }} opacity={0.9} tracksViewChanges={false}>
            <View className="h-[44px] w-[44px] items-center justify-center rounded-full bg-ficha border border-linha">
              <Icone nome="medalha" tamanho={22} cor={c.tinta} />
            </View>
            <Balao c={c} titulo="Guardião da semana" linha={m.guardiao ?? undefined} />
          </Marker>
        ))}
        <Lugares lugares={lugares} temas={temas} c={c} regiao={regiao} largura={largura} posicao={posicao} temaDoDia={temaDoDia}
          aproximar={(lat, lon) => mapa.current?.animateToRegion({ latitude: lat, longitude: lon,
            latitudeDelta: regiao.latitudeDelta / 3, longitudeDelta: regiao.longitudeDelta / 3 })} />
      </MapView>
    </View>
  );
});

function Lugares({ lugares, temas, c, regiao, largura, posicao, temaDoDia, aproximar }: {
  lugares: Lugar[]; temas: Record<string, Tema>; c: Cores; regiao: Region; largura: number;
  posicao: PropsMapa['posicao']; temaDoDia?: string; aproximar: (lat: number, lon: number) => void;
}) {
  const reduzido = useMovimentoReduzido();
  const itens = useMemo(() => agrupar(lugares, regiao, largura), [lugares, regiao, largura]);
  const pulsam = useMemo(() => {
    if (reduzido !== false || !temaDoDia) return new Set<string>();
    const escalaLon = Math.cos(posicao.lat * Math.PI / 180);
    const distancia = (lugar: Lugar) => Math.hypot(lugar.lat - posicao.lat, (lugar.lon - posicao.lon) * escalaLon);
    return new Set(lugares.filter((lugar) => lugar.tema === temaDoDia)
      .sort((primeiro, segundo) => distancia(primeiro) - distancia(segundo)).slice(0, 3).map((lugar) => lugar.mapa));
  }, [lugares, posicao, reduzido, temaDoDia]);
  const [desenhando, setDesenhando] = useState(true);
  const chave = JSON.stringify(itens.map((item) => item.tipo === 'grupo' ? item.lugares.map((lugar) => lugar.mapa) : item.lugar.mapa));
  const chavePulsos = JSON.stringify([...pulsam]);
  useEffect(() => {
    setDesenhando(true);
    const prazo = setTimeout(() => setDesenhando(false), 800);
    return () => clearTimeout(prazo);
  }, [chave, chavePulsos, lugares, temas, c, temaDoDia]);

  return (
    <>
      {itens.map((item) => {
        if (item.tipo === 'grupo') {
          const cor = escurecerParaBranco(temas[item.tema]?.cor ?? c.agua, 4.5);
          return (
            <Marker key={`grupo-${item.lugares[0].mapa}`} coordinate={{ latitude: item.lat, longitude: item.lon }}
              anchor={CENTRO} tracksViewChanges={desenhando} accessibilityLabel={`${item.quantos} lugares. Toque para aproximar`}
              onPress={() => aproximar(item.lat, item.lon)}>
              <View style={[estilosMarcador.circulo, { width: 40, height: 40, borderRadius: 20, backgroundColor: cor, borderColor: c.superficie }]}>
                <Text style={{ color: '#FFFFFF', fontFamily: FONTE_NUMERO, fontSize: 14 }}>{item.quantos}</Text>
              </View>
            </Marker>
          );
        }

        const { lugar } = item;
        const tema = temas[lugar.tema];
        const doDia = lugar.tema === temaDoDia;
        const pulsa = pulsam.has(lugar.mapa);
        const distancia = `${lugar.distancia_km.toFixed(1)} km`;
        const dica = tema ? ` · procure ${tema.nome.toLowerCase()}` : '';
        return (
          <Marker key={lugar.mapa} coordinate={{ latitude: lugar.lat, longitude: lugar.lon }} anchor={CENTRO}
            tracksViewChanges={desenhando || pulsa} title={lugar.nome} description={`${distancia}${dica}`}>
            <View style={[estilosMarcador.area, pulsa && estilosMarcador.areaPulso]}>
              {pulsa ? <Pulso cor={c.destaque} /> : null}
              <View style={[estilosMarcador.circulo, { backgroundColor: escurecerParaBranco(tema?.cor ?? c.agua),
                borderColor: doDia ? c.destaque : c.superficie }]}>
                <IconeTema id={lugar.tema} tamanho={18} cor="#FFFFFF" />
              </View>
            </View>
            <Balao c={c} titulo={lugar.nome} distancia={lugar.distancia_km} linha={tema ? `procure ${tema.nome.toLowerCase()}` : undefined} />
          </Marker>
        );
      })}
    </>
  );
}

function Pulso({ cor }: { cor: string }) {
  const [progresso] = useState(() => new Animated.Value(0));
  useEffect(() => {
    const animacao = Animated.loop(Animated.timing(progresso, {
      toValue: 1, duration: 1600, easing: Easing.out(Easing.cubic), useNativeDriver: true, isInteraction: false,
    }));
    animacao.start();
    return () => animacao.stop();
  }, [progresso]);
  return <Animated.View pointerEvents="none" style={[estilosMarcador.circulo, { position: 'absolute', borderColor: cor,
    opacity: progresso.interpolate({ inputRange: [0, 1], outputRange: [0.6, 0] }),
    transform: [{ scale: progresso.interpolate({ inputRange: [0, 1], outputRange: [1, 1.6] }) }],
  }]} />;
}

const estilosMarcador = StyleSheet.create({
  area: { alignItems: 'center', justifyContent: 'center' },
  areaPulso: { width: 58, height: 58 },
  circulo: { width: 36, height: 36, borderRadius: 18, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
});

// Balão do marcador. `tooltip` tira a moldura branca do Android, e a largura fixa evita o texto em coluna
// estreita (o balão personalizado encolhe até a largura mínima quando não tem largura).
function Balao({ c, titulo, distancia, linha }: { c: Cores; titulo: string; distancia?: number; linha?: string }) {
  return (
    <Callout tooltip>
      <View style={{ width: 230, backgroundColor: c.superficie, borderColor: c.linha, borderWidth: 1, borderRadius: 6,
        paddingHorizontal: 12, paddingVertical: 10, gap: 4 }}>
        <Text numberOfLines={2} style={{ fontFamily: FONTE_TEXTO_FORTE, fontSize: 15, color: c.tinta }}>{titulo}</Text>
        <Text numberOfLines={2} style={{ fontFamily: FONTE_TEXTO, fontSize: 13, color: c.apagado }}>
          {distancia !== undefined ? <Text style={{ fontFamily: FONTE_NUMERO, color: c.agua }}>{distancia.toFixed(1)} km</Text> : null}
          {distancia !== undefined && linha ? '  ·  ' : ''}{linha}
        </Text>
      </View>
    </Callout>
  );
}
