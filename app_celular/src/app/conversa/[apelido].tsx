// Conversa com um amigo: texto, fotos (câmera ou galeria) e cartões de achado. Segurar uma mensagem abre as opções.
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { router, useLocalSearchParams } from 'expo-router';
import { useRef, useState } from 'react';
import { ActivityIndicator, Image, KeyboardAvoidingView, Modal, Pressable, ScrollView, Text, TextInput, View, type ScrollViewInstance } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao } from '../../componentes/ui';
import { api, SERVIDOR, type CartaoAchado, type Mensagem } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { quandoFoi } from '../../lib/quando';
import { useDados } from '../../lib/useDados';

// O endereço da foto vem assinado pelo juiz e só chega a quem está na conversa (servidor/chat.py)
function FotoProtegida({ caminho, estilo, inteira }: { caminho: string; estilo: object; inteira?: boolean }) {
  const fonte = { uri: SERVIDOR + caminho };
  return <Image source={fonte} style={estilo} resizeMode={inteira ? 'contain' : 'cover'} accessibilityLabel="Foto enviada no chat" />;
}

function Cartao({ cartao }: { cartao: CartaoAchado }) {
  return (
    <View style={{ borderRadius: 12, borderWidth: 3, borderColor: '#fff', backgroundColor: cartao.cor, padding: 12, gap: 2, minWidth: 200 }}
      accessible accessibilityLabel={`Cartão de achado: ${cartao.achado}, ${cartao.nome}, ${cartao.pontos} pontos`}>
      <Text className="font-texto text-[28px]" >{cartao.emoji}</Text>
      <Text className="font-texto-forte" style={{ color: '#fff', fontSize: 12, fontWeight: '700' }}>{cartao.nome}</Text>
      <Text style={{ color: '#fff', fontFamily: FONTE_TITULO, fontSize: 20 }}>{cartao.achado}</Text>
      <Text className="font-texto-forte" style={{ color: '#fff', fontSize: 15, fontWeight: '800' }}>+{cartao.pontos} pts</Text>
    </View>
  );
}

export default function Conversa() {
  const c = useCores();
  const { apelido } = useLocalSearchParams<{ apelido: string }>();
  const conversa = useDados(() => api.conversa(apelido), [apelido], 4);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [opcoes, setOpcoes] = useState<Mensagem | 'conversa' | null>(null);
  const [aberta, setAberta] = useState<string | null>(null);
  const lista = useRef<ScrollViewInstance>(null);
  const mensagens = conversa.dados?.mensagens ?? [];

  async function mandar(m: { texto?: string; foto?: string }) {
    setEnviando(true);
    setErro(null);
    try {
      await api.enviarMensagem(apelido, m);
      if (m.texto) setTexto('');
      await conversa.recarregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não deu para enviar.');
    } finally {
      setEnviando(false);
    }
  }

  async function foto(daCamera: boolean) {
    setErro(null);
    if (daCamera && !(await ImagePicker.requestCameraPermissionsAsync()).granted) {
      setErro('Para tirar a foto, o WishLens precisa da câmera.');
      return;
    }
    const opcoesFoto: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.8 };
    const r = daCamera ? await ImagePicker.launchCameraAsync(opcoesFoto) : await ImagePicker.launchImageLibraryAsync(opcoesFoto);
    if (!r.canceled && r.assets[0]) await mandar({ foto: r.assets[0].uri });
  }

  async function acao(fazer: () => Promise<unknown>, depois?: () => void) {
    setOpcoes(null);
    try {
      await fazer();
      if (depois) depois();
      else await conversa.recarregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não deu certo.');
    }
  }

  const escolhida = opcoes && opcoes !== 'conversa' ? opcoes : null;
  return (
    <SafeAreaView edges={['top', 'bottom']} className="flex-1 bg-papel">
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 8, paddingVertical: 6,
        borderBottomWidth: 1, borderBottomColor: c.linha }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={() => (router.canGoBack() ? router.back() : router.replace('/chat'))}
          className="w-[44px] h-[44px] items-center justify-center">
          <Ionicons name="chevron-back" size={26} color={c.tinta} />
        </Pressable>
        <Text accessibilityRole="header" className="flex-1 font-titulo text-[20px] text-tinta">{apelido}</Text>
        <Pressable accessibilityRole="button" accessibilityLabel="Opções da conversa" onPress={() => setOpcoes('conversa')}
          className="w-[44px] h-[44px] items-center justify-center">
          <Ionicons name="ellipsis-vertical" size={22} color={c.tinta} />
        </Pressable>
      </View>

      <KeyboardAvoidingView className="flex-1" behavior="padding">
        <ScrollView ref={lista} contentContainerStyle={{ padding: 12, gap: 8 }}
          onContentSizeChange={() => lista.current?.scrollToEnd({ animated: false })}>
          <Apagado estilo={{ textAlign: 'center', fontSize: 12 }}>Só vocês dois veem estas mensagens. A localização das fotos é apagada antes de enviar.</Apagado>
          {conversa.erro && !conversa.dados ? <Text className="font-texto text-carimbo" >{conversa.erro}</Text> : null}
          {mensagens.map((m) => m.sistema ? (
            <Text className="font-texto self-center text-apagado text-[13px] py-[4px]" key={m.id} >{m.texto}</Text>
          ) : (
            <Pressable key={m.id} onLongPress={() => setOpcoes(m)} delayLongPress={350}
              accessibilityHint="Segure para ver as opções da mensagem"
              style={{ alignSelf: m.minha ? 'flex-end' : 'flex-start', maxWidth: '82%', gap: 4, padding: m.texto ? 10 : 4,
                borderRadius: 16, borderBottomRightRadius: m.minha ? 4 : 16, borderBottomLeftRadius: m.minha ? 16 : 4,
                backgroundColor: m.minha ? c.destaque : c.superficie, borderWidth: m.minha ? 0 : 1, borderColor: c.linha }}>
              {m.cartao ? <Cartao cartao={m.cartao} /> : null}
              {m.foto ? (
                <Pressable onPress={() => setAberta(m.foto)} accessibilityRole="imagebutton" accessibilityLabel="Abrir a foto">
                  <FotoProtegida caminho={m.foto} estilo={{ width: 220, height: 220, borderRadius: 12 }} />
                </Pressable>
              ) : null}
              {m.texto ? <Text className="font-texto" style={{ color: m.minha ? c.fundo : c.tinta, fontSize: 16, lineHeight: 21 }}>{m.texto}</Text> : null}
              <Text className="font-texto" style={{ color: m.minha ? c.fundo : c.apagado, opacity: 0.75, fontSize: 11, alignSelf: 'flex-end' }}>{quandoFoi(m.criado_em)}</Text>
            </Pressable>
          ))}
        </ScrollView>

        {erro ? <Text className="font-texto text-carimbo px-[12px]" accessibilityLiveRegion="assertive" >{erro}</Text> : null}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 6, padding: 8, borderTopWidth: 1, borderTopColor: c.linha }}>
          <Pressable accessibilityRole="button" accessibilityLabel="Tirar foto e enviar" onPress={() => foto(true)} disabled={enviando}
            className="w-[44px] h-[44px] items-center justify-center">
            <Ionicons name="camera-outline" size={26} color={c.destaque} />
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Enviar foto da galeria" onPress={() => foto(false)} disabled={enviando}
            className="w-[44px] h-[44px] items-center justify-center">
            <Ionicons name="image-outline" size={26} color={c.destaque} />
          </Pressable>
          <TextInput value={texto} onChangeText={setTexto} placeholder="Mensagem" placeholderTextColor={c.apagado} multiline maxLength={500}
            accessibilityLabel="Mensagem"
            style={{ flex: 1, minHeight: 44, maxHeight: 120, borderWidth: 1.5, borderColor: c.linha, borderRadius: 22, paddingHorizontal: 14,
              paddingTop: 11, paddingBottom: 11, fontSize: 16, color: c.tinta, backgroundColor: c.superficie }} />
          <Pressable accessibilityRole="button" accessibilityLabel="Enviar mensagem" onPress={() => mandar({ texto: texto.trim() })}
            disabled={enviando || !texto.trim()}
            style={{ width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center',
              backgroundColor: texto.trim() ? c.destaque : c.linha }}>
            {enviando ? <ActivityIndicator color={c.fundo} /> : <Ionicons name="send" size={20} color={c.fundo} />}
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      {/* Opções: da mensagem (apagar, denunciar) ou da conversa (desfazer amizade, bloquear) */}
      <Modal visible={!!opcoes} transparent animationType="fade" onRequestClose={() => setOpcoes(null)}>
        <Pressable accessibilityLabel="Fechar" onPress={() => setOpcoes(null)} style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, gap: 10 }}>
            {escolhida?.minha ? (
              <Botao titulo="Apagar para os dois" aoTocar={() => acao(() => api.apagarMensagem(escolhida.id))} />
            ) : null}
            {escolhida && !escolhida.minha ? (
              <Botao titulo="Denunciar esta mensagem" aoTocar={() => acao(() => api.denunciar(escolhida.id, 'denúncia pelo app'),
                () => setErro('Denúncia enviada. Ela vai ser lida.'))} />
            ) : null}
            {opcoes === 'conversa' ? (
              <Botao titulo="Desfazer amizade" tipo="secundario" aoTocar={() => acao(() => api.desfazerAmizade(apelido), () => router.replace('/chat'))} />
            ) : null}
            {opcoes === 'conversa' || (escolhida && !escolhida.minha) ? (
              <Botao titulo={`Bloquear ${apelido}`} tipo="secundario" aoTocar={() => acao(() => api.bloquear(apelido), () => router.replace('/chat'))} />
            ) : null}
            <Botao titulo="Cancelar" tipo="secundario" aoTocar={() => setOpcoes(null)} />
          </View>
        </Pressable>
      </Modal>

      {/* Foto em tela cheia */}
      <Modal visible={!!aberta} transparent animationType="fade" onRequestClose={() => setAberta(null)}>
        <Pressable accessibilityLabel="Fechar a foto" onPress={() => setAberta(null)}
          style={{ flex: 1, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' }}>
          {aberta ? <FotoProtegida caminho={aberta} estilo={{ width: '100%', height: '80%' }} inteira /> : null}
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
