// Gráficos de pizza e rosca: a parte de cada coisa no todo. Um gráfico por pessoa, lado a lado, e uma
// legenda única com o nome e a porcentagem escritos (a cor nunca é a única pista). Paleta categórica de referência
// do dataviz, validada para daltonismo no claro e no escuro; a ordem das cores é fixa, nunca pela posição no ranking.
import { useState } from 'react';
import { Pressable, Text, useColorScheme, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { PALETA, useCores } from '../lib/cores';
import { IconeTema } from './icones/Icone';

const CORES = {
  claro: ['#C24A06', PALETA.claro.agua, '#8A6A2E', '#5B6B8C', '#7A4E6B', '#6F7A72'],
  escuro: ['#FF9663', PALETA.escuro.agua, '#CFAD70', '#9EACCE', '#C99DBD', '#AAB7AC'],
};

export type Fatia = { nome: string; valor: number; icone?: string; cor?: string };
type Pessoa = { nome: string; fatias: Fatia[] };

const pct = (v: number, total: number) => (total ? Math.round((v / total) * 100) : 0);

function fatiaPath(cx: number, cy: number, r: number, de: number, ate: number) {
  const ponto = (a: number) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const [x1, y1] = ponto(de);
  const [x2, y2] = ponto(ate);
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${ate - de > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`;
}

function Disco({ fatias, cores, tamanho, destaque, inteira }: {
  fatias: Fatia[]; cores: string[]; tamanho: number; destaque: number | null; inteira: boolean;
}) {
  const c = useCores();
  const total = fatias.reduce((s, f) => s + f.valor, 0);
  const r = tamanho / 2;
  const cheias = fatias.filter((f) => f.valor > 0);
  let angulo = 0;
  return (
    <View style={{ width: tamanho, height: tamanho }}>
      <Svg width={tamanho} height={tamanho}>
        {total === 0 ? <Circle cx={r} cy={r} r={r - 1} fill={c.linha} /> : null}
        {cheias.length === 1 ? (
          <Circle cx={r} cy={r} r={r - 1} fill={cores[fatias.indexOf(cheias[0])]}
            opacity={destaque === null || fatias[destaque] === cheias[0] ? 1 : 0.35} />
        ) : fatias.map((f, i) => {
          if (!f.valor) return null;
          const de = angulo;
          angulo += (f.valor / total) * 2 * Math.PI;
          return (
            <Path key={f.nome} d={fatiaPath(r, r, r - 1, de, angulo)} fill={cores[i]} stroke={c.superficie} strokeWidth={2}
              opacity={destaque === null || destaque === i ? 1 : 0.35} />
          );
        })}
        {/* furo da rosca */}
        {inteira ? null : <Circle cx={r} cy={r} r={r * 0.55} fill={c.superficie} />}
      </Svg>
      {inteira ? null : <View pointerEvents="none" style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center' }}>
        <Text className="font-numero text-tinta text-[15px]" >
          {destaque !== null && total ? `${pct(fatias[destaque].valor, total)}%` : total}
        </Text>
        <Text className="font-texto text-apagado text-[10px]" >{destaque !== null && total ? 'da pizza' : 'total'}</Text>
      </View>}
    </View>
  );
}

/** Até três gráficos com uma legenda compartilhada. Tocar na legenda destaca a fatia. */
export function Pizza({ pessoas, inteira = false }: { pessoas: Pessoa[]; inteira?: boolean }) {
  const c = useCores();
  const paleta = useColorScheme() === 'dark' ? CORES.escuro : CORES.claro;
  const [destaque, setDestaque] = useState<number | null>(null);
  const totais = pessoas.map((p) => p.fatias.reduce((s, f) => s + f.valor, 0));
  if (totais.every((t) => t === 0)) return <Text className="font-texto text-apagado" >Ainda sem fotos para mostrar aqui.</Text>;
  const cores = pessoas[0].fatias.map((f, i) => f.cor ?? paleta[i % paleta.length]);
  const tamanho = pessoas.length === 3 ? 76 : pessoas.length === 2 ? 104 : 150;
  const larguraColuna = pessoas.length === 3 ? 'w-[48px]' : 'w-[64px]';
  const tocar = (i: number) => setDestaque(destaque === i ? null : i);
  const resumo = pessoas.map((p, k) => `${p.nome}: ${p.fatias.map((f) => `${f.nome} ${pct(f.valor, totais[k])}%`).join(', ')}`).join('. ');
  return (
    <View className="gap-[12px]">
      <View className="flex-row justify-around" accessible accessibilityLabel={resumo}>
        {pessoas.map((p) => (
          <View key={p.nome} className="items-center gap-[6px]" style={{ maxWidth: tamanho }}>
            <Disco fatias={p.fatias} cores={cores} tamanho={tamanho} destaque={destaque} inteira={inteira} />
            {pessoas.length > 1 ? <Text className="font-texto-forte text-tinta text-[13px]" numberOfLines={1}>{p.nome}</Text> : null}
          </View>
        ))}
      </View>
      {/* A legenda usa a mesma ordem e as mesmas cores de todos os gráficos. */}
      <View className="gap-[4px]">
        {pessoas.length > 1 ? (
          <View className="flex-row px-[6px] gap-[8px]">
            <View className="w-[12px]" />
            <Text className="font-texto flex-1"  />
            {pessoas.map((p) => <Text className={`font-texto-forte text-right text-apagado text-[11px] ${larguraColuna}`} key={p.nome} numberOfLines={1}>{p.nome}</Text>)}
          </View>
        ) : null}
        {pessoas[0].fatias.map(({ nome, icone }, i) => (
          <Pressable key={icone ?? nome} onPress={() => tocar(i)} accessibilityRole="button" accessibilityState={{ selected: destaque === i }}
            style={{ flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 44, paddingHorizontal: 6, borderRadius: 6, backgroundColor: destaque === i ? c.suave : 'transparent' }}>
            <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: cores[i] }} />
            {icone ? <IconeTema id={icone} cor={c.tinta} tamanho={16} /> : null}
            <Text className="font-texto flex-1 text-tinta text-[13px]" numberOfLines={pessoas.length === 3 ? 2 : 1}>{nome}</Text>
            {pessoas.map((p, k) => (
              <Text className={`font-numero text-right text-apagado text-[12px] ${pessoas.length > 1 ? larguraColuna : ''}`} key={p.nome}>
                {pct(p.fatias[i].valor, totais[k])}%{pessoas.length > 1 ? '' : ` · ${p.fatias[i].valor}`}
              </Text>
            ))}
          </Pressable>
        ))}
      </View>
    </View>
  );
}
