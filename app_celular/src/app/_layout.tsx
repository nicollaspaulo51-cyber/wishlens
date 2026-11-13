import { BricolageGrotesque_600SemiBold, BricolageGrotesque_800ExtraBold, useFonts } from '@expo-google-fonts/bricolage-grotesque';
import { Redirect, Stack, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';

import { useCores } from '../lib/cores';
import { ProvedorSessao, useSessao } from '../lib/sessao';

function Navegacao() {
  const c = useCores();
  const { pronto, entrou } = useSessao();
  const segmentos = useSegments();
  if (!pronto) {
    return <View style={{ flex: 1, backgroundColor: c.fundo, justifyContent: 'center' }}><ActivityIndicator color={c.destaque} /></View>;
  }
  const naEntrada = segmentos[0] === 'entrar';
  if (!entrou && !naEntrada) return <Redirect href="/entrar" />;
  if (entrou && naEntrada) return <Redirect href="/" />;
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.fundo } }}>
      <Stack.Screen name="(abas)" />
      <Stack.Screen name="entrar" />
      <Stack.Screen name="camera" options={{ presentation: 'fullScreenModal', animation: 'slide_from_bottom' }} />
    </Stack>
  );
}

export default function Raiz() {
  const [fontes] = useFonts({ BricolageGrotesque_600SemiBold, BricolageGrotesque_800ExtraBold });
  if (!fontes) return null;
  return (
    <ProvedorSessao>
      <StatusBar style="auto" />
      <Navegacao />
    </ProvedorSessao>
  );
}
