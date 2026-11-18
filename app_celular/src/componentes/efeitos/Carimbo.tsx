// Selo reto do resultado do juiz ("aceita" / "recusada"), na cor recebida. O celular vibra quando o selo aparece.
import * as Haptics from 'expo-haptics';
import { useEffect } from 'react';
import { Animated, Text } from 'react-native';

import { useTransicao } from '../../lib/movimento';

export function Carimbo({ aceita, cor }: { aceita: boolean; cor: string }) {
  const texto = aceita ? 'aceita' : 'recusada';
  const escala = useTransicao(1, 150, { inicial: 0.92 });
  useEffect(() => {
    Haptics.impactAsync(aceita ? Haptics.ImpactFeedbackStyle.Heavy : Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  }, [aceita]);
  return (
    <Animated.View pointerEvents="none" accessible accessibilityLabel={`Resultado: ${texto}`}
      style={{ paddingVertical: 4, transform: [{ scale: escala }] }}>
      <Text className="font-texto-forte text-xs uppercase" style={{ color: cor }}>{texto}</Text>
    </Animated.View>
  );
}
