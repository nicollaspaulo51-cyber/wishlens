// Mapa nativo do celular (Google no Android, Apple no iPhone): você, os lugares de cada tema e as manchas da turma.
// Os blocos do tile.openstreetmap.org bloqueiam apps sem identificação ("Access blocked"), por isso o mapa do sistema.
// shortcut: no Expo Go o Google Maps já vem com chave; num APK próprio, pôr a chave em app.json (android.config.googleMaps).
import { Text, View, useColorScheme } from 'react-native';
import MapView, { Callout, Circle, Marker } from 'react-native-maps';

// Esconde lojas e empresas do mapa base: sobram as ruas, os parques e os marcadores do jogo
const ESTILO_LIMPO = [{ featureType: 'poi.business', stylers: [{ visibility: 'off' }] }];

import type { Mapa as DadosMapa, Tema } from '../lib/api';
import { useCores } from '../lib/cores';

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
        {lugares.map((l) => (
          <Marker key={l.mapa} coordinate={{ latitude: l.lat, longitude: l.lon }} pinColor={temas[l.tema]?.cor}
            title={`${temas[l.tema]?.emoji ?? ''} ${l.nome}`} description={`${l.distancia_km.toFixed(1)} km · procure ${temas[l.tema]?.nome.toLowerCase() ?? ''}`} />
        ))}
      </MapView>
    </View>
  );
}
