// Na versão web (só para conferir telas no computador) não há mapa nativo: mostra a lista de lugares.
import { ScrollView, Text, View } from 'react-native';

import { useCores } from '../lib/cores';
import type { PropsMapa } from './Mapa';

export type { PropsMapa };

export function Mapa({ dados, temas, mostrar }: PropsMapa) {
  const c = useCores();
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)).slice(0, 30);
  return (
    <ScrollView className="flex-1 bg-suave" contentContainerStyle={{ padding: 12, paddingTop: 230, gap: 6 }}>
      <Text className="font-texto text-apagado text-[13px]" >O mapa aparece no celular. Aqui, os lugares mais perto:</Text>
      {lugares.map((l) => (
        <View key={l.mapa} className="flex-row gap-[8px]">
          <Text className="font-texto">{temas[l.tema]?.emoji}</Text>
          <Text className="font-texto flex-1 text-tinta" >{l.nome}</Text>
          <Text className="font-texto text-apagado" >{l.distancia_km.toFixed(1)} km</Text>
        </View>
      ))}
    </ScrollView>
  );
}
