import { Tabs } from 'expo-router';
import type { BottomTabSceneStyleInterpolator } from 'expo-router/build/react-navigation/bottom-tabs/types';

import { BarraAbas } from '../../componentes/BarraAbas';
import { useMovimentoReduzido } from '../../lib/movimento';

// Trocar de aba vira a página como folha de caderno: a nova entra girando de leve do lado em que está na barra
const folha: BottomTabSceneStyleInterpolator = ({ current }) => ({
  sceneStyle: {
    opacity: current.progress.interpolate({ inputRange: [-1, -0.4, 0, 0.4, 1], outputRange: [0, 0.6, 1, 0.6, 0] }),
    transform: [
      { perspective: 1200 },
      { translateX: current.progress.interpolate({ inputRange: [-1, 0, 1], outputRange: [-70, 0, 70] }) },
      { rotateY: current.progress.interpolate({ inputRange: [-1, 0, 1], outputRange: ['28deg', '0deg', '-28deg'] }) },
    ],
  },
});

export default function Abas() {
  const parado = useMovimentoReduzido(); // com "reduzir movimento" ligado, troca sem animação
  return (
    <Tabs tabBar={(props) => <BarraAbas {...props} />}
      screenOptions={parado ? { headerShown: false, animation: 'none' } : {
        headerShown: false, animation: 'shift', sceneStyleInterpolator: folha,
        transitionSpec: { animation: 'timing', config: { duration: 320 } },
      }}>
      {/* o mapa é desenhado pelo celular: girar a tela dele pode piscar, então ele só esmaece */}
      <Tabs.Screen name="index" options={{ title: 'Mapa', ...(parado ? null : { animation: 'fade', sceneStyleInterpolator: undefined }) }} />
      <Tabs.Screen name="podio" options={{ title: 'Pódio' }} />
      <Tabs.Screen name="amigos" options={{ title: 'Amigos' }} />
      <Tabs.Screen name="chat" options={{ title: 'Chat' }} />
      <Tabs.Screen name="colecao" options={{ title: 'Museu' }} />
      <Tabs.Screen name="conta" options={{ title: 'Conta' }} />
    </Tabs>
  );
}
