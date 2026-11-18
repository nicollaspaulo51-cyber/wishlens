// Resumo do dia numa linha (toque para abrir): lupa, meta da turma e desafios. Abre sozinho quando a lupa
// enche ou a meta está aberta, como no app web.
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { Estado } from '../lib/api';
import { useCores } from '../lib/cores';

export function PainelDoDia({ estado }: { estado: Estado }) {
  const c = useCores();
  const { dia, meta, corrente } = estado;
  const [aberto, setAberto] = useState(dia.lupa_cheia); // fica por cima do mapa: só abre sozinho com a lupa cheia
  const feitos = dia.desafios.filter((d) => d.ok).length;
  const tema = estado.tema_do_dia.nome.toLowerCase();
  const metaTxt = meta.cumprida
    ? <>Meta da turma cumprida: <Text className="font-numero">{meta.feitas}</Text> fotos de {tema}. Cada uma ganhou <Text className="font-numero">+10</Text>.</>
    : meta.aberta
      ? <>Meta da turma: <Text className="font-numero">{meta.feitas}/{meta.alvo}</Text> fotos de {tema}. Faltam <Text className="font-numero">{meta.faltam_min}</Text> min.</>
      : <>Meta da turma, das <Text className="font-numero">{meta.comeca}</Text> às <Text className="font-numero">{meta.termina}</Text>: <Text className="font-numero">{meta.alvo}</Text> fotos de {tema}. Quem ajudar ganha <Text className="font-numero">+10</Text> por foto.</>;

  return (
    <View className="bg-ficha rounded-ficha border-[1px] border-linha">
      <Pressable accessibilityRole="button" accessibilityState={{ expanded: aberto }} onPress={() => setAberto(!aberto)}
        className="flex-row items-center gap-[10px] p-[12px] min-h-[48px]">
        <Lupa carga={dia.lupa} cheia={dia.lupa_cheia} />
        <Text className="font-texto flex-1 text-tinta text-[14px]">
          Lupa <Text className="font-numero">{dia.lupa}/3</Text> · Meta <Text className="font-numero">{meta.feitas}/{meta.alvo}</Text> · Desafios <Text className="font-numero">{feitos}/{dia.desafios.length}</Text>
        </Text>
        <Text className="font-texto text-apagado text-[13px]" accessibilityElementsHidden>{aberto ? 'Ver menos' : 'Ver mais'}</Text>
      </Pressable>
      {aberto ? (
        <View className="px-[12px] pb-[12px] gap-[10px]">
          <Text className="font-texto text-tinta text-[14px] leading-[20px]" >
            {dia.lupa_cheia
              ? <>Lupa cheia: o próximo achado vale <Text className="font-numero">+50%</Text>.</>
              : <>Lupa <Text className="font-numero">{dia.lupa}/3</Text>: fotografe <Text className="font-numero">3</Text> temas diferentes para encher.</>}
            {corrente ? <> Corrente: <Text className="font-numero">{corrente}</Text> {corrente === 1 ? 'dia' : 'dias'}.</> : null}
          </Text>
          <View>
            <Text className="font-texto text-tinta text-[14px] leading-[20px]" >{metaTxt}</Text>
            <View accessibilityRole="progressbar" accessibilityLabel="Meta da turma"
              accessibilityValue={{ min: 0, max: meta.alvo, now: meta.feitas }}
              className="h-[8px] rounded-[4px] bg-suave mt-[6px] overflow-hidden">
              <View style={{ width: `${Math.min(100, (100 * meta.feitas) / meta.alvo)}%`, height: 8, backgroundColor: c.sol }} />
            </View>
          </View>
          {dia.desafios.map((d) => (
            <View key={d.texto} className="flex-row gap-[10px] items-center">
              <Text className="font-texto-forte" style={{ minWidth: 36, color: d.ok ? c.destaque : c.apagado, fontWeight: '700' }}>{d.ok ? 'Feito' : <Text className="font-numero">{d.feito}/{d.alvo}</Text>}</Text>
              <Text className="font-texto" style={{ flex: 1, color: c.tinta, fontSize: 14, textDecorationLine: d.ok ? 'line-through' : 'none' }}>
                {d.texto} <Text className="font-numero text-apagado">(+15)</Text>
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
    <View className="flex-row gap-[3px]" accessibilityElementsHidden>
      {[0, 1, 2].map((k) => (
        <View key={k} style={{ width: 8, height: 18, borderRadius: 3, backgroundColor: k < carga ? c.sol : c.suave,
          borderWidth: cheia ? 1 : 0, borderColor: c.solTinta }} />
      ))}
    </View>
  );
}
