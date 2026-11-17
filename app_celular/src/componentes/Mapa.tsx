// Mapa nativo do celular (Google no Android, Apple no iPhone): você, os lugares de cada tema e as manchas da turma.
// Os blocos do tile.openstreetmap.org bloqueiam apps sem identificação ("Access blocked"), por isso o mapa do sistema.
// shortcut: no Expo Go o Google Maps já vem com chave; num APK próprio, pôr a chave em app.json (android.config.googleMaps).
import { memo, useEffect, useRef, useState } from 'react';
import { Text, View, useColorScheme } from 'react-native';
import MapView, { Callout, Circle, Marker, type Region } from 'react-native-maps';

// Esconde lojas e empresas do mapa base: sobram as ruas, os parques e os marcadores do jogo
const ESTILO_LIMPO = [{ featureType: 'poi.business', stylers: [{ visibility: 'off' }] }];

import type { Mapa as DadosMapa, Lugar, Tema } from '../lib/api';
import { useCores } from '../lib/cores';
import { useMovimentoReduzido } from '../lib/movimento';

export type PropsMapa = {
  posicao: { lat: number; lon: number };
  dados: DadosMapa | null;
  temas: Record<string, Tema>;
  mostrar: string[];
};

// O mapa só redesenha quando os dados, a posição ou os filtros mudam; o piscar fica nos Lugares
export const Mapa = memo(function Mapa({ posicao, dados, temas, mostrar }: PropsMapa) {
  const c = useCores();
  const escuro = useColorScheme() === 'dark';
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema));
  const manchas = (dados?.manchas ?? []).filter((m) => mostrar.includes(m.tema));
  // A parte do mapa na tela: só os lugares dela piscam (atualiza quando você para de arrastar)
  const [regiao, setRegiao] = useState<Region>(() => ({ latitude: posicao.lat, longitude: posicao.lon, latitudeDelta: 0.02, longitudeDelta: 0.02 }));
  const mapa = useRef<MapView>(null);
  // Nas abas os lugares podem estar a 5 ou 10 km: se nenhum aparece na tela, afasta até mostrar os 3 mais perto
  const chaveLugares = lugares.map((l) => l.mapa).join();
  useEffect(() => {
    if (!lugares.length || lugares.some((l) => Math.abs(l.lat - regiao.latitude) <= regiao.latitudeDelta / 2
      && Math.abs(l.lon - regiao.longitude) <= regiao.longitudeDelta / 2)) return;
    const perto = [...lugares].sort((a, b) => a.distancia_km - b.distancia_km).slice(0, 3);
    mapa.current?.fitToCoordinates([{ latitude: posicao.lat, longitude: posicao.lon }, ...perto.map((l) => ({ latitude: l.lat, longitude: l.lon }))],
      { edgePadding: { top: 120, right: 60, bottom: 160, left: 60 }, animated: true });
    // só quando chegam lugares novos (troca de aba ou nova busca), não a cada arrastada
  }, [chaveLugares]);
  return (
    <View style={{ flex: 1 }}>
      <MapView
        ref={mapa}
        style={{ flex: 1 }}
        initialRegion={regiao}
        onRegionChangeComplete={setRegiao}
        showsUserLocation
        showsMyLocationButton={false}
        showsPointsOfInterests={false}
        customMapStyle={ESTILO_LIMPO}
        userInterfaceStyle={escuro ? 'dark' : 'light'}
        toolbarEnabled={false}
        accessibilityLabel={`Mapa com ${lugares.length} lugares para procurar perto de você`}
      >
        {manchas.map((m) => (
          <Circle key={`${m.celula}-${m.tema}`} center={{ latitude: m.lat, longitude: m.lon }} radius={250}
            fillColor={m.guardiao ? 'rgba(255,200,61,0.30)' : 'rgba(19,107,76,0.18)'} strokeColor={m.guardiao ? c.sol : c.destaque} strokeWidth={1} />
        ))}
        {manchas.filter((m) => m.guardiao).map((m) => (
          <Marker key={`g-${m.celula}-${m.tema}`} coordinate={{ latitude: m.lat, longitude: m.lon }} opacity={0.9} tracksViewChanges={false}>
            <Text style={{ fontSize: 20 }}>🛡️</Text>
            <Callout><Text>Guardião da semana: {m.guardiao}</Text></Callout>
          </Marker>
        ))}
        <Lugares lugares={lugares} temas={temas} cor={c.destaque} regiao={regiao} />
      </MapView>
    </View>
  );
});

// Piscam todos os lugares na tela, até este limite (os mais perto de você): cada passo é uma mensagem
// para o mapa nativo, e fora da tela ninguém vê a piscada
const PISCAM = 30;
// Passos curtos numa onda lenta (2,4 a 3,3 s por piscada): cada passo muda pouco a opacidade, e o olho vê
// um brilho que respira em vez de saltos. O marcador nativo não aceita animação do Animated.
const PASSO_MS = 130;

// Os lugares piscam, cada um no seu ritmo. Muda só a opacidade do marcador; o resto do mapa não redesenha.
function Lugares({ lugares, temas, cor, regiao }: { lugares: Lugar[]; temas: Record<string, Tema>; cor: string; regiao: Region }) {
  const parado = useMovimentoReduzido();
  const [tempo, setTempo] = useState(0);
  useEffect(() => {
    if (parado || !lugares.length) return;
    const id = setInterval(() => setTempo((n) => n + 1), PASSO_MS);
    return () => clearInterval(id);
  }, [parado, lugares.length]);
  // Android: o marcador com desenho próprio vira imagem; redesenha só logo depois que a lista muda
  const [desenhando, setDesenhando] = useState(true);
  const chave = lugares.map((l) => l.mapa).join();
  useEffect(() => {
    setDesenhando(true);
    const t = setTimeout(() => setDesenhando(false), 800);
    return () => clearTimeout(t);
  }, [chave]);
  const pertoPrimeiro = [...lugares].sort((a, b) => a.distancia_km - b.distancia_km);
  const naTela = (l: Lugar) => Math.abs(l.lat - regiao.latitude) <= regiao.latitudeDelta / 2
    && Math.abs(l.lon - regiao.longitude) <= regiao.longitudeDelta / 2;
  const piscam = new Set(pertoPrimeiro.filter(naTela).slice(0, PISCAM).map((l) => l.mapa));
  return (
    <>
      {pertoPrimeiro.map((l, i) => {
        const t = temas[l.tema];
        const segundos = (tempo * PASSO_MS) / 1000;
        const periodo = 2.4 + (i % 4) * 0.3;
        const onda = 0.5 + 0.5 * Math.sin((2 * Math.PI * segundos) / periodo + i * 1.7);
        const brilho = parado || !piscam.has(l.mapa) ? 0.95 : Math.round((0.4 + 0.6 * onda) * 50) / 50;
        return (
          <Marker key={l.mapa} coordinate={{ latitude: l.lat, longitude: l.lon }} anchor={{ x: 0.5, y: 0.5 }}
            opacity={brilho} tracksViewChanges={desenhando}
            title={`${t?.emoji ?? ''} ${l.nome}`} description={`${l.distancia_km.toFixed(1)} km · procure ${t?.nome.toLowerCase() ?? ''}`}>
            <View style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: t?.cor ?? cor,
              borderWidth: 3, borderColor: '#fff', alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ fontSize: 17 }}>{t?.emoji ?? '📍'}</Text>
            </View>
          </Marker>
        );
      })}
    </>
  );
}
