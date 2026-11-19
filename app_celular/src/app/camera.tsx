// Câmera: tira a foto, diminui para 1024 px (envio rápido), manda para o juiz e mostra o cartão de pontos.
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as Location from 'expo-location';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Image, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CartaoPontos } from '../componentes/CartaoPontos';
import { CompartilharFoto } from '../componentes/CompartilharFoto';
import { SeletorAba } from '../componentes/SeletorAba';
import { Apagado, Botao, Fichas, Titulo } from '../componentes/ui';
import { api, type Julgamento, type Tema } from '../lib/api';
import { useCores } from '../lib/cores';
import { useModo } from '../lib/modo';
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
  const enviando = useRef(false);
  const [apertado, setApertado] = useState(false);
  const [pronta, setPronta] = useState(false);
  const [foto, setFoto] = useState<string | null>(null);
  const [enviada, setEnviada] = useState<string | null>(null); // a versão menor, que foi ao juiz
  const [resposta, setResposta] = useState<Julgamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [contestada, setContestada] = useState<string | null>(null);
  const [treinoEnviado, setTreinoEnviado] = useState(false);
  const [era, setEra] = useState<string>('');
  const temas = useDados(api.temas);
  const modo = useModo();
  const falta = useEsperaPartida(modo === 'competicao' && !foto); // volta a perguntar ao juiz depois de cada foto

  async function fotografar() {
    // dois toques rápidos mandavam duas fotos ao juiz: a 1ª ganhava os pontos e a tela mostrava a 2ª ("já achou isso hoje", 0)
    if (!camera.current || enviando.current) return;
    enviando.current = true;
    setErro(null);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    const local = posicaoAgora(); // ao mesmo tempo que a foto
    try {
      const crua = await camera.current.takePictureAsync({ quality: 0.9, shutterSound: false });
      setFoto(crua.uri);
      const menor = await (await ImageManipulator.manipulate(crua.uri).resize({ width: 1024, height: null }).renderAsync())
        .saveAsync({ format: SaveFormat.JPEG, compress: 0.85 });
      setEnviada(menor.uri);
      const r = await api.julgar(menor.uri, await local, modo);
      setResposta(r);
      if (r.status === 'ok' && r.cartao.aceita) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não consegui enviar a foto.');
    } finally {
      enviando.current = false;
    }
  }

  function outra() {
    setFoto(null);
    setEnviada(null);
    setResposta(null);
    setErro(null);
    setContestada(null);
    setTreinoEnviado(false);
    setEra('');
  }

  // Só quando a pessoa toca no botão (é o aceite): a foto vai para o treino com o tema que ela disse
  async function mandarParaTreino(tema: string) {
    if (!enviada) return;
    try {
      await api.treinoFoto(enviada, tema, 'real');
      setTreinoEnviado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não consegui mandar a foto para o treino.');
    }
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

  if (!permissao) return <View style={{ flex: 1, backgroundColor: c.fundo }} />;
  if (!permissao.granted) {
    return (
      <SafeAreaView className="flex-1 bg-papel p-[24px] gap-[16px] justify-center">
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
      <SafeAreaView className="flex-1 bg-papel">
        <ScrollView contentContainerStyle={{ padding: 16, gap: 16 }}>
          <Image source={{ uri: foto }} style={{ width: '100%', aspectRatio: 4 / 3, borderRadius: 6 }} accessibilityLabel="Sua foto" />
          {!resposta && !erro ? (
            <View className="flex-row gap-[12px] items-center" accessibilityLiveRegion="polite">
              <ActivityIndicator color={c.destaque} />
              <Text className="font-texto text-tinta text-[16px]" >Os juízes estão olhando sua foto...</Text>
            </View>
          ) : null}
          {erro ? <Text className="font-texto text-carimbo text-[16px]"  accessibilityLiveRegion="assertive">{erro}</Text> : null}
          {resposta?.status === 'borrada' ? (
            <View className="bg-ficha border border-linha rounded-ficha p-[16px] gap-[6px]">
              <Text className="font-texto-forte text-tinta text-[17px]" >{resposta.titulo ?? 'Foto borrada'}</Text>
              <Text className="font-texto text-tinta text-[15px] leading-[21px]" >{resposta.mensagem}</Text>
            </View>
          ) : null}
          {resposta?.status === 'ok' ? (
            <>
              <CartaoPontos cartao={resposta.cartao} />
              {resposta.avisos.map((a) => (
                <Text className="font-texto text-tinta text-[15px]" key={a} >{a}</Text>
              ))}
              {enviada ? <CompartilharFoto foto={foto} enviada={enviada} captura={resposta.id} aceita={resposta.cartao.aceita}
                placa={{ achado: resposta.cartao.achado, emoji: resposta.cartao.tema?.emoji ?? '', tema: resposta.cartao.tema?.nome ?? '', temaId: resposta.cartao.tema?.id,
                  cor: resposta.cartao.tema?.cor ?? c.apagado, pontos: resposta.cartao.aceita ? resposta.cartao.pontos : 0 }} /> : null}
              {resposta.posicao ? (
                <Text className="font-texto text-tinta text-[16px]" >
                  <Text className="font-numero">{resposta.posicao}º</Text> lugar hoje com <Text className="font-numero">{resposta.pontos_hoje}</Text> pontos.
                </Text>
              ) : null}
              {resposta.cartao.pode_contestar ? (
                contestada ? (
                  <View className="gap-[8px]">
                    <Apagado>Contestação registrada: você disse que era {porId[contestada]?.nome.toLowerCase()}. Isso ajuda a melhorar o juiz.</Apagado>
                    {enviada ? (
                      treinoEnviado ? <Apagado>Foto enviada para o treino. Obrigado!</Apagado> : (
                        <Botao titulo="Mandar esta foto para o treino" tipo="secundario"
                          rotulo="Mandar esta foto para o treino do juiz: fica só no computador do juiz, sem localização"
                          aoTocar={() => mandarParaTreino(contestada)} />
                      )
                    ) : null}
                  </View>
                ) : (
                  <View className="gap-[8px]">
                    <Text className="font-texto-forte text-tinta text-[15px]" >O juiz errou? Era…</Text>
                    <Fichas rotulo="Tema da foto" valor={era} aoEscolher={setEra}
                      opcoes={(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: t.nome, icone: t }))} />
                    <Botao titulo="Contestar" tipo="secundario" desativado={!era} aoTocar={() => contestar(resposta.id)} />
                  </View>
                )
              ) : null}
            </>
          ) : null}
          {resposta?.status === 'ok' ? (
            <Botao titulo="Algo errado? Avisar o suporte" tipo="secundario" rotulo="Avisar o suporte sobre esta foto"
              aoTocar={() => router.push({ pathname: '/avisar', params: { tipo: 'juiz', captura: resposta.id,
                achado: resposta.cartao.achado || undefined } })} />
          ) : erro ? (
            <Botao titulo="Avisar o suporte" tipo="secundario" aoTocar={() => router.push({ pathname: '/avisar', params: { tipo: 'app' } })} />
          ) : null}
          {resposta || erro ? (
            <View className="gap-[10px]">
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
      <CameraView ref={camera} className="flex-1" facing="back" onCameraReady={() => setPronta(true)} />
      <SafeAreaView edges={['top', 'bottom']} className="absolute top-[0px] left-[0px] right-[0px] bottom-[0px] justify-between"
        pointerEvents="box-none">
        <View className="flex-row justify-between items-center p-[16px]">
          <Pressable accessibilityRole="button" accessibilityLabel="Fechar a câmera" onPress={() => router.back()}
            style={{ minWidth: 48, minHeight: 48, paddingHorizontal: 12, borderRadius: 6, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center' }}>
            <Text className="font-texto" style={{ color: '#fff', fontSize: 16 }}>Fechar</Text>
          </Pressable>
          <SeletorAba />
        </View>
        <View style={{ alignItems: 'center', gap: 12, paddingBottom: Platform.OS === 'web' ? 24 : 12 }}>
          {modo === 'competicao' ? (
            <Text className="font-texto-forte" accessibilityLiveRegion="polite" style={{ color: '#fff', fontSize: 15, fontWeight: '700', backgroundColor: 'rgba(0,0,0,0.55)',
              paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, overflow: 'hidden', textAlign: 'center' }}>
              {falta > 0 ? <>Próxima partida em <Text className="font-numero">{Math.floor(falta / 60)}:{String(falta % 60).padStart(2, '0')}</Text></>
                : 'Fotografe a tela do fim da partida'}
            </Text>
          ) : null}
          <Pressable accessibilityRole="button" accessibilityLabel={falta > 0 ? 'Tirar a foto (espere a próxima partida)' : 'Tirar a foto'}
            disabled={!pronta || falta > 0} onPress={fotografar}
            onPressIn={() => setApertado(true)} onPressOut={() => setApertado(false)}
            // estilo fixo e sem className: no celular um Pressable só com classes ficava sem tamanho (botão invisível)
            style={{ width: 78, height: 78, borderRadius: 39, borderWidth: 5, borderColor: '#fff', alignItems: 'center', justifyContent: 'center',
              backgroundColor: apertado ? c.destaque : 'rgba(255,255,255,0.25)', opacity: pronta && falta <= 0 ? 1 : 0.4 }}>
            <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: '#fff' }} />
          </Pressable>
        </View>
      </SafeAreaView>
    </View>
  );
}

// Competição: segundos até poder mandar a próxima foto de partida (o juiz manda o número; aqui só conta para baixo)
function useEsperaPartida(ativa: boolean) {
  const [fim, setFim] = useState(0);
  const [agora, setAgora] = useState(Date.now());
  useEffect(() => {
    if (!ativa) return;
    api.estado().then((e) => setFim(Date.now() + (e.espera_competicao ?? 0) * 1000)).catch(() => {});
  }, [ativa]);
  useEffect(() => {
    if (!ativa || fim <= Date.now()) return;
    const id = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(id);
  }, [ativa, fim]);
  return ativa ? Math.max(0, Math.ceil((fim - agora) / 1000)) : 0;
}
