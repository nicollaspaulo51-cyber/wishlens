// Peças pequenas de interface usadas em várias telas, no estilo caderno de campo (classes do NativeWind; as cores
// são as variáveis da PALETA, então o tema claro/escuro troca sozinho).
import type { ReactNode } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, View, type TextStyle, type ViewStyle } from 'react-native';

import { graoDePapel } from './efeitos/grao';

import { useCores } from '../lib/cores';

export function Titulo({ children, tamanho = 28, estilo }: { children: ReactNode; tamanho?: number; estilo?: TextStyle }) {
  return (
    <Text accessibilityRole="header" className="font-titulo text-tinta tracking-tight" style={[{ fontSize: tamanho }, estilo]}>
      {children}
    </Text>
  );
}

// Subtítulo de seção com um traço de marca-texto embaixo, como num caderno
export function Subtitulo({ children }: { children: ReactNode }) {
  return (
    <View className="mt-6 mb-2 self-start">
      <Text accessibilityRole="header" className="font-titulo-media text-[19px] text-tinta">{children}</Text>
      <View className="h-1.5 -mt-2 -mx-1 rounded-full bg-sol opacity-40" />
    </View>
  );
}

export function Apagado({ children, estilo }: { children: ReactNode; estilo?: TextStyle }) {
  return <Text className="font-texto text-apagado text-sm leading-5" style={estilo}>{children}</Text>;
}

// Anotação à mão (Caveat): só para textos curtos, como etiquetas e carimbos
export function Anotacao({ children, estilo }: { children: ReactNode; estilo?: TextStyle }) {
  return <Text className="font-mao text-destaque text-xl" style={estilo}>{children}</Text>;
}

// A ficha de papel do caderno: fundo de ficha, borda de lápis e uma sombra curta. `fita` cola um pedaço de fita adesiva.
export function Cartaz({ children, estilo, fita }: { children: ReactNode; estilo?: ViewStyle; fita?: boolean }) {
  return (
    <View className="bg-ficha border border-linha rounded-ficha p-4 shadow-sm overflow-hidden" style={estilo}>
      <Grao />
      {fita ? <View pointerEvents="none" className="absolute -top-2.5 self-center w-16 h-5 bg-sol/40 rotate-[-3deg]" /> : null}
      {children}
    </View>
  );
}

// Textura de papel por baixo do conteúdo da ficha (ladrilho de ruído do Skia, bem fraquinho)
function Grao() {
  const ladrilho = graoDePapel();
  if (!ladrilho) return null;
  return <Image source={{ uri: ladrilho }} resizeMode="repeat" pointerEvents="none" accessibilityElementsHidden
    style={[StyleSheet.absoluteFill, { opacity: 0.07 }]} />;
}

export function Botao({ titulo, aoTocar, tipo = 'primario', desativado, carregando, estilo, rotulo }: {
  titulo: string; aoTocar: () => void; tipo?: 'primario' | 'secundario'; desativado?: boolean; carregando?: boolean;
  estilo?: ViewStyle; rotulo?: string;
}) {
  const c = useCores();
  const primario = tipo === 'primario';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={rotulo ?? titulo}
      accessibilityState={{ disabled: !!desativado || !!carregando, busy: !!carregando }}
      disabled={desativado || carregando}
      onPress={aoTocar}
      className={`min-h-[52px] rounded-ficha items-center justify-center px-5 active:scale-[0.97] ${primario ? 'bg-destaque' : 'border-[1.5px] border-destaque'}`}
      style={[{ opacity: desativado ? 0.5 : 1 }, estilo]}
    >
      {carregando ? <ActivityIndicator color={primario ? c.destaqueTinta : c.destaque} /> : (
        <Text className={`font-texto-forte text-[17px] ${primario ? 'text-destaque-tinta' : 'text-destaque'}`}>{titulo}</Text>
      )}
    </Pressable>
  );
}

// Escolha de uma opção (períodos, temas): etiquetas que rolam de lado quando não cabem
export function Fichas<T extends string>({ opcoes, valor, aoEscolher, rotulo }: {
  opcoes: { valor: T; texto: string }[]; valor: T; aoEscolher: (v: T) => void; rotulo: string;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={rotulo}
      contentContainerStyle={{ gap: 8, paddingVertical: 4 }}>
      {opcoes.map((o) => {
        const ativa = o.valor === valor;
        return (
          <Pressable key={o.valor} accessibilityRole="radio" accessibilityState={{ selected: ativa }} onPress={() => aoEscolher(o.valor)}
            className={`min-h-[40px] px-3.5 rounded-full justify-center border ${ativa ? 'bg-tinta border-tinta' : 'bg-ficha border-linha'}`}>
            <Text className={`text-[15px] ${ativa ? 'font-texto-forte text-papel' : 'font-texto text-tinta'}`}>{o.texto}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
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
