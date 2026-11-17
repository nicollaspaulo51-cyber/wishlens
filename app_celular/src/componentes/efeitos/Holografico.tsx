// Brilho holográfico das figurinhas: uma faixa de arco-íris que atravessa o cartão de tempos em tempos (Skia +
// Reanimated). Vai dentro de um View com overflow 'hidden'. Substitui o Brilho antigo, feito com faixas de View.
import { Canvas, LinearGradient, Rect, vec } from '@shopify/react-native-skia';
import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Easing, useDerivedValue, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from 'react-native-reanimated';

import { useMovimentoReduzido } from '../../lib/movimento';

const ARCO = ['#ffffff00', '#ff7ab633', '#ffe08a66', '#7ef0c466', '#7ab8ff55', '#ffffff00'];

export function Holografico({ pausa = 3200, atraso = 0 }: { pausa?: number; atraso?: number }) {
  const parado = useMovimentoReduzido();
  const [t, setT] = useState({ w: 0, h: 0 });
  const passo = useSharedValue(0);
  useEffect(() => {
    if (parado) return;
    passo.value = withDelay(atraso, withRepeat(withSequence(
      withTiming(1, { duration: 1300, easing: Easing.inOut(Easing.quad) }), withDelay(pausa, withTiming(0, { duration: 0 }))), -1));
  }, [parado, pausa, atraso, passo]);
  const ini = useDerivedValue(() => vec(-t.w + passo.value * t.w * 2.2, 0), [t]);
  const fim = useDerivedValue(() => vec(-t.w + passo.value * t.w * 2.2 + t.w * 0.7, t.h), [t]);
  if (parado) return null;
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill} onLayout={(e) => setT({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
      {t.w ? (
        <Canvas style={StyleSheet.absoluteFill}>
          <Rect x={0} y={0} width={t.w} height={t.h}>
            <LinearGradient start={ini} end={fim} colors={ARCO} />
          </Rect>
        </Canvas>
      ) : null}
    </View>
  );
}
