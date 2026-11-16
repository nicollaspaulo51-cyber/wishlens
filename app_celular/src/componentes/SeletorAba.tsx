// Troca de aba do jogo: um botão pequeno ("🗺️ Mapa livre ▾") que abre uma folha de baixo com as 4 abas,
// cada uma com o que vale nela, onde achar no mapa e os seus pontos de hoje.
import { useState } from 'react';
import { Modal, Pressable, ScrollView, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type Modo } from '../lib/api';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { escolherModo, NOME_LIVRE, useModo } from '../lib/modo';
import { useDados } from '../lib/useDados';

export function useAbas() {
  const temas = useDados(api.temas);
  return [NOME_LIVRE, ...(temas.dados?.abas ?? [])];
}

export function SeletorAba({ pontos, estilo, escuro }: { pontos?: Partial<Record<Modo, number>>; estilo?: StyleProp<ViewStyle>; escuro?: boolean }) {
  const c = useCores();
  const baixo = useSafeAreaInsets().bottom;
  const modo = useModo();
  const abas = useAbas();
  const [aberta, setAberta] = useState(false);
  const atual = abas.find((a) => a.id === modo) ?? NOME_LIVRE;

  return (
    <>
      <Pressable accessibilityRole="button" accessibilityLabel={`Aba do jogo: ${atual.nome}. Tocar para trocar`}
        onPress={() => setAberta(true)}
        style={[{ flexDirection: 'row', alignItems: 'center', gap: 6, minHeight: 40, paddingHorizontal: 14, borderRadius: 20,
          backgroundColor: escuro ? 'rgba(0,0,0,0.45)' : c.superficie, alignSelf: 'flex-start' }, estilo]}>
        <Text style={{ fontSize: 16 }}>{atual.emoji}</Text>
        <Text style={{ color: escuro ? '#fff' : c.tinta, fontWeight: '700', fontSize: 15 }}>{atual.nome}</Text>
        <Text style={{ color: escuro ? '#fff' : c.apagado, fontSize: 12 }}>▼</Text>
      </Pressable>

      <Modal visible={aberta} transparent animationType="slide" onRequestClose={() => setAberta(false)}>
        <Pressable accessibilityLabel="Fechar" onPress={() => setAberta(false)} style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} />
        <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 22, borderTopRightRadius: 22, maxHeight: '80%',
          paddingTop: 10, paddingBottom: baixo + 12 }}>
          <View style={{ alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: c.linha }} />
          <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 22, color: c.tinta, paddingHorizontal: 16, paddingVertical: 10 }}>
            Onde você quer jogar?
          </Text>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }}>
            {abas.map((a) => {
              const ativa = a.id === modo;
              const pts = pontos?.[a.id as Modo];
              return (
                <Pressable key={a.id} accessibilityRole="radio" accessibilityState={{ selected: ativa }}
                  onPress={() => { escolherModo(a.id as Modo); setAberta(false); }}
                  style={({ pressed }) => ({ backgroundColor: c.superficie, borderRadius: 14, padding: 14, gap: 4,
                    borderWidth: 2, borderColor: ativa ? a.cor : c.linha, borderLeftWidth: 6, borderLeftColor: a.cor,
                    opacity: pressed ? 0.8 : 1 })}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Text style={{ fontSize: 22 }}>{a.emoji}</Text>
                    <Text style={{ flex: 1, fontFamily: FONTE_TITULO, fontSize: 18, color: c.tinta }}>{a.nome}</Text>
                    {pts !== undefined ? <Text style={{ color: c.apagado, fontWeight: '700' }}>{pts} pts hoje</Text> : null}
                    {ativa ? <Text style={{ color: a.cor, fontWeight: '700' }}>✓</Text> : null}
                  </View>
                  <Text style={{ color: c.tinta, fontSize: 14, lineHeight: 19 }}>Vale: {a.conta}.</Text>
                  <Text style={{ color: c.apagado, fontSize: 13 }}>No mapa: {a.onde} perto de você.</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      </Modal>
    </>
  );
}
