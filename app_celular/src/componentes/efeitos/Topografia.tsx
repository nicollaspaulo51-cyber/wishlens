// Curvas de nível de mapa topográfico, geradas por conta: círculos tortos em volta de dois "morros".
import { Canvas, Group, Path, Skia } from '@shopify/react-native-skia';
import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { useCores } from '../../lib/cores';

function morro(cx: number, cy: number, niveis: number, passo: number, semente: number) {
  const caminho = Skia.PathBuilder.Make();
  for (let n = 1; n <= niveis; n++) {
    const r0 = n * passo;
    for (let i = 0; i <= 72; i++) {
      const a = (i / 72) * Math.PI * 2;
      const r = r0 * (1 + 0.16 * Math.sin(3 * a + semente + n * 0.4) + 0.08 * Math.sin(5 * a - semente * 1.7 + n * 0.25));
      const x = cx + r * Math.cos(a);
      const y = cy + r * 0.78 * Math.sin(a);
      if (i === 0) caminho.moveTo(x, y);
      else caminho.lineTo(x, y);
    }
    caminho.close();
  }
  return caminho.build();
}

export function Topografia() {
  const c = useCores();
  const [t, setT] = useState({ w: 0, h: 0 });
  const caminhos = useMemo(() => (t.w ? [morro(t.w * 0.18, t.h * 0.28, 9, t.w * 0.06, 1.3), morro(t.w * 0.9, t.h * 0.75, 11, t.w * 0.07, 4.1)] : []),
    [t.w, t.h]);
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill} onLayout={(e) => setT({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
      {t.w ? (
        <Canvas style={StyleSheet.absoluteFill}>
          <Group opacity={0.08}>
            {caminhos.map((caminho, i) => <Path key={i} path={caminho} style="stroke" strokeWidth={1.2} color={c.linha} />)}
          </Group>
        </Canvas>
      ) : null}
    </View>
  );
}
