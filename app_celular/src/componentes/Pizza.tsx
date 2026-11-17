// Gráficos de pizza (rosca) da aba Amigos: a parte de cada coisa no todo. Uma rosca por pessoa, lado a lado, e uma
// legenda única com o nome e a porcentagem escritos (a cor nunca é a única pista). Paleta categórica de referência
// do dataviz, validada para daltonismo no claro e no escuro; a ordem das cores é fixa, nunca pela posição no ranking.
import { useState } from 'react';
import { Pressable, Text, useColorScheme, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { useCores } from '../lib/cores';

const CORES = {
  claro: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'],
  escuro: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'],
};

export type Fatia = { nome: string; valor: number };
type Pessoa = { nome: string; fatias: Fatia[] };

const pct = (v: number, total: number) => (total ? Math.round((v / total) * 100) : 0);

function fatiaPath(cx: number, cy: number, r: number, de: number, ate: number) {
  const ponto = (a: number) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const [x1, y1] = ponto(de);
  const [x2, y2] = ponto(ate);
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${ate - de > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`;
}

function Rosca({ fatias, cores, tamanho, destaque }: {
  fatias: Fatia[]; cores: string[]; tamanho: number; destaque: number | null;
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
          <Circle cx={r} cy={r} r={r - 1} fill={cores[fatias.indexOf(cheias[0])]} />
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
        <Circle cx={r} cy={r} r={r * 0.55} fill={c.superficie} />
      </Svg>
      <View pointerEvents="none" style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: c.tinta, fontSize: 15, fontWeight: '800' }}>
          {destaque !== null && total ? `${pct(fatias[destaque].valor, total)}%` : total}
        </Text>
        <Text style={{ color: c.apagado, fontSize: 10 }}>{destaque !== null && total ? 'da pizza' : 'total'}</Text>
      </View>
    </View>
  );
}

/** Uma rosca por pessoa (1 ou 2) e a legenda com nome, número e porcentagem. Tocar na legenda destaca a fatia. */
export function Pizza({ pessoas }: { pessoas: Pessoa[] }) {
  const c = useCores();
  const cores = useColorScheme() === 'dark' ? CORES.escuro : CORES.claro;
  const [destaque, setDestaque] = useState<number | null>(null);
  const totais = pessoas.map((p) => p.fatias.reduce((s, f) => s + f.valor, 0));
  if (totais.every((t) => t === 0)) return <Text style={{ color: c.apagado }}>Ainda sem fotos para mostrar aqui.</Text>;
  const nomes = pessoas[0].fatias.map((f) => f.nome);
  const tocar = (i: number) => setDestaque(destaque === i ? null : i);
  const resumo = pessoas.map((p, k) => `${p.nome}: ${p.fatias.map((f) => `${f.nome} ${pct(f.valor, totais[k])}%`).join(', ')}`).join('. ');
  return (
    <View style={{ gap: 12 }} accessible accessibilityLabel={resumo}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-around' }}>
        {pessoas.map((p) => (
          <View key={p.nome} style={{ alignItems: 'center', gap: 6 }}>
            <Rosca fatias={p.fatias} cores={cores} tamanho={pessoas.length > 1 ? 130 : 150} destaque={destaque} />
            {pessoas.length > 1 ? <Text style={{ color: c.tinta, fontSize: 13, fontWeight: '700' }}>{p.nome}</Text> : null}
          </View>
        ))}
      </View>
      {/* Legenda: a mesma ordem e a mesma cor para as duas pessoas */}
      <View style={{ gap: 4 }}>
        {pessoas.length > 1 ? (
          <View style={{ flexDirection: 'row', paddingHorizontal: 6, gap: 8 }}>
            <View style={{ width: 12 }} />
            <Text style={{ flex: 1 }} />
            {pessoas.map((p) => <Text key={p.nome} numberOfLines={1} style={{ width: 64, textAlign: 'right', color: c.apagado, fontSize: 11, fontWeight: '700' }}>{p.nome}</Text>)}
          </View>
        ) : null}
        {nomes.map((n, i) => (
          <Pressable key={n} onPress={() => tocar(i)} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4,
            paddingHorizontal: 6, borderRadius: 8, backgroundColor: destaque === i ? c.suave : 'transparent' }}>
            <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: cores[i] }} />
            <Text numberOfLines={1} style={{ flex: 1, color: c.tinta, fontSize: 13 }}>{n}</Text>
            {pessoas.map((p, k) => (
              <Text key={p.nome} style={{ width: 64, textAlign: 'right', color: c.apagado, fontSize: 12 }}>
                {pct(p.fatias[i].valor, totais[k])}%{pessoas.length > 1 ? '' : ` · ${p.fatias[i].valor}`}
              </Text>
            ))}
          </Pressable>
        ))}
      </View>
    </View>
  );
}
