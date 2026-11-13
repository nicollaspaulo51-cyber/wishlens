// Peças pequenas de interface usadas em várias telas.
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type TextStyle, type ViewStyle } from 'react-native';

import { FONTE_TITULO, FONTE_TITULO_MEDIA, useCores } from '../lib/cores';

export function Titulo({ children, tamanho = 28, estilo }: { children: ReactNode; tamanho?: number; estilo?: TextStyle }) {
  const c = useCores();
  return (
    <Text accessibilityRole="header" style={[{ fontFamily: FONTE_TITULO, fontSize: tamanho, color: c.tinta, letterSpacing: -0.5 }, estilo]}>
      {children}
    </Text>
  );
}

export function Subtitulo({ children }: { children: ReactNode }) {
  const c = useCores();
  return (
    <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO_MEDIA, fontSize: 19, color: c.tinta, marginTop: 24, marginBottom: 8 }}>
      {children}
    </Text>
  );
}

export function Apagado({ children, estilo }: { children: ReactNode; estilo?: TextStyle }) {
  const c = useCores();
  return <Text style={[{ color: c.apagado, fontSize: 14, lineHeight: 20 }, estilo]}>{children}</Text>;
}

export function Cartaz({ children, estilo }: { children: ReactNode; estilo?: ViewStyle }) {
  const c = useCores();
  return (
    <View style={[{ backgroundColor: c.superficie, borderColor: c.linha, borderWidth: StyleSheet.hairlineWidth, borderRadius: 14, padding: 16 }, estilo]}>
      {children}
    </View>
  );
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
      style={({ pressed }) => [{
        minHeight: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20,
        backgroundColor: primario ? c.destaque : 'transparent', borderWidth: primario ? 0 : 1.5, borderColor: c.destaque,
        opacity: desativado ? 0.5 : pressed ? 0.85 : 1,
      }, estilo]}
    >
      {carregando ? <ActivityIndicator color={primario ? c.destaqueTinta : c.destaque} /> : (
        <Text style={{ color: primario ? c.destaqueTinta : c.destaque, fontSize: 17, fontWeight: '700' }}>{titulo}</Text>
      )}
    </Pressable>
  );
}

// Escolha de uma opção (períodos, temas). Rola de lado quando não cabe.
export function Fichas<T extends string>({ opcoes, valor, aoEscolher, rotulo }: {
  opcoes: { valor: T; texto: string }[]; valor: T; aoEscolher: (v: T) => void; rotulo: string;
}) {
  const c = useCores();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={rotulo}
      contentContainerStyle={{ gap: 8, paddingVertical: 4 }}>
      {opcoes.map((o) => {
        const ativa = o.valor === valor;
        return (
          <Pressable key={o.valor} accessibilityRole="radio" accessibilityState={{ selected: ativa }} onPress={() => aoEscolher(o.valor)}
            style={{ minHeight: 40, paddingHorizontal: 14, borderRadius: 20, justifyContent: 'center',
              backgroundColor: ativa ? c.tinta : c.superficie, borderWidth: 1, borderColor: ativa ? c.tinta : c.linha }}>
            <Text style={{ color: ativa ? c.fundo : c.tinta, fontWeight: ativa ? '700' : '500', fontSize: 15 }}>{o.texto}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function Aviso({ texto, aoTentar }: { texto: string; aoTentar?: () => void }) {
  const c = useCores();
  return (
    <Cartaz estilo={{ gap: 12 }}>
      <Text style={{ color: c.tinta, fontSize: 15, lineHeight: 21 }}>{texto}</Text>
      {aoTentar ? <Botao titulo="Tentar de novo" tipo="secundario" aoTocar={aoTentar} /> : null}
    </Cartaz>
  );
}
