// Resultado de uma foto: a figurinha que "cola" (aceita) ou o motivo da recusa.
import { useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Text, View } from 'react-native';

import type { Cartao } from '../lib/api';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { Brilho } from '../lib/movimento';
import { Apagado } from './ui';
import { IconeTema } from './icones/Icone';

export function CartaoPontos({ cartao }: { cartao: Cartao }) {
  const c = useCores();
  const colar = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // A figurinha cola com um giro curto; sem animação para quem pediu menos movimento no aparelho
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
      <View style={{ backgroundColor: c.superficie, borderRadius: 16, padding: 20, borderLeftWidth: 5, borderLeftColor: c.recusa, gap: 6 }}>
        <Text className="font-titulo text-[40px] text-tinta">0 <Text className="font-texto text-[18px]" >pontos</Text></Text>
        <Text className="font-texto text-tinta text-[16px] leading-[22px]" >
          <Text className="font-texto-forte" >Não valeu: </Text>{cartao.motivo}.
        </Text>
        <Apagado>Vale foto tirada agora, de algo real na sua frente, de um dos temas.</Apagado>
        <Apagado estilo={{ fontSize: 12, marginTop: 4 }}>{cartao.juizes}</Apagado>
      </View>
    );
  }

  const tema = cartao.tema!;
  const achado = cartao.achado.charAt(0).toUpperCase() + cartao.achado.slice(1);
  const giro = colar.interpolate({ inputRange: [0, 1], outputRange: ['-8deg', '-2deg'] });
  return (
    <Animated.View style={{ opacity: colar, transform: [{ scale: colar.interpolate({ inputRange: [0, 1], outputRange: [1.15, 1] }) }, { rotate: giro }] }}>
      <View style={{ borderRadius: 8, borderWidth: 6, borderColor: '#FFFFFF', backgroundColor: c.figurinha,
        shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 5 }}>
      <View className="p-[16px] rounded-[2px] overflow-hidden">
        <View className="flex-row justify-between items-start">
          <IconeTema id={tema.id} emoji={tema.emoji} tamanho={40} cor={tema.cor} />
          <View className="bg-sol rounded-[10px] px-[12px] py-[4px]">
            <Text className="font-titulo text-[30px] text-sol-tinta">+{cartao.pontos}</Text>
          </View>
        </View>
        <Text className="font-titulo text-[26px] text-tinta mt-[8px]">{achado}</Text>
        <Apagado>{tema.nome}</Apagado>
        <View className="flex-row flex-wrap gap-[6px] mt-[12px]">
          {(cartao.partes ?? []).map((p) => <Selo key={p} texto={p} />)}
          {(cartao.bonus ?? []).map((b) => <Selo key={b} texto={b} bonus />)}
        </View>
        <Apagado estilo={{ marginTop: 10 }}>{cartao.destaque}</Apagado>
        <Apagado estilo={{ fontSize: 12, marginTop: 6 }}>{cartao.juizes}</Apagado>
        <Brilho pausa={2500} atraso={500} />
      </View>
      </View>
    </Animated.View>
  );
}

function Selo({ texto, bonus }: { texto: string; bonus?: boolean }) {
  const c = useCores();
  return (
    <View style={{ backgroundColor: bonus ? c.sol : c.suave, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 }}>
      <Text className="font-texto-forte" style={{ color: bonus ? c.solTinta : c.tinta, fontSize: 13, fontWeight: '600' }}>{texto}</Text>
    </View>
  );
}
