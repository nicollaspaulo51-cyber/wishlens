// Zum, o mascote do WishLens: uma bolinha com olho de lente de câmera e cachecol ao vento. Corre pelo chão do
// Museu enquanto a pessoa arrasta as fotos. Personagem original: a ideia de velocidade (linhas de vento, poeira,
// corpo inclinado, pé batendo de impaciência parado) vem dos jogos de corrida, sem copiar o visual de nenhum.
import { useEffect, useRef } from 'react';
import { Animated, Easing, View } from 'react-native';

import { useCores } from '../lib/cores';
import { useMovimentoReduzido } from '../lib/movimento';

export type Passo = 'parado' | 'correndo' | 'rapido';

export function Corredor({ passo, direcao }: { passo: Passo; direcao: 1 | -1 }) {
  const c = useCores();
  const parado = useMovimentoReduzido();
  const ciclo = useRef(new Animated.Value(0)).current; // passada (correndo) ou batida do pé (parado)
  const inclina = useRef(new Animated.Value(0)).current;
  const vento = useRef(new Animated.Value(0)).current; // linhas de velocidade e poeira
  const pisca = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (parado) {
      ciclo.setValue(0);
      return;
    }
    const duracao = passo === 'rapido' ? 150 : passo === 'correndo' ? 300 : 650;
    ciclo.setValue(0);
    const laco = Animated.loop(Animated.timing(ciclo, { toValue: 1, duration: duracao, easing: Easing.linear, useNativeDriver: true }));
    laco.start();
    Animated.spring(inclina, { toValue: passo === 'rapido' ? 1 : passo === 'correndo' ? 0.5 : 0, friction: 6, useNativeDriver: true }).start();
    Animated.timing(vento, { toValue: passo === 'parado' ? 0 : 1, duration: 180, useNativeDriver: true }).start();
    return () => laco.stop();
  }, [passo, parado, ciclo, inclina, vento]);

  // Pisca de vez em quando
  useEffect(() => {
    if (parado) return;
    const laco = Animated.loop(Animated.sequence([
      Animated.delay(2600),
      Animated.timing(pisca, { toValue: 0.1, duration: 70, useNativeDriver: true }),
      Animated.timing(pisca, { toValue: 1, duration: 90, useNativeDriver: true }),
    ]));
    laco.start();
    return () => laco.stop();
  }, [parado, pisca]);

  const correndo = passo !== 'parado';
  // Correndo: as pernas vão e voltam em oposição. Parado: só o pé de trás bate no chão.
  const frente = ciclo.interpolate({ inputRange: [0, 0.5, 1], outputRange: correndo ? ['40deg', '-40deg', '40deg'] : ['0deg', '0deg', '0deg'] });
  const tras = ciclo.interpolate({ inputRange: [0, 0.5, 1], outputRange: correndo ? ['-40deg', '40deg', '-40deg'] : ['0deg', '-22deg', '0deg'] });
  const pulo = ciclo.interpolate({ inputRange: [0, 0.25, 0.5, 0.75, 1], outputRange: correndo ? [0, -4, 0, -4, 0] : [0, 0, 0, 0, 0] });
  const giro = inclina.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '16deg'] });
  const cachecol = ciclo.interpolate({ inputRange: [0, 0.5, 1], outputRange: ['-8deg', '8deg', '-8deg'] });

  return (
    <View pointerEvents="none" accessibilityElementsHidden importantForAccessibility="no-hide-descendants"
      style={{ width: 96, height: 74, transform: [{ scaleX: direcao }] }}>
      {/* Linhas de vento atrás */}
      <Animated.View style={{ position: 'absolute', left: 0, top: 22, gap: 7, opacity: vento }}>
        {[22, 30, 16].map((w, i) => (
          <View key={i} style={{ width: w, height: 3, borderRadius: 2, marginLeft: 22 - w + i * 4, backgroundColor: c.apagado, opacity: 0.6 }} />
        ))}
      </Animated.View>
      {/* Poeira saindo dos pés */}
      <Animated.View style={{ position: 'absolute', left: 14, bottom: 0, flexDirection: 'row', gap: 3, opacity: vento,
        transform: [{ scale: ciclo.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1.2] }) }] }}>
        <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: c.linha }} />
        <View style={{ width: 6, height: 6, borderRadius: 3, marginTop: 3, backgroundColor: c.linha }} />
      </Animated.View>

      <Animated.View style={{ position: 'absolute', left: 30, bottom: 0, width: 56, height: 74,
        transform: [{ translateY: pulo }, { rotate: giro }] }}>
        {/* Pernas (giram a partir do quadril) com tênis amarelo */}
        {[tras, frente].map((ang, i) => (
          <Animated.View key={i} style={{ position: 'absolute', left: 18 + i * 10, top: 50, width: 6, height: 16, transformOrigin: 'top',
            transform: [{ rotate: ang }] }}>
            <View style={{ flex: 1, backgroundColor: c.tinta, borderRadius: 3 }} />
            <View style={{ position: 'absolute', bottom: -4, left: -2, width: 14, height: 7, borderRadius: 4, backgroundColor: c.sol }} />
          </Animated.View>
        ))}
        {/* Cachecol ao vento */}
        <Animated.View style={{ position: 'absolute', left: -6, top: 30, width: 22, height: 7, borderRadius: 4, backgroundColor: c.sol,
          transformOrigin: 'right', transform: [{ rotate: cachecol }] }} />
        {/* Corpo, barriga e o flash da câmera na cabeça */}
        <View style={{ position: 'absolute', left: 14, top: 0, width: 16, height: 9, borderTopLeftRadius: 4, borderTopRightRadius: 4,
          backgroundColor: c.sol }} />
        <View style={{ position: 'absolute', left: 4, top: 6, width: 48, height: 48, borderRadius: 24, backgroundColor: c.destaque }} />
        <View style={{ position: 'absolute', left: 16, top: 30, width: 26, height: 20, borderRadius: 13, backgroundColor: '#FFFFFF', opacity: 0.85 }} />
        {/* Olho de lente: aro escuro, íris e reflexo */}
        <Animated.View style={{ position: 'absolute', left: 28, top: 13, width: 20, height: 20, borderRadius: 10, backgroundColor: '#FFFFFF',
          borderWidth: 3, borderColor: '#1B1B1B', alignItems: 'center', justifyContent: 'center', transform: [{ scaleY: pisca }] }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#1B1B1B' }} />
          <View style={{ position: 'absolute', top: 2, right: 3, width: 3, height: 3, borderRadius: 2, backgroundColor: '#FFFFFF' }} />
        </Animated.View>
        {/* Braço */}
        <Animated.View style={{ position: 'absolute', left: 22, top: 32, width: 5, height: 13, borderRadius: 3, backgroundColor: c.tinta,
          transformOrigin: 'top', transform: [{ rotate: tras }] }} />
      </Animated.View>
    </View>
  );
}
