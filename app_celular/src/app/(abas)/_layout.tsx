import { Tabs } from 'expo-router';

import { BarraAbas } from '../../componentes/BarraAbas';

export default function Abas() {
  return (
    <Tabs tabBar={(props) => <BarraAbas {...props} />} screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: 'Mapa' }} />
      <Tabs.Screen name="podio" options={{ title: 'Pódio' }} />
      <Tabs.Screen name="chat" options={{ title: 'Chat' }} />
      <Tabs.Screen name="colecao" options={{ title: 'Álbum' }} />
      <Tabs.Screen name="conta" options={{ title: 'Conta' }} />
    </Tabs>
  );
}
