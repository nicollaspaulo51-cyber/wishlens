import '../../global.css';

import { AtkinsonHyperlegible_400Regular, AtkinsonHyperlegible_700Bold } from '@expo-google-fonts/atkinson-hyperlegible';
import { BricolageGrotesque_600SemiBold, BricolageGrotesque_800ExtraBold, useFonts } from '@expo-google-fonts/bricolage-grotesque';
import { Caveat_700Bold } from '@expo-google-fonts/caveat';
import { vars } from 'nativewind';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Redirect, Stack, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';

import { useCores, variaveis } from '../lib/cores';
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
      <Stack.Screen name="avisar" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
    </Stack>
  );
}

export default function Raiz() {
  const c = useCores();
  const [fontes] = useFonts({ BricolageGrotesque_600SemiBold, BricolageGrotesque_800ExtraBold, AtkinsonHyperlegible_400Regular,
    AtkinsonHyperlegible_700Bold, Caveat_700Bold });
  if (!fontes) return null;
  return (
    // vars(): as cores da PALETA viram variáveis CSS para as classes do NativeWind (tema claro/escuro)
    <GestureHandlerRootView style={[{ flex: 1 }, vars(variaveis(c))]}>
      <ProvedorSessao>
        <StatusBar style="auto" />
        <Navegacao />
      </ProvedorSessao>
    </GestureHandlerRootView>
  );
}
