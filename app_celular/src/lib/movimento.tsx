// Animações do app (Animated do React Native, no driver nativo). Todas param com "reduzir movimento" ligado no celular.
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { useIsFocused } from 'expo-router';
import { AccessibilityInfo, Animated, Easing, Platform, type StyleProp, type ViewStyle } from 'react-native';

export function useMovimentoReduzido() {
  const [reduzido, setReduzido] = useState<boolean | null>(null);
  useEffect(() => {
    let ativo = true;
    AccessibilityInfo.isReduceMotionEnabled().then((preferencia) => {
      if (ativo) setReduzido(preferencia);
    }).catch(() => { if (ativo) setReduzido(true); });
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduzido);
    return () => { ativo = false; sub?.remove(); };
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

// Vai de 0 a 1 sem parar, com pausa no fim.
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

// Número que conta até o valor novo (pontos)
export function useContagem(alvo: number, duracao: number, inicial = alvo) {
  const [valor, setValor] = useState(inicial);
  const parado = useMovimentoReduzido();
  const numero = useRef(new Animated.Value(inicial)).current;
  useLayoutEffect(() => {
    if (parado === null) return;
    if (parado) {
      numero.setValue(alvo);
      setValor(alvo);
      return;
    }
    const id = numero.addListener(({ value }) => setValor(Math.round(value)));
    const animacao = Animated.timing(numero, { toValue: alvo, duration: duracao, easing: Easing.out(Easing.cubic), useNativeDriver: false });
    animacao.start();
    return () => { animacao.stop(); numero.removeListener(id); };
  }, [alvo, duracao, numero, parado]);
  return parado ? alvo : valor;
}

export function useTransicao(alvo: number, duracao: number, { inicial = alvo, atraso = 0, nativo = true } = {}) {
  const parado = useMovimentoReduzido();
  const valor = useRef(new Animated.Value(inicial)).current;
  useLayoutEffect(() => {
    if (parado === null) return;
    if (parado) {
      valor.setValue(alvo);
      return;
    }
    const animacao = Animated.timing(valor, { toValue: alvo, duration: duracao, delay: atraso,
      easing: Easing.out(Easing.cubic), useNativeDriver: nativo && Platform.OS !== 'web' });
    animacao.start();
    return () => animacao.stop();
  }, [alvo, atraso, duracao, nativo, parado, valor]);
  return valor;
}
