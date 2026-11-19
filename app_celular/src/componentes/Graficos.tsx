// Gráficos de Amigos e Pódio. A legenda identifica as séries e tocar numa coluna mostra sua contagem.
import { Fragment, useState } from 'react';
import { Pressable, ScrollView, Text, useColorScheme, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Text as TextoSvg } from 'react-native-svg';

import { useCores } from '../lib/cores';
import { Surge } from '../lib/movimento';
import { IconeTema } from './icones/Icone';

export function useCoresGrafico() {
  const { agua, apagado } = useCores();
  return { voce: useColorScheme() === 'dark' ? '#FF9663' : '#C24A06', amigo: agua, terceiro: apagado };
}

type Serie = { nome: string; valores: number[]; cor?: string };

function corDaSerie(serie: Pick<Serie, 'cor'>, indice: number, cores: ReturnType<typeof useCoresGrafico>) {
  return serie.cor ?? [cores.voce, cores.amigo, cores.terceiro][indice] ?? cores.terceiro;
}

// "Você: mais às 9-12h · Carlos: mais às 18-21h"
function resumo(rotulos: string[], series: Serie[], prefixo: string) {
  return series.map((s) => {
    const max = Math.max(...s.valores);
    return max > 0 ? `${s.nome}: ${prefixo} ${rotulos[s.valores.indexOf(max)]} (${max})` : `${s.nome}: nada ainda`;
  }).join('. ');
}

export function Legenda({ series }: { series: Pick<Serie, 'nome' | 'cor'>[] }) {
  const cor = useCoresGrafico();
  if (series.length < 2) return null;
  return (
    <View className="flex-row flex-wrap gap-[12px]" accessibilityElementsHidden>
      {series.map((s, i) => (
        <View key={s.nome} className="flex-row items-center gap-[6px]">
          <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: corDaSerie(s, i, cor) }} />
          <Text className="font-texto text-apagado text-[13px]" >{s.nome}</Text>
        </View>
      ))}
    </View>
  );
}

export function Linhas({ rotulos, series }: { rotulos: string[]; series: Serie[] }) {
  const c = useCores();
  const cores = useCoresGrafico();
  const [largura, setLargura] = useState(0);
  const [dia, setDia] = useState(0);
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  if (!max) return <Text className="font-texto text-apagado">Sem pontos para mostrar nesses dias.</Text>;
  const teto = Math.ceil(max / 2) * 2;
  const margem = 40;
  const passo = Math.max(44, (largura - margem) / rotulos.length);
  const larguraGrafico = margem + passo * rotulos.length;
  const x = (i: number) => margem + passo * (i + 0.5);
  const y = (valor: number) => 134 - 122 * valor / teto;

  return (
    <View className="gap-[6px]" onLayout={(e) => setLargura(e.nativeEvent.layout.width)}>
      <Text className="font-texto text-tinta text-[13px]" accessibilityLiveRegion="polite">
        {rotulos[dia]} · {series.map((s) => `${s.nome} ${s.valores[dia]} pts`).join(' · ')}
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
            <Svg width={larguraGrafico} height={144}>
              {[0, teto / 2, teto].map((v) => (
                <Fragment key={v}>
                  <Line x1={margem} x2={larguraGrafico} y1={y(v)} y2={y(v)} stroke={c.linha} />
                  <TextoSvg x={margem - 5} y={y(v) + 4} fill={c.apagado} fontSize={10} textAnchor="end">{v}</TextoSvg>
                </Fragment>
              ))}
              {series.map((s, k) => (
                <Polyline key={s.nome} points={s.valores.map((valor, i) => `${x(i)},${y(valor)}`).join(' ')}
                  fill="none" stroke={corDaSerie(s, k, cores)} strokeWidth={2.5} strokeLinejoin="round" />
              ))}
              {series.map((s, k) => (
                <Circle key={s.nome} cx={x(dia)} cy={y(s.valores[dia])} r={4}
                  fill={corDaSerie(s, k, cores)} stroke={c.superficie} strokeWidth={1} />
              ))}
            </Svg>
          </View>
          <View className="flex-row" style={{ paddingLeft: margem }}>
            {rotulos.map((rotulo, i) => (
              <Pressable key={rotulo} onPress={() => setDia(i)} accessibilityRole="button"
                accessibilityState={{ selected: dia === i }}
                accessibilityLabel={`${rotulo}, ${series.map((s) => `${s.nome} ${s.valores[i]} pontos acumulados`).join(', ')}`}
                className="min-h-[44px] items-center justify-center rounded-ficha"
                style={{ width: passo, backgroundColor: dia === i ? c.suave : 'transparent' }}>
                <Text className="font-texto text-apagado text-[11px]">{rotulo}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

/** Colunas verticais por grupo. Só a maior coluna de cada pessoa leva o número em cima. */
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
                    borderTopLeftRadius: 4, borderTopRightRadius: 4, backgroundColor: corDaSerie(s, k, cor) }} />
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
                  borderTopRightRadius: 4, borderBottomRightRadius: 4, backgroundColor: corDaSerie(s, k, cor) }} />
                <Text className="font-numero text-apagado text-[11px]">{s.valores[i]}</Text>
              </View>
            ))}
          </View>
        </Surge>
      ))}
    </View>
  );
}
