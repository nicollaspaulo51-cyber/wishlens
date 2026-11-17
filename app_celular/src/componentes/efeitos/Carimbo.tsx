// Carimbo de tinta ("ACEITA" / "RECUSADA") que desce e bate na ficha: borda tremida (DiscretePathEffect do Skia)
// e letra de mão. A batida é uma mola do Reanimated; o celular vibra quando o carimbo encosta no papel.
import { Canvas, DiscretePathEffect, Group, Paint, RoundedRect, Text as TextoSkia, useFont } from '@shopify/react-native-skia';
import * as Haptics from 'expo-haptics';
import { useEffect } from 'react';
import Reanimated, { runOnJS, useAnimatedStyle, useSharedValue, withDelay, withSpring, withTiming } from 'react-native-reanimated';

import { useMovimentoReduzido } from '../../lib/movimento';

const LARGURA = 150;
const ALTURA = 56;

export function Carimbo({ aceita, cor }: { aceita: boolean; cor: string }) {
  const fonte = useFont(require('@expo-google-fonts/caveat/700Bold/Caveat_700Bold.ttf'), 30);
  const parado = useMovimentoReduzido();
  const desce = useSharedValue(parado ? 1 : 0);
  const vibrar = () => Haptics.impactAsync(aceita ? Haptics.ImpactFeedbackStyle.Heavy : Haptics.ImpactFeedbackStyle.Light).catch(() => {});

  useEffect(() => {
    if (parado) return;
    desce.value = withDelay(350, withSpring(1, { damping: 9, stiffness: 180, mass: 0.7 }, (fim) => {
      if (fim) runOnJS(vibrar)();
    }));
  }, [parado]); // uma batida por cartão (o cartão é montado de novo a cada foto)

  const estilo = useAnimatedStyle(() => ({
    opacity: withTiming(desce.value > 0.05 ? 1 : 0, { duration: 80 }),
    transform: [{ scale: 2.4 - 1.4 * desce.value }, { rotate: `${-14 + 4 * desce.value}deg` }],
  }));
  const texto = aceita ? 'ACEITA' : 'RECUSADA';
  const largura = fonte ? fonte.measureText(texto).width : 0;
  return (
    <Reanimated.View pointerEvents="none" accessible accessibilityLabel={`Carimbo: ${texto.toLowerCase()}`} style={[{ width: LARGURA, height: ALTURA }, estilo]}>
      <Canvas style={{ width: LARGURA, height: ALTURA }}>
        <Group opacity={0.85}>
          <RoundedRect x={4} y={4} width={LARGURA - 8} height={ALTURA - 8} r={8} style="stroke" strokeWidth={3.5} color={cor}>
            <DiscretePathEffect length={6} deviation={1.6} />
          </RoundedRect>
          {fonte ? (
            <TextoSkia x={(LARGURA - largura) / 2} y={ALTURA / 2 + 10} text={texto} font={fonte} color={cor}>
              <Paint style="stroke" strokeWidth={0.6} color={cor}><DiscretePathEffect length={3} deviation={0.8} /></Paint>
            </TextoSkia>
          ) : null}
        </Group>
      </Canvas>
    </Reanimated.View>
  );
}
