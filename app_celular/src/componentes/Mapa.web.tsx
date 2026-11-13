// Na versão web (só para conferir telas no computador) não há mapa nativo: mostra a lista de lugares.
import { ScrollView, Text, View } from 'react-native';

import { useCores } from '../lib/cores';
import type { PropsMapa } from './Mapa';

export type { PropsMapa };

export function Mapa({ dados, temas, mostrar }: PropsMapa) {
  const c = useCores();
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)).slice(0, 30);
  return (
    <ScrollView style={{ flex: 1, backgroundColor: c.suave }} contentContainerStyle={{ padding: 12, gap: 6 }}>
      <Text style={{ color: c.apagado, fontSize: 13 }}>O mapa aparece no celular. Aqui, os lugares mais perto:</Text>
      {lugares.map((l) => (
        <View key={l.mapa} style={{ flexDirection: 'row', gap: 8 }}>
          <Text>{temas[l.tema]?.emoji}</Text>
          <Text style={{ flex: 1, color: c.tinta }}>{l.nome}</Text>
          <Text style={{ color: c.apagado }}>{l.distancia_km.toFixed(1)} km</Text>
        </View>
      ))}
    </ScrollView>
  );
}
