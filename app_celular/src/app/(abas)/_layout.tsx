import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { useCores } from '../../lib/cores';

const icone = (emoji: string) => ({ focused }: { focused: boolean }) => (
  <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.55 }}>{emoji}</Text>
);

export default function Abas() {
  const c = useCores();
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: c.destaque,
      tabBarInactiveTintColor: c.apagado,
      tabBarStyle: { backgroundColor: c.superficie, borderTopColor: c.linha },
      tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
    }}>
      <Tabs.Screen name="index" options={{ title: 'Jogar', tabBarIcon: icone('🧭') }} />
      <Tabs.Screen name="podio" options={{ title: 'Pódio', tabBarIcon: icone('🏆') }} />
      <Tabs.Screen name="colecao" options={{ title: 'Coleção', tabBarIcon: icone('📒') }} />
    </Tabs>
  );
}
