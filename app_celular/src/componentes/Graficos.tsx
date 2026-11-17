// Gráficos da aba Amigos, feitos só com Views (sem biblioteca nova): colunas e barras, de uma pessoa ou de duas lado a
// lado. Cores validadas para daltonismo (dataviz/validate_palette.js) no tema claro e no escuro; a identidade também
// vai na legenda e no texto, nunca só na cor. Tocar numa coluna ou barra mostra os números dela.
import { useState } from 'react';
import { Pressable, Text, useColorScheme, View } from 'react-native';

import { useCores } from '../lib/cores';
import { Surge } from '../lib/movimento';

export function useCoresGrafico() {
  return useColorScheme() === 'dark' ? { voce: '#2BA673', amigo: '#9A7BEA' } : { voce: '#0B8A5A', amigo: '#7B4FD6' };
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
  const c = useCores();
  const cor = useCoresGrafico();
  if (series.length < 2) return null;
  return (
    <View style={{ flexDirection: 'row', gap: 16 }} accessibilityElementsHidden>
      {series.map((s, i) => (
        <View key={s.nome} style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: i ? cor.amigo : cor.voce }} />
          <Text style={{ color: c.apagado, fontSize: 13 }}>{s.nome}</Text>
        </View>
      ))}
    </View>
  );
}

function Detalhe({ texto }: { texto: string | null }) {
  const c = useCores();
  return <Text style={{ color: c.tinta, fontSize: 13, minHeight: 18 }} accessibilityLiveRegion="polite">{texto ?? ' '}</Text>;
}

/** Colunas verticais (uma ou duas por grupo). Só a maior coluna de cada pessoa leva o número em cima. */
export function Colunas({ rotulos, series, prefixo = 'mais em', altura = 120, chave }: {
  rotulos: string[]; series: Serie[]; prefixo?: string; altura?: number; chave?: unknown;
}) {
  const c = useCores();
  const cor = useCoresGrafico();
  const [sel, setSel] = useState<number | null>(null);
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  if (max === 0) return <Text style={{ color: c.apagado }}>Ainda sem fotos para mostrar aqui.</Text>;
  const maiores = series.map((s) => s.valores.indexOf(Math.max(...s.valores)));
  return (
    <View style={{ gap: 6 }} accessible accessibilityLabel={resumo(rotulos, series, prefixo)}>
      <Detalhe texto={sel === null ? null : `${rotulos[sel]}: ${series.map((s) => `${s.nome} ${s.valores[sel]}`).join(' · ')}`} />
      <View style={{ height: altura + 16, flexDirection: 'row', alignItems: 'flex-end', gap: 3, borderBottomWidth: 1, borderBottomColor: c.linha }}>
        {rotulos.map((r, i) => (
          <Pressable key={r} onPress={() => setSel(sel === i ? null : i)} style={{ flex: 1, height: '100%', flexDirection: 'row',
            alignItems: 'flex-end', justifyContent: 'center', gap: 2, borderRadius: 4, backgroundColor: sel === i ? c.suave : 'transparent' }}>
            {series.map((s, k) => (
              <Surge key={s.nome} ordem={i} chave={chave} estilo={{ flex: 1, maxWidth: 16, alignItems: 'center' }}>
                {maiores[k] === i ? <Text style={{ color: c.tinta, fontSize: 10, fontWeight: '700' }}>{s.valores[i]}</Text> : null}
                <View style={{ width: '100%', height: Math.max(s.valores[i] ? 3 : 0, (s.valores[i] / max) * altura),
                  borderTopLeftRadius: 4, borderTopRightRadius: 4, backgroundColor: k ? cor.amigo : cor.voce }} />
              </Surge>
            ))}
          </Pressable>
        ))}
      </View>
      <View style={{ flexDirection: 'row', gap: 3 }}>
        {rotulos.map((r) => (
          <Text key={r} numberOfLines={1} style={{ flex: 1, textAlign: 'center', color: c.apagado, fontSize: rotulos.length > 8 ? 9 : 11 }}>{r}</Text>
        ))}
      </View>
    </View>
  );
}

/** Barras horizontais, uma linha por item (com o nome à esquerda e o número no fim de cada barra). */
export function Barras({ rotulos, series, prefixo = 'mais em', chave }: {
  rotulos: string[]; series: Serie[]; prefixo?: string; chave?: unknown;
}) {
  const c = useCores();
  const cor = useCoresGrafico();
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  if (max === 0) return <Text style={{ color: c.apagado }}>Ainda sem fotos para mostrar aqui.</Text>;
  return (
    <View style={{ gap: 10 }} accessible accessibilityLabel={resumo(rotulos, series, prefixo)}>
      {rotulos.map((r, i) => (
        <Surge key={r} ordem={i} chave={chave} estilo={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Text numberOfLines={2} style={{ width: 96, color: c.tinta, fontSize: 13 }}>{r}</Text>
          <View style={{ flex: 1, gap: 2 }}>
            {series.map((s, k) => (
              <View key={s.nome} style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <View style={{ height: 10, width: `${(s.valores[i] / max) * 82}%`, minWidth: s.valores[i] ? 3 : 0,
                  borderTopRightRadius: 4, borderBottomRightRadius: 4, backgroundColor: k ? cor.amigo : cor.voce }} />
                <Text style={{ color: c.apagado, fontSize: 11 }}>{s.valores[i]}</Text>
              </View>
            ))}
          </View>
        </Surge>
      ))}
    </View>
  );
}
