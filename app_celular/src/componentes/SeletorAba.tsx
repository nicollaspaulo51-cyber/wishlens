// Troca de aba do jogo: um botão pequeno ("🗺️ Mapa livre ▾") que abre uma folha de baixo com as 4 abas,
// cada uma com o que vale nela, onde achar no mapa e os seus pontos de hoje.
import { useState } from 'react';
import { Modal, Pressable, ScrollView, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type Modo } from '../lib/api';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { escolherModo, NOME_LIVRE, useModo } from '../lib/modo';
import { useDados } from '../lib/useDados';
import { IconeTema } from './icones/Icone';

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
        <IconeTema id={atual.id} emoji={atual.emoji} tamanho={18} cor={escuro ? '#fff' : atual.cor} />
        <Text className="font-texto-forte" style={{ color: escuro ? '#fff' : c.tinta, fontWeight: '700', fontSize: 15 }}>{atual.nome}</Text>
        <Text className="font-texto" style={{ color: escuro ? '#fff' : c.apagado, fontSize: 12 }}>▼</Text>
      </Pressable>

      <Modal visible={aberta} transparent animationType="slide" onRequestClose={() => setAberta(false)}>
        <Pressable accessibilityLabel="Fechar" onPress={() => setAberta(false)} style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} />
        <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 22, borderTopRightRadius: 22, maxHeight: '80%',
          paddingTop: 10, paddingBottom: baixo + 12 }}>
          <View className="self-center w-[40px] h-[5px] rounded-[3px] bg-linha" />
          <Text accessibilityRole="header" className="font-titulo text-[22px] text-tinta px-[16px] py-[10px]">
            Onde você quer jogar?
          </Text>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 16, gap: 10 }}>
            {abas.map((a) => {
              const ativa = a.id === modo;
              const pts = pontos?.[a.id as Modo];
              return (
                <Pressable key={a.id} accessibilityRole="radio" accessibilityState={{ selected: ativa }}
                  onPress={() => { escolherModo(a.id as Modo); setAberta(false); }}
                  className="active:opacity-80"
                  style={{ backgroundColor: c.superficie, borderRadius: 14, padding: 14, gap: 4,
                    borderWidth: 2, borderColor: ativa ? a.cor : c.linha, borderLeftWidth: 6, borderLeftColor: a.cor }}>
                  <View className="flex-row items-center gap-[8px]">
                    <IconeTema id={a.id} emoji={a.emoji} tamanho={24} cor={a.cor} />
                    <Text className="flex-1 font-titulo text-[18px] text-tinta">{a.nome}</Text>
                    {pts !== undefined ? <Text className="font-texto-forte text-apagado" >{pts} pts hoje</Text> : null}
                    {ativa ? <Text className="font-texto-forte" style={{ color: a.cor, fontWeight: '700' }}>✓</Text> : null}
                  </View>
                  <Text className="font-texto text-tinta text-[14px] leading-[19px]" >Vale: {a.conta}.</Text>
                  <Text className="font-texto text-apagado text-[13px]" >No mapa: {a.onde} perto de você.</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      </Modal>
    </>
  );
}
