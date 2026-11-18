// Resultado da avaliação: pontos da foto aceita ou motivo da recusa.
import { useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Text, View } from 'react-native';

import type { Cartao } from '../lib/api';
import { useCores } from '../lib/cores';
import { Carimbo } from './efeitos/Carimbo';
import { Apagado } from './ui';
import { IconeTema } from './icones/Icone';

export function CartaoPontos({ cartao }: { cartao: Cartao }) {
  const c = useCores();
  const colar = useRef(new Animated.Value(0)).current;
  const juizes = cartao.juizes?.replaceAll('\u2714', 'confirma').replaceAll('\u2716', 'diverge');

  useEffect(() => {
    // A ficha aparece sem animação para quem pediu menos movimento no aparelho.
    AccessibilityInfo.isReduceMotionEnabled().then((menos) => {
      if (menos) colar.setValue(1);
      else Animated.spring(colar, { toValue: 1, friction: 6, tension: 80, useNativeDriver: true }).start();
    });
    AccessibilityInfo.announceForAccessibility(
      cartao.aceita ? `Valeu: mais ${cartao.pontos} pontos` : `Não valeu: ${cartao.motivo ?? ''}`,
    );
  }, [cartao, colar]);

  if (!cartao.aceita) {
    return (
      <View className="bg-ficha border border-linha rounded-ficha p-4 gap-1.5">
        <View className="flex-row items-center justify-between gap-2 flex-wrap">
          <Text className="font-texto text-[18px] text-tinta"><Text className="font-numero text-[40px]">0</Text> pontos</Text>
          <Carimbo aceita={false} cor={c.recusa} />
        </View>
        <Text className="font-texto text-tinta text-[16px] leading-[22px]" >
          <Text className="font-texto-forte" >Não valeu: </Text>{cartao.motivo}.
        </Text>
        <Apagado>Vale foto tirada agora, de algo real na sua frente, de um dos temas.</Apagado>
        <Apagado estilo={{ fontSize: 12, marginTop: 4 }}>{juizes}</Apagado>
      </View>
    );
  }

  const tema = cartao.tema!;
  const achado = cartao.achado.charAt(0).toUpperCase() + cartao.achado.slice(1);
  return (
    <Animated.View style={{ opacity: colar, transform: [{ scale: colar.interpolate({ inputRange: [0, 1], outputRange: [1.15, 1] }) }] }}>
      <View className="bg-ficha border border-linha rounded-ficha p-4">
        <View className="flex-row justify-between items-center gap-2">
          <View className="flex-1 flex-row items-center gap-2">
            <IconeTema id={tema.id} tamanho={24} cor={c.tinta} />
            <Text className="shrink font-texto text-apagado">{tema.nome}</Text>
          </View>
          <Text className="font-numero text-[30px] text-destaque">+{cartao.pontos}</Text>
        </View>
        <Text className="font-titulo text-[26px] text-tinta mt-[8px]">{achado}</Text>
        <View className="flex-row flex-wrap gap-[6px] mt-[12px]">
          {(cartao.partes ?? []).map((p) => <Selo key={p} texto={p} />)}
          {(cartao.bonus ?? []).map((b) => <Selo key={b} texto={b} bonus />)}
        </View>
        <Apagado estilo={{ marginTop: 10 }}>{cartao.destaque}</Apagado>
        <Apagado estilo={{ fontSize: 12, marginTop: 6 }}>{juizes}</Apagado>
        <View className="mt-3"><Carimbo aceita cor={c.destaque} /></View>
      </View>
    </Animated.View>
  );
}

function Selo({ texto, bonus }: { texto: string; bonus?: boolean }) {
  const c = useCores();
  return (
    <View style={{ backgroundColor: c.suave, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 }}>
      <Text className="font-texto-forte" style={{ color: bonus ? c.destaque : c.tinta, fontSize: 13 }}>
        {texto.split(/([+×]?\d+(?:[.,]\d+)?%?)/u).map((parte, indice) => (
          indice % 2 ? <Text key={indice} className="font-numero">{parte}</Text> : parte
        ))}
      </Text>
    </View>
  );
}
