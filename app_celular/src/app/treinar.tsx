// Treinar o juiz: a pessoa fotografa de propósito e diz o que é. As fotos vão só para o PC do juiz (sem GPS e sem
// EXIF) e ensinam o CLIP e a IA com fotos de celular de verdade, principalmente as FALSAS (tela, impressa, brinquedo).
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Image, KeyboardAvoidingView, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Cartaz, Fichas, Subtitulo, Titulo } from '../componentes/ui';
import { api } from '../lib/api';
import { useCores } from '../lib/cores';
import { useDados } from '../lib/useDados';

const CHAVE_ACEITE = 'wl_treino_ok';
const TIPOS = [
  { valor: 'real', texto: 'Real', dica: 'O próprio objeto na frente da câmera.' },
  { valor: 'tela', texto: 'Na tela', dica: 'Foto do objeto aparecendo no celular, monitor ou TV.' },
  { valor: 'impressa', texto: 'Impressa', dica: 'Foto do objeto num papel, revista, cartaz ou livro.' },
  { valor: 'brinquedo', texto: 'Brinquedo', dica: 'Miniatura, pelúcia, boneco ou planta de plástico.' },
  { valor: 'desenho', texto: 'Desenho', dica: 'Desenho, pintura, grafite ou ilustração.' },
  { valor: 'estatua', texto: 'Estátua', dica: 'Estátua ou escultura do objeto.' },
] as const;

export default function Treinar() {
  const c = useCores();
  const [aceitou, setAceitou] = useState<boolean | null>(null);
  const [tema, setTema] = useState('carros');
  const [tipo, setTipo] = useState('real');
  const [objeto, setObjeto] = useState('');
  const [resultado, setResultado] = useState<'vitoria' | 'derrota'>('vitoria');
  const [fotografando, setFotografando] = useState(false);
  const [permissao, pedirPermissao] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [pronta, setPronta] = useState(false);
  const [apertado, setApertado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  // a foto tirada espera aqui: a IA sugere o modelo e a pessoa confirma, corrige ou descarta
  const [rascunho, setRascunho] = useState<{ uri: string; modelo: string; sugerindo: boolean; aviso: string | null } | null>(null);
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const temas = useDados(api.temas);
  const contagem = useDados(api.treinoContagem, [], 0);

  useEffect(() => {
    AsyncStorage.getItem(CHAVE_ACEITE).then((v) => setAceitou(v === '1')).catch(() => setAceitou(false));
  }, []);

  const opcoesTema = [
    ...(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: t.nome, icone: t })),
    ...(temas.dados?.abas ?? []).map((a) => ({ valor: a.id, texto: a.nome, icone: a })),
    { valor: 'nenhum', texto: 'Nenhum deles' },
  ];
  const nomeTema = opcoesTema.find((o) => o.valor === tema)?.texto ?? tema;
  const objetos = contagem.dados?.objetos[tema] ?? [];
  const dicaTipo = TIPOS.find((t) => t.valor === tipo)?.dica;
  const d = contagem.dados;
  const falta = d ? Math.max(0, d.meta_tema - (d.por_tema[tema] ?? 0)) : null;

  async function aceitar() {
    await AsyncStorage.setItem(CHAVE_ACEITE, '1').catch(() => {});
    setAceitou(true);
  }

  async function fotografar() {
    if (!camera.current || enviando || rascunho) return;
    setMsg(null);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    try {
      const crua = await camera.current.takePictureAsync({ quality: 0.9, shutterSound: false });
      const menor = await (await ImageManipulator.manipulate(crua.uri).resize({ width: 1024, height: null }).renderAsync())
        .saveAsync({ format: SaveFormat.JPEG, compress: 0.85 });
      setRascunho({ uri: menor.uri, modelo: '', sugerindo: true, aviso: null });
      api.treinoSugerir(menor.uri)
        .then((r) => setRascunho((a) => (a && a.uri === menor.uri
          // a sugestão só vale se o tema que a IA viu é o que a pessoa escolheu (senão ela errou de assunto)
          ? { ...a, sugerindo: false, aviso: r.aviso, modelo: !a.modelo && r.tema === tema ? r.achado : a.modelo } : a)))
        .catch(() => setRascunho((a) => (a ? { ...a, sugerindo: false, aviso: 'Sem sugestão agora: escreva o modelo, se souber.' } : a)));
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não consegui tirar a foto.', erro: true });
    }
  }

  async function enviarRascunho() {
    if (!rascunho || enviando) return;
    setEnviando(true);
    try {
      await api.treinoFoto(rascunho.uri, tema, tipo, tema === 'competicao' ? (resultado === 'vitoria' ? 'vitória' : 'derrota') : objeto,
        tema === 'competicao' ? '' : rascunho.modelo.trim());
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      setMsg({ texto: 'Foto enviada. Obrigado!', erro: false });
      setRascunho(null);
      contagem.recarregar();
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não consegui enviar a foto.', erro: true });
    } finally {
      setEnviando(false);
    }
  }

  if (aceitou === null) return <View style={{ flex: 1, backgroundColor: c.fundo }} />;

  if (!aceitou) {
    return (
      <SafeAreaView className="flex-1 bg-papel">
        <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>
          <Titulo>Ajudar a treinar o juiz</Titulo>
          <Apagado>
            Você tira fotos de propósito e diz o que são: um carro de verdade, a foto de um carro numa tela, um brinquedo...
            Com elas, o juiz aprende a errar menos.
          </Apagado>
          <Cartaz estilo={{ gap: 8 }}>
            <Text className="font-texto-forte text-tinta text-[16px]">O que acontece com as suas fotos</Text>
            <Text className="font-texto text-tinta text-[15px] leading-[22px]">
              • Ficam só no computador do juiz da turma, nunca na internet.{'\n'}
              • Sem localização e sem os dados escondidos da foto (EXIF).{'\n'}
              • Aparece o seu apelido e o modelo do seu celular junto, para a gente ver se algum aparelho erra mais.{'\n'}
              • Evite pessoas e rostos: fotografe objetos, bichos e telas.
            </Text>
          </Cartaz>
          <Botao titulo="Aceito, quero ajudar" aoTocar={aceitar} />
          <Botao titulo="Agora não" tipo="secundario" aoTocar={() => router.back()} />
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (fotografando && rascunho) {
    return (
      <SafeAreaView className="flex-1 bg-papel">
        <KeyboardAvoidingView className="flex-1" behavior="padding">
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
          <Titulo>Confira a foto</Titulo>
          <Image source={{ uri: rascunho.uri }} style={{ width: '100%', aspectRatio: 3 / 4, borderRadius: 6 }} resizeMode="cover"
            accessibilityLabel="A foto que você tirou" />
          <Apagado>{nomeTema}{objeto ? `: ${objeto}` : ''} · {TIPOS.find((t) => t.valor === tipo)?.texto}</Apagado>
          {tema !== 'competicao' ? (
            <View className="gap-[6px]">
              <Text className="font-texto-forte text-tinta text-[15px]">Qual é o modelo ou a marca? (opcional)</Text>
              <TextInput value={rascunho.modelo} onChangeText={(m) => setRascunho({ ...rascunho, modelo: m })} maxLength={60}
                placeholder="Ex.: Volkswagen Gol, mouse Logitech G203" placeholderTextColor={c.apagado} accessibilityLabel="Modelo ou marca"
                className="min-h-[52px] border border-linha rounded-[6px] px-[14px] text-[16px] text-tinta bg-fundo" />
              {rascunho.sugerindo ? (
                <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                  <ActivityIndicator color={c.destaque} /><Apagado>A IA está sugerindo um modelo...</Apagado>
                </View>
              ) : rascunho.aviso ? <Apagado>{rascunho.aviso}</Apagado>
                : <Apagado>Sugestão da IA: corrija se estiver errada. Deixe vazio se não souber.</Apagado>}
            </View>
          ) : null}
          {msg?.erro ? <Text className="font-texto text-recusa text-[15px]" accessibilityLiveRegion="polite">{msg.texto}</Text> : null}
          <Botao titulo="Enviar para o treino" aoTocar={enviarRascunho} carregando={enviando} />
          <Botao titulo="Descartar" tipo="secundario" desativado={enviando} aoTocar={() => { setRascunho(null); setMsg(null); }} />
        </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  if (fotografando) {
    if (!permissao) return <View style={{ flex: 1, backgroundColor: c.fundo }} />;
    if (!permissao.granted) {
      return (
        <SafeAreaView className="flex-1 bg-papel p-[24px] gap-[16px] justify-center">
          <Titulo>Câmera</Titulo>
          <Apagado>Para treinar o juiz, o WishLens precisa da câmera.</Apagado>
          <Botao titulo="Permitir a câmera" aoTocar={pedirPermissao} />
          <Botao titulo="Voltar" tipo="secundario" aoTocar={() => setFotografando(false)} />
        </SafeAreaView>
      );
    }
    return (
      <View style={{ flex: 1, backgroundColor: '#000' }}>
        <CameraView ref={camera} style={{ flex: 1 }} facing="back" onCameraReady={() => setPronta(true)} />
        <SafeAreaView edges={['top', 'bottom']} pointerEvents="box-none"
          style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, justifyContent: 'space-between' }}>
          <View style={{ padding: 16, gap: 8, alignItems: 'flex-start' }}>
            <Pressable accessibilityRole="button" accessibilityLabel="Mudar o que vou fotografar" onPress={() => setFotografando(false)}
              style={{ minHeight: 48, paddingHorizontal: 14, borderRadius: 6, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'center' }}>
              <Text className="font-texto-forte" style={{ color: '#fff', fontSize: 15 }}>Mudar</Text>
            </Pressable>
            <Text className="font-texto" style={{ color: '#fff', fontSize: 15, backgroundColor: 'rgba(0,0,0,0.55)', padding: 8, borderRadius: 6, overflow: 'hidden' }}>
              {nomeTema}{tema === 'competicao' ? ` (${resultado === 'vitoria' ? 'vitória' : 'derrota'})` : objeto ? `: ${objeto}` : ''} · {TIPOS.find((t) => t.valor === tipo)?.texto}
            </Text>
          </View>
          <View style={{ alignItems: 'center', gap: 12, paddingBottom: 12 }}>
            {msg ? (
              <Text className="font-texto-forte" accessibilityLiveRegion="polite"
                style={{ color: '#fff', fontSize: 15, backgroundColor: msg.erro ? '#B3261E' : 'rgba(0,0,0,0.65)', padding: 8, borderRadius: 6, overflow: 'hidden' }}>
                {msg.texto}
              </Text>
            ) : null}
            <Pressable accessibilityRole="button" accessibilityLabel="Tirar a foto" disabled={!pronta || enviando} onPress={fotografar}
              onPressIn={() => setApertado(true)} onPressOut={() => setApertado(false)}
              // estilo fixo e sem className (regra do scripts/checar_app.js: Pressable com estilo em função some no celular)
              style={{ width: 78, height: 78, borderRadius: 39, borderWidth: 5, borderColor: '#fff', alignItems: 'center', justifyContent: 'center',
                backgroundColor: apertado ? c.destaque : 'rgba(255,255,255,0.25)', opacity: pronta && !enviando ? 1 : 0.4 }}>
              <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: '#fff' }} />
            </Pressable>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-papel">
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }} keyboardShouldPersistTaps="handled">
        <Titulo>Treinar o juiz</Titulo>
        <Apagado>
          Escolha o que vai fotografar e como a foto é. Fotos falsas (na tela, impressa, brinquedo) ajudam tanto quanto as reais.
        </Apagado>
        {d ? (
          <Text className="font-texto text-tinta text-[15px]" accessibilityLiveRegion="polite">
            <Text className="font-numero">{d.total}</Text> fotos da turma, <Text className="font-numero">{d.minhas}</Text> suas.
            {falta ? <> Faltam <Text className="font-numero">{falta}</Text> de {nomeTema}.</> : <> {nomeTema} já chegou à meta.</>}
          </Text>
        ) : null}

        <Subtitulo>O que é</Subtitulo>
        <Fichas rotulo="O que vai fotografar" valor={tema} aoEscolher={(t) => { setTema(t); setObjeto(''); }} opcoes={opcoesTema} />
        {objetos.length ? (
          <>
            <Apagado>Qual objeto? O juiz aprende a diferenciar um do outro.</Apagado>
            <Fichas rotulo="Qual objeto" valor={objeto} aoEscolher={setObjeto}
              opcoes={[{ valor: '', texto: 'Não sei / outro' }, ...objetos.map((o) => ({ valor: o, texto: o }))]} />
          </>
        ) : null}
        {tema === 'competicao' ? (
          <Fichas rotulo="Resultado da partida" valor={resultado} aoEscolher={setResultado}
            opcoes={[{ valor: 'vitoria', texto: 'Vitória' }, { valor: 'derrota', texto: 'Derrota' }]} />
        ) : null}

        <Subtitulo>Como a foto é</Subtitulo>
        <Fichas rotulo="Tipo da foto" valor={tipo} aoEscolher={setTipo} opcoes={TIPOS.map((t) => ({ valor: t.valor, texto: t.texto }))} />
        {dicaTipo ? <Apagado>{dicaTipo}</Apagado> : null}
        {d ? (
          <Apagado>
            {TIPOS.map((t) => `${t.texto} ${d.por_tipo[t.valor] ?? 0}`).join(' · ')} (meta {d.meta_tipo} de cada)
          </Apagado>
        ) : null}

        <Botao titulo="Abrir a câmera" aoTocar={() => { setMsg(null); setFotografando(true); }} />
        <Botao titulo="Voltar" tipo="secundario" aoTocar={() => router.back()} />
      </ScrollView>
    </SafeAreaView>
  );
}
