import { Tabs } from 'expo-router';

import { BarraAbas } from '../../componentes/BarraAbas';
import { useMovimentoReduzido } from '../../lib/movimento';

export default function Abas() {
  // Trocar de aba desliza e esmaece a tela (sem animação com "reduzir movimento" ligado)
  const parado = useMovimentoReduzido();
  return (
    <Tabs tabBar={(props) => <BarraAbas {...props} />} screenOptions={{ headerShown: false, animation: parado ? 'none' : 'shift' }}>
      <Tabs.Screen name="index" options={{ title: 'Mapa' }} />
      <Tabs.Screen name="podio" options={{ title: 'Pódio' }} />
      <Tabs.Screen name="amigos" options={{ title: 'Amigos' }} />
      <Tabs.Screen name="chat" options={{ title: 'Chat' }} />
      <Tabs.Screen name="colecao" options={{ title: 'Álbum' }} />
      <Tabs.Screen name="conta" options={{ title: 'Conta' }} />
    </Tabs>
  );
}
