// Resumo do dia numa linha (toque para abrir): lupa, meta da turma e desafios. Abre sozinho quando a lupa
// enche ou a meta está aberta, como no app web.
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { Estado } from '../lib/api';
import { useCores } from '../lib/cores';

export function PainelDoDia({ estado }: { estado: Estado }) {
  const c = useCores();
  const { dia, meta, corrente } = estado;
  const [aberto, setAberto] = useState(dia.lupa_cheia || meta.aberta);
  const feitos = dia.desafios.filter((d) => d.ok).length;
  const tema = estado.tema_do_dia.nome.toLowerCase();
  const metaTxt = meta.cumprida
    ? `Meta da turma cumprida: ${meta.feitas} fotos de ${tema}. Cada uma ganhou +10.`
    : meta.aberta
      ? `Meta da turma: ${meta.feitas} de ${meta.alvo} fotos de ${tema}. Faltam ${meta.faltam_min} min.`
      : `Meta da turma, das ${meta.comeca} às ${meta.termina}: ${meta.alvo} fotos de ${tema}. Quem ajudar ganha +10 por foto.`;

  return (
    <View style={{ backgroundColor: c.superficie, borderRadius: 14, borderWidth: 1, borderColor: c.linha }}>
      <Pressable accessibilityRole="button" accessibilityState={{ expanded: aberto }} onPress={() => setAberto(!aberto)}
        style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, minHeight: 48 }}>
        <Lupa carga={dia.lupa} cheia={dia.lupa_cheia} />
        <Text style={{ flex: 1, color: c.tinta, fontSize: 14 }} numberOfLines={1}>
          Lupa {dia.lupa}/3 · Meta {meta.feitas} de {meta.alvo} · Desafios {feitos} de {dia.desafios.length}
        </Text>
        <Text style={{ color: c.apagado, fontSize: 16 }} accessibilityElementsHidden>{aberto ? '▴' : '▾'}</Text>
      </Pressable>
      {aberto ? (
        <View style={{ paddingHorizontal: 12, paddingBottom: 12, gap: 10 }}>
          <Text style={{ color: c.tinta, fontSize: 14, lineHeight: 20 }}>
            {dia.lupa_cheia ? 'Lupa cheia: o próximo achado vale +50%.' : `Lupa ${dia.lupa}/3: fotografe 3 temas diferentes para encher.`}
            {corrente ? ` Corrente: ${corrente} ${corrente === 1 ? 'dia' : 'dias'}.` : ''}
          </Text>
          <View>
            <Text style={{ color: c.tinta, fontSize: 14, lineHeight: 20 }}>{metaTxt}</Text>
            <View accessibilityRole="progressbar" accessibilityLabel="Meta da turma"
              accessibilityValue={{ min: 0, max: meta.alvo, now: meta.feitas }}
              style={{ height: 8, borderRadius: 4, backgroundColor: c.suave, marginTop: 6, overflow: 'hidden' }}>
              <View style={{ width: `${Math.min(100, (100 * meta.feitas) / meta.alvo)}%`, height: 8, backgroundColor: c.sol }} />
            </View>
          </View>
          {dia.desafios.map((d) => (
            <View key={d.texto} style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
              <Text style={{ minWidth: 36, color: d.ok ? c.destaque : c.apagado, fontWeight: '700' }}>{d.ok ? '✔' : `${d.feito}/${d.alvo}`}</Text>
              <Text style={{ flex: 1, color: c.tinta, fontSize: 14, textDecorationLine: d.ok ? 'line-through' : 'none' }}>
                {d.texto} <Text style={{ color: c.apagado }}>(+15)</Text>
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function Lupa({ carga, cheia }: { carga: number; cheia: boolean }) {
  const c = useCores();
  return (
    <View style={{ flexDirection: 'row', gap: 3 }} accessibilityElementsHidden>
      {[0, 1, 2].map((k) => (
        <View key={k} style={{ width: 8, height: 18, borderRadius: 3, backgroundColor: k < carga ? c.sol : c.suave,
          borderWidth: cheia ? 1 : 0, borderColor: c.solTinta }} />
      ))}
    </View>
  );
}
