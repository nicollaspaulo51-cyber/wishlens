// Peças comuns do mapa topográfico; as classes do NativeWind usam as cores do tema ativo.
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View, type TextStyle, type ViewStyle } from 'react-native';

import { IconeTema } from './icones/Icone';

import { useCores } from '../lib/cores';

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
  titulo: ReactNode; aoTocar: () => void; tipo?: 'primario' | 'secundario'; desativado?: boolean; carregando?: boolean;
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
// `icone` identifica o tema ou a aba e aparece antes do texto.
export function Fichas<T extends string>({ opcoes, valor, aoEscolher, rotulo }: {
  opcoes: { valor: T; texto: string; icone?: { id: string } }[]; valor: T; aoEscolher: (v: T) => void; rotulo: string;
}) {
  const c = useCores();
  return (
    // alignItems: as etiquetas não esticam até a altura da rolagem (no Android ficavam enormes)
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={rotulo}
      contentContainerStyle={{ gap: 8, paddingVertical: 4, alignItems: 'center' }}>
      {opcoes.map((o) => {
        const ativa = o.valor === valor;
        return (
          <Pressable key={o.valor} accessibilityRole="radio" accessibilityState={{ selected: ativa }} onPress={() => aoEscolher(o.valor)}
            className={`min-h-[44px] min-w-[44px] px-3.5 rounded-ficha flex-row items-center gap-1.5 border ${ativa ? 'bg-suave border-apagado' : 'bg-ficha border-linha'}`}>
            {o.icone ? <IconeTema id={o.icone.id} tamanho={18} cor={ativa ? c.tinta : c.apagado} /> : null}
            <Text className={`text-[15px] ${ativa ? 'font-texto-forte text-tinta' : 'font-texto text-tinta'}`}>{o.texto}</Text>
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
