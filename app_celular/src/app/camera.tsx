// Câmera: tira a foto, diminui para 1024 px (envio rápido), manda para o juiz e mostra o cartão de pontos.
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as Location from 'expo-location';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { ActivityIndicator, Image, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CartaoPontos } from '../componentes/CartaoPontos';
import { Apagado, Botao, Fichas, Titulo } from '../componentes/ui';
import { api, type Julgamento, type Tema } from '../lib/api';
import { useCores } from '../lib/cores';
import { useDados } from '../lib/useDados';

async function posicaoAgora() {
  try {
    const { granted } = await Location.getForegroundPermissionsAsync();
    if (!granted) return null;
    const p = (await Location.getLastKnownPositionAsync({ maxAge: 60_000 }))
      ?? (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
    return p ? { lat: p.coords.latitude, lon: p.coords.longitude } : null;
  } catch {
    return null;
  }
}

export default function Camera() {
  const c = useCores();
  const [permissao, pedirPermissao] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [pronta, setPronta] = useState(false);
  const [foto, setFoto] = useState<string | null>(null);
  const [resposta, setResposta] = useState<Julgamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [contestada, setContestada] = useState<string | null>(null);
  const [era, setEra] = useState<string>('');
  const temas = useDados(api.temas);

  async function fotografar() {
    if (!camera.current) return;
    setErro(null);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    const local = posicaoAgora(); // ao mesmo tempo que a foto
    try {
      const crua = await camera.current.takePictureAsync({ quality: 0.9, shutterSound: false });
      setFoto(crua.uri);
      const menor = await (await ImageManipulator.manipulate(crua.uri).resize({ width: 1024, height: null }).renderAsync())
        .saveAsync({ format: SaveFormat.JPEG, compress: 0.85 });
      const r = await api.julgar(menor.uri, await local);
      setResposta(r);
      if (r.status === 'ok' && r.cartao.aceita) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não consegui enviar a foto.');
    }
  }

  function outra() {
    setFoto(null);
    setResposta(null);
    setErro(null);
    setContestada(null);
    setEra('');
  }

  async function contestar(id: string) {
    if (!era) return;
    try {
      await api.contestar(id, era);
      setContestada(era);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não consegui registrar.');
    }
  }

  if (!permissao) return <View style={{ flex: 1, backgroundColor: '#000' }} />;
  if (!permissao.granted) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: c.fundo, padding: 24, gap: 16, justifyContent: 'center' }}>
        <Titulo>Câmera</Titulo>
        <Apagado>Para jogar, o WishLens precisa da câmera. A foto é usada só para o juiz dizer o que é.</Apagado>
        <Botao titulo="Permitir a câmera" aoTocar={pedirPermissao} />
        <Botao titulo="Voltar" tipo="secundario" aoTocar={() => router.back()} />
      </SafeAreaView>
    );
  }

  // Depois da foto: o julgamento e o resultado
  if (foto) {
    const porId = Object.fromEntries((temas.dados?.temas ?? []).map((t) => [t.id, t])) as Record<string, Tema>;
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: c.fundo }}>
        <ScrollView contentContainerStyle={{ padding: 16, gap: 16 }}>
          <Image source={{ uri: foto }} style={{ width: '100%', aspectRatio: 4 / 3, borderRadius: 12 }} accessibilityLabel="Sua foto" />
          {!resposta && !erro ? (
            <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }} accessibilityLiveRegion="polite">
              <ActivityIndicator color={c.destaque} />
              <Text style={{ color: c.tinta, fontSize: 16 }}>Os juízes estão olhando sua foto...</Text>
            </View>
          ) : null}
          {erro ? <Text style={{ color: c.recusa, fontSize: 16 }} accessibilityLiveRegion="assertive">{erro}</Text> : null}
          {resposta?.status === 'borrada' ? (
            <View style={{ backgroundColor: c.superficie, borderRadius: 14, padding: 16, gap: 6 }}>
              <Text style={{ color: c.tinta, fontSize: 17, fontWeight: '700' }}>Foto borrada</Text>
              <Text style={{ color: c.tinta, fontSize: 15, lineHeight: 21 }}>{resposta.mensagem}</Text>
            </View>
          ) : null}
          {resposta?.status === 'ok' ? (
            <>
              <CartaoPontos cartao={resposta.cartao} />
              {resposta.avisos.map((a) => (
                <Text key={a} style={{ color: c.tinta, fontSize: 15 }}>⚡ {a}</Text>
              ))}
              {resposta.posicao ? (
                <Text style={{ color: c.tinta, fontSize: 16 }}>
                  <Text style={{ fontWeight: '700' }}>{resposta.posicao}º lugar hoje</Text> com {resposta.pontos_hoje} pontos.
                </Text>
              ) : null}
              {resposta.cartao.pode_contestar ? (
                contestada ? (
                  <Apagado>Contestação registrada: você disse que era {porId[contestada]?.nome.toLowerCase()}. Isso ajuda a melhorar o juiz.</Apagado>
                ) : (
                  <View style={{ gap: 8 }}>
                    <Text style={{ color: c.tinta, fontSize: 15, fontWeight: '600' }}>O juiz errou? Era…</Text>
                    <Fichas rotulo="Tema da foto" valor={era} aoEscolher={setEra}
                      opcoes={(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: `${t.emoji} ${t.nome}` }))} />
                    <Botao titulo="Contestar" tipo="secundario" desativado={!era} aoTocar={() => contestar(resposta.id)} />
                  </View>
                )
              ) : null}
            </>
          ) : null}
          {resposta || erro ? (
            <View style={{ gap: 10 }}>
              <Botao titulo="Tirar outra" aoTocar={outra} />
              <Botao titulo="Voltar ao mapa" tipo="secundario" aoTocar={() => router.back()} />
            </View>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      <CameraView ref={camera} style={{ flex: 1 }} facing="back" onCameraReady={() => setPronta(true)} />
      <SafeAreaView edges={['top', 'bottom']} style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, justifyContent: 'space-between' }}
        pointerEvents="box-none">
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 }}>
          <Pressable accessibilityRole="button" accessibilityLabel="Fechar a câmera" onPress={() => router.back()}
            style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ color: '#fff', fontSize: 22 }}>✕</Text>
          </Pressable>
          <Text style={{ color: '#fff', fontSize: 14, backgroundColor: 'rgba(0,0,0,0.45)', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 }}>
            Algo real, de um dos temas
          </Text>
        </View>
        <View style={{ alignItems: 'center', paddingBottom: Platform.OS === 'web' ? 24 : 12 }}>
          <Pressable accessibilityRole="button" accessibilityLabel="Tirar a foto" disabled={!pronta} onPress={fotografar}
            style={({ pressed }) => ({ width: 78, height: 78, borderRadius: 39, borderWidth: 5, borderColor: '#fff',
              backgroundColor: pressed ? '#FFC83D' : 'rgba(255,255,255,0.25)', opacity: pronta ? 1 : 0.4 })} />
        </View>
      </SafeAreaView>
    </View>
  );
}
