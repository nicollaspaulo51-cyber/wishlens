// Animações do app (Animated do React Native, no driver nativo). Todas param com "reduzir movimento" ligado no celular.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useIsFocused } from 'expo-router';
import { AccessibilityInfo, Animated, Dimensions, Easing, View, type StyleProp, type ViewStyle } from 'react-native';

export function useMovimentoReduzido() {
  const [reduzido, setReduzido] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduzido).catch(() => {});
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduzido);
    return () => sub.remove();
  }, []);
  return reduzido;
}

// Conta as visitas a uma aba: as abas ficam montadas, então as entradas (Surge) usam isto como `chave` para
// animar de novo cada vez que a pessoa volta para a aba
export function useVisita() {
  const focada = useIsFocused();
  const [n, setN] = useState(0);
  useEffect(() => {
    if (focada) setN((x) => x + 1);
  }, [focada]);
  return n;
}

// Vai de 0 a 1 com mola quando aparece (de novo a cada mudança de `chave`)
export function useEntrada(atraso = 0, chave?: unknown) {
  const v = useRef(new Animated.Value(0)).current;
  const parado = useMovimentoReduzido();
  useEffect(() => {
    if (parado) {
      v.setValue(1);
      return;
    }
    v.setValue(0);
    const a = Animated.sequence([Animated.delay(atraso), Animated.spring(v, { toValue: 1, friction: 7, tension: 60, useNativeDriver: true })]);
    a.start();
    return () => a.stop();
  }, [chave, parado, atraso, v]);
  return v;
}

// Vai de 0 a 1 sem parar (com pausa no fim), para brilhos e pulsos
export function useLaco(duracao: number, pausa = 0) {
  const v = useRef(new Animated.Value(0)).current;
  const parado = useMovimentoReduzido();
  useEffect(() => {
    v.setValue(0);
    if (parado) return;
    const a = Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 1, duration: duracao, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      Animated.delay(pausa),
    ]));
    a.start();
    return () => a.stop();
  }, [parado, duracao, pausa, v]);
  return { v, parado };
}

// Aparece subindo um pouco e crescendo; `ordem` escalona listas
export function Surge({ children, ordem = 0, estilo, chave }: { children: ReactNode; ordem?: number; estilo?: StyleProp<ViewStyle>; chave?: unknown }) {
  const v = useEntrada(Math.min(ordem, 12) * 60, chave);
  return (
    <Animated.View style={[estilo, { opacity: v, transform: [
      { translateY: v.interpolate({ inputRange: [0, 1], outputRange: [14, 0] }) },
      { scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.92, 1] }) },
    ] }]}>
      {children}
    </Animated.View>
  );
}

// Brilho de figurinha holográfica: uma faixa clara que atravessa o cartão de tempos em tempos.
// Vai dentro de um View com overflow 'hidden'.
const LARGURA = Dimensions.get('window').width;
export function Brilho({ pausa = 3200, atraso = 0 }: { pausa?: number; atraso?: number }) {
  const { v, parado } = useLaco(1100, pausa + atraso);
  if (parado) return null;
  const x = v.interpolate({ inputRange: [0, 1], outputRange: [-160, LARGURA + 40] });
  return (
    <View pointerEvents="none" accessibilityElementsHidden className="absolute -top-[40px] -bottom-[40px] left-[0px] right-[0px]">
      <Animated.View style={{ position: 'absolute', top: 0, bottom: 0, width: 70, flexDirection: 'row',
        transform: [{ translateX: x }, { rotate: '18deg' }] }}>
        <View style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.18)' }} />
        <View style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.5)' }} />
        <View style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.18)' }} />
      </Animated.View>
    </View>
  );
}

// Número que conta até o valor novo (pontos)
export function useContagem(alvo: number, duracao = 700) {
  const [valor, setValor] = useState(alvo);
  const antes = useRef(alvo);
  const parado = useMovimentoReduzido();
  useEffect(() => {
    const de = antes.current;
    antes.current = alvo;
    if (parado || de === alvo) {
      setValor(alvo);
      return;
    }
    const inicio = Date.now();
    let quadro = 0;
    const passo = () => {
      const t = Math.min(1, (Date.now() - inicio) / duracao);
      setValor(Math.round(de + (alvo - de) * (1 - (1 - t) ** 3)));
      if (t < 1) quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [alvo, duracao, parado]);
  return valor;
}
