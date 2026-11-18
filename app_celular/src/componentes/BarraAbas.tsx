// Barra de baixo: metade das abas de cada lado e o botão da câmera no meio, mais alto que a barra.
import * as Haptics from 'expo-haptics';
import { router, type Tabs } from 'expo-router';
import { useEffect, useLayoutEffect, useRef, useState, type ComponentProps } from 'react';
import { Animated, Easing, Platform, Pressable, Text, useWindowDimensions, View, type LayoutRectangle } from 'react-native';

import { api } from '../lib/api';
import { useCores } from '../lib/cores';
import { useLaco, useMovimentoReduzido } from '../lib/movimento';
import { Icone, type NomeIcone } from './icones/Icone';

type Props = Parameters<NonNullable<ComponentProps<typeof Tabs>['tabBar']>>[0];

// Ícones das rotas principais.
const ICONES: Record<string, NomeIcone> = {
  index: 'mapa', podio: 'trofeu', amigos: 'amigos', chat: 'chat', colecao: 'museu', conta: 'bussola',
};

export function BarraAbas({ state, descriptors, navigateToTab, insets }: Props) {
  const c = useCores();
  const meio = Math.floor(state.routes.length / 2);
  const { width } = useWindowDimensions();
  const centro = Math.min(84, Math.max(44, width - state.routes.length * 44));
  const botao = Math.min(68, centro);
  const { v: halo } = useLaco(1800, 600);
  const parado = useMovimentoReduzido();
  // A posição da pílula da aba ativa vem do onLayout de cada aba.
  const caixas = useRef<Record<number, { aba?: LayoutRectangle; pilula?: LayoutRectangle }>>({});
  const [, setMedidas] = useState(0);
  const pilula = useRef(new Animated.Value(0)).current;
  const posicionada = useRef(false);
  const medir = (i: number, parte: 'aba' | 'pilula', r: LayoutRectangle) => {
    caixas.current[i] = { ...caixas.current[i], [parte]: r };
    setMedidas((n) => n + 1);
  };
  const alvo = caixas.current[state.index];
  const pronta = !!(alvo?.aba && alvo.pilula);
  const destino = pronta ? alvo.aba!.x + alvo.pilula!.x : null;
  useLayoutEffect(() => {
    if (destino === null) return;
    if (parado !== false || !posicionada.current) {
      pilula.setValue(destino);
      posicionada.current = true;
      return;
    }
    const animacao = Animated.timing(pilula, { toValue: destino, duration: 220,
      easing: Easing.out(Easing.cubic), useNativeDriver: Platform.OS !== 'web' });
    animacao.start();
    return () => animacao.stop();
  }, [destino, parado, pilula]);
  // Mensagens não lidas no ícone do Chat (de 20 em 20 s; a barra não é uma tela, então sem useDados)
  const [naoLidas, setNaoLidas] = useState(0);
  useEffect(() => {
    const buscar = () => api.naoLidas().then((r) => setNaoLidas(r.nao_lidas)).catch(() => {});
    buscar();
    const id = setInterval(buscar, 20000);
    return () => clearInterval(id);
  }, [state.index]);

  const aba = (rota: (typeof state.routes)[number], indice: number) => {
    const ativa = state.index === indice;
    const titulo = String(descriptors[rota.key].options.title ?? rota.name);
    const nomeIcone = ICONES[rota.name] ?? 'alfinete';
    const contador = rota.name === 'chat' ? naoLidas : 0;
    return (
      <Pressable key={rota.key} accessibilityRole="tab" accessibilityState={{ selected: ativa }}
        accessibilityLabel={contador ? `${titulo}, ${contador} mensagens não lidas` : titulo}
        onPress={() => navigateToTab(rota.key)} onLayout={(e) => medir(indice, 'aba', e.nativeEvent.layout)}
        className="flex-1 items-center justify-center min-h-[56px] min-w-[44px] gap-[2px]">
        <View onLayout={(e) => medir(indice, 'pilula', e.nativeEvent.layout)}
          style={{ paddingHorizontal: 12, paddingVertical: 3, borderRadius: 6, backgroundColor: ativa && !pronta ? c.suave : 'transparent' }}>
          <Icone nome={nomeIcone} tamanho={23} cor={ativa ? c.destaque : c.apagado} ativo={ativa} />
          {contador ? (
            <View className="absolute -top-[2px] right-[6px] min-w-[18px] h-[18px] rounded-full px-[4px] bg-destaque items-center justify-center">
              <Text className="font-numero text-destaque-tinta text-[11px]">{contador > 99 ? '99+' : contador}</Text>
            </View>
          ) : null}
        </View>
        <Text className="font-texto-forte" style={{ fontSize: 11, fontWeight: ativa ? '700' : '500', color: ativa ? c.destaque : c.apagado }}>{titulo}</Text>
      </Pressable>
    );
  };

  return (
    <View accessibilityRole="tablist" style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: c.superficie,
      paddingBottom: insets.bottom, paddingTop: 4, borderTopLeftRadius: 6, borderTopRightRadius: 6, borderTopWidth: 1, borderColor: c.linha }}>
      {pronta ? (
        <Animated.View pointerEvents="none" style={{ position: 'absolute', left: 0, top: alvo.aba!.y + alvo.pilula!.y, width: alvo.pilula!.width,
          height: alvo.pilula!.height, borderRadius: 6, backgroundColor: c.suave, transform: [{ translateX: pilula }] }} />
      ) : null}
      {state.routes.slice(0, meio).map((r, i) => aba(r, i))}
      <View className="items-center" style={{ width: centro }}>
        {/* Halo de lente: chama para a câmera sem tampar nada */}
        <Animated.View pointerEvents="none" accessibilityElementsHidden style={{ position: 'absolute', top: -30, width: botao, height: botao,
          borderRadius: 6, borderWidth: 3, borderColor: c.sol,
          opacity: halo.interpolate({ inputRange: [0, 0.1, 1], outputRange: [0, 0.8, 0] }),
          transform: [{ scale: halo.interpolate({ inputRange: [0, 1], outputRange: [1, 1.6] }) }] }} />
        <Pressable accessibilityRole="button" accessibilityLabel="Fotografar"
          onPress={() => {
            Haptics.selectionAsync().catch(() => {});
            router.push('/camera');
          }}
          // estilo fixo, sem função nem className: no celular o Pressable ficava sem tamanho (não dava para tocar)
          style={{ width: botao, height: botao, borderRadius: 6, marginTop: -30, alignItems: 'center', justifyContent: 'center',
            backgroundColor: c.sol, borderWidth: 1, borderColor: c.linha }}>
          <Icone nome="camera" tamanho={30} cor={c.solTinta} traco={2.2} />
        </Pressable>
      </View>
      {state.routes.slice(meio).map((r, i) => aba(r, i + meio))}
    </View>
  );
}
