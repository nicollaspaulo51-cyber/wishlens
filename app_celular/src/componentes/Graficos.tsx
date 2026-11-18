// Gráficos da aba Amigos, feitos só com Views (sem biblioteca nova): colunas e barras, de uma pessoa ou de duas lado a
// lado. A legenda identifica as séries; tocar numa coluna mostra sua contagem.
import { useState } from 'react';
import { Pressable, ScrollView, Text, useColorScheme, View } from 'react-native';

import { useCores } from '../lib/cores';
import { Surge } from '../lib/movimento';
import { IconeTema } from './icones/Icone';

export function useCoresGrafico() {
  const { agua } = useCores();
  return { voce: useColorScheme() === 'dark' ? '#FF9663' : '#C24A06', amigo: agua };
}

type Serie = { nome: string; valores: number[] };

// "Você: mais às 9-12h · Carlos: mais às 18-21h"
function resumo(rotulos: string[], series: Serie[], prefixo: string) {
  return series.map((s) => {
    const max = Math.max(...s.valores);
    return max > 0 ? `${s.nome}: ${prefixo} ${rotulos[s.valores.indexOf(max)]} (${max})` : `${s.nome}: nada ainda`;
  }).join('. ');
}

export function Legenda({ series }: { series: Serie[] }) {
  const cor = useCoresGrafico();
  if (series.length < 2) return null;
  return (
    <View className="flex-row gap-[16px]" accessibilityElementsHidden>
      {series.map((s, i) => (
        <View key={s.nome} className="flex-row items-center gap-[6px]">
          <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: i ? cor.amigo : cor.voce }} />
          <Text className="font-texto text-apagado text-[13px]" >{s.nome}</Text>
        </View>
      ))}
    </View>
  );
}

/** Colunas verticais (uma ou duas por grupo). Só a maior coluna de cada pessoa leva o número em cima. */
export function Colunas({ rotulos, series, prefixo = 'mais em', altura = 120, chave }: {
  rotulos: string[]; series: Serie[]; prefixo?: string; altura?: number; chave?: unknown;
}) {
  const c = useCores();
  const cor = useCoresGrafico();
  const [sel, setSel] = useState<number | null>(null);
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  if (max === 0) return <Text className="font-texto text-apagado" >Ainda sem fotos para mostrar aqui.</Text>;
  const maiores = series.map((s) => s.valores.indexOf(Math.max(...s.valores)));
  return (
    <View className="gap-[6px]">
      <Text className="font-texto text-tinta text-[13px] min-h-[18px]" accessibilityLiveRegion="polite">
        {sel === null ? resumo(rotulos, series, prefixo) : <>
          {rotulos[sel]}: {series.map((s, idx) => (
            <Text key={s.nome}>{idx ? ' · ' : ''}{s.nome} <Text className="font-numero">{s.valores[sel]}</Text></Text>
          ))}
        </>}
      </Text>
      <ScrollView horizontal contentContainerStyle={{ flexGrow: 1, gap: 3 }}>
        {rotulos.map((r, i) => (
          <Pressable key={r} onPress={() => setSel(sel === i ? null : i)} accessibilityRole="button"
            accessibilityState={{ selected: sel === i }} accessibilityLabel={`${r}: ${series.map((s) => `${s.nome} ${s.valores[i]}`).join(', ')}`}
            style={{ flexGrow: 1, minWidth: 44, borderRadius: 6, backgroundColor: sel === i ? c.suave : 'transparent' }}>
            <View style={{ height: altura + 16, flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'center',
              gap: 2, borderBottomWidth: 1, borderBottomColor: c.linha }}>
              {series.map((s, k) => (
                <Surge key={s.nome} ordem={i} chave={chave} estilo={{ flex: 1, maxWidth: 16, alignItems: 'center' }}>
                  {maiores[k] === i ? <Text className="font-numero text-tinta text-[10px]">{s.valores[i]}</Text> : null}
                  <View style={{ width: '100%', height: Math.max(s.valores[i] ? 3 : 0, (s.valores[i] / max) * altura),
                    borderTopLeftRadius: 4, borderTopRightRadius: 4, backgroundColor: k ? cor.amigo : cor.voce }} />
                </Surge>
              ))}
            </View>
            <Text className="font-texto text-apagado text-center text-[11px]" numberOfLines={1}>{r}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

/** Barras horizontais, uma linha por item (com o nome à esquerda e o número no fim de cada barra). */
export function Barras({ rotulos, icones, series, prefixo = 'mais em', chave }: {
  rotulos: string[]; icones?: string[]; series: Serie[]; prefixo?: string; chave?: unknown;
}) {
  const c = useCores();
  const cor = useCoresGrafico();
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  if (max === 0) return <Text className="font-texto text-apagado" >Ainda sem fotos para mostrar aqui.</Text>;
  return (
    <View className="gap-[10px]" accessible accessibilityLabel={resumo(rotulos, series, prefixo)}>
      {rotulos.map((r, i) => (
        <Surge key={r} ordem={i} chave={chave} estilo={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View className="w-[96px] flex-row items-center gap-1">
            {icones?.[i] ? <IconeTema id={icones[i]} tamanho={16} cor={c.tinta} /> : null}
            <Text className="flex-1 font-texto text-tinta text-[13px]" numberOfLines={2}>{r}</Text>
          </View>
          <View className="flex-1 gap-[2px]">
            {series.map((s, k) => (
              <View key={s.nome} className="flex-row items-center gap-[6px]">
                <View style={{ height: 10, width: `${(s.valores[i] / max) * 82}%`, minWidth: s.valores[i] ? 3 : 0,
                  borderTopRightRadius: 4, borderBottomRightRadius: 4, backgroundColor: k ? cor.amigo : cor.voce }} />
                <Text className="font-numero text-apagado text-[11px]">{s.valores[i]}</Text>
              </View>
            ))}
          </View>
        </Surge>
      ))}
    </View>
  );
}
