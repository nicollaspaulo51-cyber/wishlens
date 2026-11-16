// Barra de baixo: metade das abas de cada lado e o botão da câmera no meio, mais alto que a barra.
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { router, type Tabs } from 'expo-router';
import { useEffect, useState, type ComponentProps } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';

import { api } from '../lib/api';
import { useCores } from '../lib/cores';
import { useLaco } from '../lib/movimento';

type Props = Parameters<NonNullable<ComponentProps<typeof Tabs>['tabBar']>>[0];
type Icone = ComponentProps<typeof Ionicons>['name'];

const ICONES: Record<string, [Icone, Icone]> = {
  index: ['map', 'map-outline'],
  podio: ['trophy', 'trophy-outline'],
  amigos: ['people', 'people-outline'],
  chat: ['chatbubbles', 'chatbubbles-outline'],
  colecao: ['albums', 'albums-outline'],
  conta: ['person-circle', 'person-circle-outline'],
};

export function BarraAbas({ state, descriptors, navigateToTab, insets }: Props) {
  const c = useCores();
  const meio = Math.floor(state.routes.length / 2);
  const { v: halo } = useLaco(1800, 600);
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
    const [cheio, vazado] = ICONES[rota.name] ?? ['ellipse', 'ellipse-outline'];
    const contador = rota.name === 'chat' ? naoLidas : 0;
    return (
      <Pressable key={rota.key} accessibilityRole="tab" accessibilityState={{ selected: ativa }}
        accessibilityLabel={contador ? `${titulo}, ${contador} mensagens não lidas` : titulo}
        onPress={() => navigateToTab(rota.key)}
        style={{ flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56, gap: 2 }}>
        <View style={{ paddingHorizontal: 12, paddingVertical: 3, borderRadius: 14, backgroundColor: ativa ? c.suave : 'transparent' }}>
          <Ionicons name={ativa ? cheio : vazado} size={22} color={ativa ? c.destaque : c.apagado} />
          {contador ? (
            <View style={{ position: 'absolute', top: -2, right: 6, minWidth: 18, height: 18, borderRadius: 9, paddingHorizontal: 4,
              backgroundColor: c.recusa, alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: '#fff', fontSize: 11, fontWeight: '800' }}>{contador > 99 ? '99+' : contador}</Text>
            </View>
          ) : null}
        </View>
        <Text style={{ fontSize: 11, fontWeight: ativa ? '700' : '500', color: ativa ? c.destaque : c.apagado }}>{titulo}</Text>
      </Pressable>
    );
  };

  return (
    <View accessibilityRole="tablist" style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: c.superficie,
      paddingBottom: insets.bottom, paddingTop: 4, borderTopLeftRadius: 22, borderTopRightRadius: 22,
      shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 12, shadowOffset: { width: 0, height: -3 }, elevation: 16 }}>
      {state.routes.slice(0, meio).map((r, i) => aba(r, i))}
      <View style={{ width: 84, alignItems: 'center' }}>
        {/* Halo de lente: chama para a câmera sem tampar nada */}
        <Animated.View pointerEvents="none" accessibilityElementsHidden style={{ position: 'absolute', top: -30, width: 68, height: 68,
          borderRadius: 34, borderWidth: 3, borderColor: c.sol,
          opacity: halo.interpolate({ inputRange: [0, 0.1, 1], outputRange: [0, 0.8, 0] }),
          transform: [{ scale: halo.interpolate({ inputRange: [0, 1], outputRange: [1, 1.6] }) }] }} />
        <Pressable accessibilityRole="button" accessibilityLabel="Fotografar"
          onPress={() => {
            Haptics.selectionAsync().catch(() => {});
            router.push('/camera');
          }}
          style={({ pressed }) => ({ width: 68, height: 68, borderRadius: 34, marginTop: -30, alignItems: 'center', justifyContent: 'center',
            backgroundColor: c.sol, borderWidth: 5, borderColor: c.superficie, transform: [{ scale: pressed ? 0.94 : 1 }],
            shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 8, shadowOffset: { width: 0, height: 4 }, elevation: 8 })}>
          <Ionicons name="camera" size={30} color={c.solTinta} />
        </Pressable>
      </View>
      {state.routes.slice(meio).map((r, i) => aba(r, i + meio))}
    </View>
  );
}
