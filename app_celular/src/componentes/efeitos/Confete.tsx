// Confete de papel picado quando você ganha pontos: tirinhas que caem girando, desenhadas pelo Skia. Uma passagem
// de tempo do Reanimated move tudo; cada cor vira um caminho só (4 caminhos por quadro, leve para o celular).
import { Canvas, Path, Skia } from '@shopify/react-native-skia';
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Easing, useDerivedValue, useSharedValue, withTiming } from 'react-native-reanimated';

import { useMovimentoReduzido } from '../../lib/movimento';

const CORES = ['#FFC83D', '#136B4C', '#E5484D', '#2a78d6'];
const PEDACOS = 44;
const DURACAO = 2200;

type Pedaco = { x: number; vx: number; atraso: number; giro: number; tam: number; cor: number };

export function Confete({ disparo }: { disparo: number }) {
  const parado = useMovimentoReduzido();
  const [t, setT] = useState({ w: 0, h: 0 });
  const tempo = useSharedValue(1);
  const pedacos = useMemo<Pedaco[]>(() => Array.from({ length: PEDACOS }, (_, i) => ({
    x: Math.random(), vx: (Math.random() - 0.5) * 0.25, atraso: Math.random() * 0.25, giro: 2 + Math.random() * 5,
    tam: 6 + Math.random() * 6, cor: i % CORES.length,
  })), [disparo]); // pedaços novos a cada disparo

  useEffect(() => {
    if (!disparo || parado) return;
    tempo.value = 0;
    tempo.value = withTiming(1, { duration: DURACAO, easing: Easing.out(Easing.quad) });
  }, [disparo, parado, tempo]);

  // CORES tem tamanho fixo: são sempre os mesmos 4 hooks, na mesma ordem
  const caminhos = CORES.map((_, k) =>
    useDerivedValue(() => {
      const p = Skia.PathBuilder.Make();
      if (tempo.value >= 1 || !t.w) return p.build();
      for (const d of pedacos) {
        if (d.cor !== k) continue;
        const u = Math.max(0, (tempo.value - d.atraso) / (1 - d.atraso));
        if (u <= 0) continue;
        const cx = (d.x + d.vx * u) * t.w;
        const cy = -20 + u * (t.h + 40) * (0.6 + 0.4 * u);
        const a = d.giro * u * Math.PI * 2;
        const lx = Math.cos(a) * d.tam, ly = Math.sin(a) * d.tam * 0.45;
        p.moveTo(cx - lx, cy - ly);
        p.lineTo(cx + ly, cy - lx * 0.35);
        p.lineTo(cx + lx, cy + ly);
        p.lineTo(cx - ly, cy + lx * 0.35);
        p.close();
      }
      return p.build();
    }, [t, pedacos]));

  if (parado) return null;
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill} onLayout={(e) => setT({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
      <Canvas style={StyleSheet.absoluteFill}>
        {caminhos.map((c, k) => <Path key={k} path={c} color={CORES[k]} />)}
      </Canvas>
    </View>
  );
}
