// Na versão web (só para conferir telas no computador) não há mapa nativo: mostra a lista de lugares.
import { useEffect, useRef, type ComponentRef } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { useCores } from '../lib/cores';
import { IconeTema } from './icones/Icone';
import type { PropsMapa } from './Mapa';

export type { PropsMapa };

export function Mapa({ dados, mostrar, temas, recentrar }: PropsMapa) {
  const c = useCores();
  const lista = useRef<ComponentRef<typeof ScrollView>>(null);
  const pedidoAnterior = useRef(recentrar ?? 0);
  useEffect(() => {
    if (recentrar === undefined || recentrar === pedidoAnterior.current) return;
    lista.current?.scrollTo({ y: 0, animated: false });
    pedidoAnterior.current = recentrar;
  }, [recentrar]);
  const lugares = (dados?.lugares ?? []).filter((l) => mostrar.includes(l.tema)).slice(0, 30);
  return (
    <ScrollView ref={lista} className="flex-1 bg-suave"
      contentContainerStyle={{ padding: 12, paddingTop: 88, paddingRight: recentrar === undefined ? 12 : 68, gap: 6 }}>
      <Text className="font-texto text-apagado text-[13px]" >O mapa aparece no celular. Aqui, os lugares mais perto:</Text>
      <View className="flex-row items-center gap-[8px]">
        <View className="h-[12px] w-[12px] rounded-full bg-agua border border-agua-tinta" />
        <Text className="font-texto-forte text-agua">Você</Text>
      </View>
      {lugares.map((l) => (
        <View key={l.mapa} className="flex-row items-center gap-[8px]">
          <IconeTema id={l.tema} tamanho={18} cor={temas[l.tema]?.cor ?? c.agua} />
          <Text className="font-texto flex-1 text-tinta" >{l.nome}</Text>
          <Text className="font-texto text-agua" ><Text className="font-numero">{l.distancia_km.toFixed(1)}</Text> km</Text>
        </View>
      ))}
    </ScrollView>
  );
}
