import '../../global.css';
import '../lib/estilo';

import { Overpass_400Regular, Overpass_700Bold, Overpass_800ExtraBold, useFonts } from '@expo-google-fonts/overpass';
import { OverpassMono_600SemiBold } from '@expo-google-fonts/overpass-mono';
import { vars } from 'nativewind';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';

import { useCores, variaveis } from '../lib/cores';
import { ProvedorSessao, useSessao } from '../lib/sessao';

function Navegacao() {
  const c = useCores();
  const { pronto, entrou } = useSessao();
  if (!pronto) {
    return <View className="flex-1 bg-papel justify-center"><ActivityIndicator color={c.destaque} /></View>;
  }
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.fundo } }}>
      <Stack.Protected guard={entrou}>
        <Stack.Screen name="(abas)" />
        <Stack.Screen name="camera" options={{ presentation: 'fullScreenModal', animation: 'slide_from_bottom' }} />
        <Stack.Screen name="avisar" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
        <Stack.Screen name="conversa/[apelido]" />
      </Stack.Protected>
      <Stack.Protected guard={!entrou}>
        <Stack.Screen name="entrar" />
      </Stack.Protected>
    </Stack>
  );
}

export default function Raiz() {
  const c = useCores();
  const [fontes, erroFontes] = useFonts({ Overpass_400Regular, Overpass_700Bold, Overpass_800ExtraBold, OverpassMono_600SemiBold });
  // Se uma fonte não baixar, o app abre com a fonte do sistema em vez de ficar em branco para sempre
  if (!fontes && !erroFontes) return null;
  return (
    // vars(): as cores da PALETA viram variáveis CSS para as classes do NativeWind (tema claro/escuro)
    <GestureHandlerRootView style={{ flex: 1 }}>
      {/* View comum: o NativeWind registra as variáveis por componentes do React Native */}
      <View style={[{ flex: 1 }, vars(variaveis(c))]}>
        <ProvedorSessao>
          <StatusBar style="auto" />
          <Navegacao />
        </ProvedorSessao>
      </View>
    </GestureHandlerRootView>
  );
}
