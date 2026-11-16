// Mapa nativo do celular (Google no Android, Apple no iPhone): você, os lugares de cada tema e as manchas da turma.
// Os blocos do tile.openstreetmap.org bloqueiam apps sem identificação ("Access blocked"), por isso o mapa do sistema.
// shortcut: no Expo Go o Google Maps já vem com chave; num APK próprio, pôr a chave em app.json (android.config.googleMaps).
import { useEffect, useState } from 'react';
import { Text, View, useColorScheme } from 'react-native';
import MapView, { Callout, Circle, Marker } from 'react-native-maps';

// Esconde lojas e empresas do mapa base: sobram as ruas, os parques e os marcadores do jogo
const ESTILO_LIMPO = [{ featureType: 'poi.business', stylers: [{ visibility: 'off' }] }];

// Os lugares piscam, cada um no seu ritmo. Muda só a opacidade do marcador (barato no nativo).
function usePiscar() {
  const [tempo, setTempo] = useState(0);
  const parado = useMovimentoReduzido();
  useEffect(() => {
    if (parado) return;
    const id = setInterval(() => setTempo((t) => t + 1), 150);
    return () => clearInterval(id);
  }, [parado]);
  return (i: number) => (parado ? 1 : 0.25 + 0.75 * Math.abs(Math.sin(tempo * (0.12 + (i % 5) * 0.03) + i * 1.7)));
}

import type { Mapa as DadosMapa, Tema } from '../lib/api';
import { useCores } from '../lib/cores';
import { useMovimentoReduzido } from '../lib/movimento';

export type PropsMapa = {
  posicao: { lat: number; lon: number };
  dados: DadosMapa | null;
  temas: Record<string, Tema>;
  mostrar: string[];
};

export function Mapa({ posicao, dados, temas, mostrar }: PropsMapa) {
  const c = useCores();
  const escuro = useColorScheme() === 'dark';
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema));
  const manchas = (dados?.manchas ?? []).filter((m) => mostrar.includes(m.tema));
  const brilho = usePiscar();
  // Android: o marcador com desenho próprio vira imagem; redesenha só logo depois que a lista muda
  const [desenhando, setDesenhando] = useState(true);
  const chave = lugares.map((l) => l.mapa).join();
  useEffect(() => {
    setDesenhando(true);
    const t = setTimeout(() => setDesenhando(false), 800);
    return () => clearTimeout(t);
  }, [chave]);
  return (
    <View style={{ flex: 1 }}>
      <MapView
        style={{ flex: 1 }}
        initialRegion={{ latitude: posicao.lat, longitude: posicao.lon, latitudeDelta: 0.02, longitudeDelta: 0.02 }}
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
          <Marker key={`g-${m.celula}-${m.tema}`} coordinate={{ latitude: m.lat, longitude: m.lon }} opacity={0.9}>
            <Text style={{ fontSize: 20 }}>🛡️</Text>
            <Callout><Text>Guardião da semana: {m.guardiao}</Text></Callout>
          </Marker>
        ))}
        {lugares.map((l, i) => {
          const t = temas[l.tema];
          return (
            <Marker key={l.mapa} coordinate={{ latitude: l.lat, longitude: l.lon }} anchor={{ x: 0.5, y: 0.5 }}
              opacity={brilho(i)} tracksViewChanges={desenhando}
              title={`${t?.emoji ?? ''} ${l.nome}`} description={`${l.distancia_km.toFixed(1)} km · procure ${t?.nome.toLowerCase() ?? ''}`}>
              <View style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: t?.cor ?? c.destaque,
                borderWidth: 3, borderColor: '#fff', alignItems: 'center', justifyContent: 'center' }}>
                <Text style={{ fontSize: 17 }}>{t?.emoji ?? '📍'}</Text>
              </View>
            </Marker>
          );
        })}
      </MapView>
    </View>
  );
}
