// Na versão web (só para conferir telas no computador) não há mapa nativo: mostra a lista de lugares.
import { ScrollView, Text, View } from 'react-native';

import { useCores } from '../lib/cores';
import { IconeTema } from './icones/Icone';
import type { PropsMapa } from './Mapa';

export type { PropsMapa };

export function Mapa({ dados, mostrar, temaDoDia }: PropsMapa) {
  const c = useCores();
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)).slice(0, 30);
  return (
    <ScrollView className="flex-1 bg-suave" contentContainerStyle={{ padding: 12, paddingTop: 230, gap: 6 }}>
      <Text className="font-texto text-apagado text-[13px]" >O mapa aparece no celular. Aqui, os lugares mais perto:</Text>
      <View className="flex-row items-center gap-[8px]">
        <View className="h-[12px] w-[12px] rounded-full bg-agua border border-agua-tinta" />
        <Text className="font-texto-forte text-agua">Você</Text>
      </View>
      {lugares.map((l) => (
        <View key={l.mapa} className="flex-row items-center gap-[8px]">
          <IconeTema id={l.tema} tamanho={18} cor={l.tema === temaDoDia ? c.destaque : c.agua} />
          <Text className="font-texto flex-1 text-tinta" >{l.nome}</Text>
          <Text className="font-texto text-agua" ><Text className="font-numero">{l.distancia_km.toFixed(1)}</Text> km</Text>
        </View>
      ))}
    </ScrollView>
  );
}
