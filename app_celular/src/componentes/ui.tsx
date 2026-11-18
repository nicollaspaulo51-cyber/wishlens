// Peças comuns do mapa topográfico; as classes do NativeWind usam as cores do tema ativo.
import type { ComponentProps, ReactNode } from 'react';
import { vars } from 'nativewind';
import { ActivityIndicator, Animated, Modal, Pressable, ScrollView, StyleSheet, Text, View, type TextStyle, type ViewStyle } from 'react-native';

import { IconeTema } from './icones/Icone';

import { useCores, variaveis } from '../lib/cores';
import { useTransicao } from '../lib/movimento';

// Modal com as cores do tema: no navegador o Modal fica fora da raiz do app e não herda as variáveis CSS do
// _layout.tsx, então as classes (text-tinta...) caíam no preto padrão sobre o fundo escuro.
export function ModalTema({ children, ...props }: ComponentProps<typeof Modal>) {
  const c = useCores();
  return (
    <Modal {...props}>
      <View style={[{ flex: 1 }, vars(variaveis(c))]}>{children}</View>
    </Modal>
  );
}

export function Titulo({ children, tamanho = 28, estilo }: { children: ReactNode; tamanho?: number; estilo?: TextStyle }) {
  return (
    <Text accessibilityRole="header" className="font-titulo text-tinta tracking-tight" style={[{ fontSize: tamanho }, estilo]}>
      {children}
    </Text>
  );
}

export function Subtitulo({ children }: { children: ReactNode }) {
  return (
    <View className="mt-6 mb-2 self-start">
      <Text accessibilityRole="header" className="font-titulo-media text-[19px] text-tinta">{children}</Text>
    </View>
  );
}

export function Apagado({ children, estilo }: { children: ReactNode; estilo?: TextStyle }) {
  return <Text className="font-texto text-apagado text-sm leading-5" style={estilo}>{children}</Text>;
}

export function Cartaz({ children, estilo }: { children: ReactNode; estilo?: ViewStyle }) {
  return (
    <View className="bg-ficha border border-linha rounded-ficha p-4" style={estilo}>
      {children}
    </View>
  );
}

export function Botao({ titulo, aoTocar, tipo = 'primario', desativado, carregando, estilo, rotulo }: {
  titulo: ReactNode; aoTocar: () => void; tipo?: 'primario' | 'secundario' | 'localizacao'; desativado?: boolean; carregando?: boolean;
  estilo?: ViewStyle; rotulo?: string;
}) {
  const c = useCores();
  const primario = tipo === 'primario';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={rotulo ?? (typeof titulo === 'string' ? titulo : undefined)}
      accessibilityState={{ disabled: !!desativado || !!carregando, busy: !!carregando }}
      disabled={desativado || carregando}
      onPress={aoTocar}
      className={`min-h-[52px] rounded-ficha items-center justify-center px-5 active:scale-[0.97] ${primario ? 'bg-destaque' : tipo === 'localizacao' ? 'bg-ficha border-[1.5px] border-agua' : 'border-[1.5px] border-destaque'}`}
      style={[{ opacity: desativado ? 0.5 : 1 }, estilo]}
    >
      {carregando ? <ActivityIndicator color={primario ? c.destaqueTinta : tipo === 'localizacao' ? c.agua : c.destaque} /> : (
        <Text className={`font-texto-forte text-[17px] ${primario ? 'text-destaque-tinta' : tipo === 'localizacao' ? 'text-agua' : 'text-destaque'}`}>{titulo}</Text>
      )}
    </Pressable>
  );
}

// Escolha de uma opção (períodos, temas): etiquetas que rolam de lado quando não cabem
// `icone` identifica o tema ou a aba e aparece antes do texto.
export function Fichas<T extends string>({ opcoes, valor, aoEscolher, rotulo }: {
  opcoes: { valor: T; texto: string; icone?: { id: string } }[]; valor: T; aoEscolher: (v: T) => void; rotulo: string;
}) {
  return (
    // alignItems: as etiquetas não esticam até a altura da rolagem (no Android ficavam enormes)
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={rotulo}
      contentContainerStyle={{ gap: 8, paddingVertical: 4, alignItems: 'center' }}>
      {opcoes.map((opcao) => (
        <Ficha key={opcao.valor} texto={opcao.texto} icone={opcao.icone?.id} ativa={opcao.valor === valor} aoTocar={() => aoEscolher(opcao.valor)} />
      ))}
    </ScrollView>
  );
}

function Ficha({ texto, icone, ativa, aoTocar }: { texto: string; icone?: string; ativa: boolean; aoTocar: () => void }) {
  const c = useCores();
  const opacidade = useTransicao(ativa ? 1 : 0, 150);
  return (
    <Pressable accessibilityRole="radio" accessibilityState={{ selected: ativa }} onPress={aoTocar}
      className={`min-h-[44px] min-w-[44px] px-3.5 rounded-ficha flex-row items-center gap-1.5 border bg-ficha ${ativa ? 'border-apagado' : 'border-linha'}`}>
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { borderRadius: 5, backgroundColor: c.suave, opacity: opacidade }]} />
      {icone ? <IconeTema id={icone} tamanho={18} cor={ativa ? c.tinta : c.apagado} /> : null}
      <Text className={`text-[15px] text-tinta ${ativa ? 'font-texto-forte' : 'font-texto'}`}>{texto}</Text>
    </Pressable>
  );
}

export function Aviso({ texto, aoTentar }: { texto: string; aoTentar?: () => void }) {
  return (
    <Cartaz estilo={{ gap: 12 }}>
      <Text className="font-texto text-tinta text-[15px] leading-[21px]">{texto}</Text>
      {aoTentar ? <Botao titulo="Tentar de novo" tipo="secundario" aoTocar={aoTentar} /> : null}
    </Cartaz>
  );
}
