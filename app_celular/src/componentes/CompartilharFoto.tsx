// Depois da foto do jogo: mandar para um amigo pelo chat (a foto e, se valeu pontos, o cartão do achado) ou salvar
// no celular.
import { requestPermissionsAsync, Asset } from 'expo-media-library';
import { router } from 'expo-router';
import { isAvailableAsync, shareAsync } from 'expo-sharing';
import { useState } from 'react';
import { ActivityIndicator, Modal, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type Amigo } from '../lib/api';
import { salvarNaGaleria, type FotoGaleria } from '../lib/galeria';
import { FONTE_TITULO, useCores, PALETA } from '../lib/cores';
import { Apagado, Botao } from './ui';

type Placa = Pick<FotoGaleria, 'achado' | 'emoji' | 'tema' | 'temaId' | 'cor' | 'pontos'>;

export function CompartilharFoto({ foto, enviada, captura, aceita, placa }: {
  foto: string; enviada: string; captura: string; aceita: boolean; placa?: Placa;
}) {
  const c = useCores();
  const baixo = useSafeAreaInsets().bottom;
  const [amigos, setAmigos] = useState<Amigo[] | null>(null);
  const [aberto, setAberto] = useState(false);
  const [msg, setMsg] = useState<{ texto: string; erro: boolean; para?: string; galeria?: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function abrir() {
    setAberto(true);
    setMsg(null);
    try {
      setAmigos((await api.amigos()).amigos);
    } catch (e) {
      setAberto(false);
      setMsg({ texto: e instanceof Error ? e.message : 'Não consegui abrir seus amigos.', erro: true });
    }
  }

  async function mandar(apelido: string) {
    setOcupado(true);
    try {
      await api.enviarMensagem(apelido, { foto: enviada, captura: aceita ? captura : undefined });
      setMsg({ texto: `Enviado para ${apelido}.`, erro: false, para: apelido });
      setAberto(false);
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não deu para enviar.', erro: true });
    } finally {
      setOcupado(false);
    }
  }

  // Salvar = galeria do app (sem permissão, funciona no Expo Go). O celular é um passo a mais, só se a pessoa pedir.
  async function salvar() {
    setMsg(null);
    try {
      const nova = await salvarNaGaleria(enviada, { id: captura, achado: placa?.achado || 'Foto', emoji: placa?.emoji ?? '',
        tema: placa?.tema ?? '', temaId: placa?.temaId, cor: placa?.cor ?? c.apagado, pontos: placa?.pontos ?? 0 });
      setMsg({ texto: nova ? 'Salva no seu museu.' : 'Esta foto já está no seu museu.', erro: false, galeria: true });
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não consegui salvar a foto.', erro: true });
    }
  }

  async function salvarNoCelular() {
    try {
      if (!(await requestPermissionsAsync(true, ['photo'])).granted) {
        setMsg({ texto: 'Para salvar no celular, o WishLens precisa de permissão para guardar fotos.', erro: true });
        return;
      }
      await Asset.create(foto);
      setMsg({ texto: 'Foto salva no museu e na galeria do celular.', erro: false });
    } catch {
      // No Expo Go do Android a galeria é bloqueada: a folha de compartilhar do celular salva em Fotos, Arquivos ou Drive
      try {
        if (!(await isAvailableAsync())) throw new Error();
        await shareAsync(foto, { mimeType: 'image/jpeg', dialogTitle: 'Salvar a foto', UTI: 'public.jpeg' });
      } catch {
        setMsg({ texto: 'Não consegui salvar a foto neste celular.', erro: true });
      }
    }
  }

  return (
    <View className="gap-[10px]">
      <View className="flex-row gap-[8px]">
        <Botao titulo={aceita ? 'Enviar com o cartão' : 'Enviar a um amigo'} estilo={{ flex: 1 }} aoTocar={abrir}
          rotulo={aceita ? 'Enviar a foto e o cartão do achado a um amigo' : 'Enviar a foto a um amigo'} />
        <Botao titulo="Salvar" tipo="secundario" aoTocar={salvar} rotulo="Salvar a foto no seu museu" />
      </View>
      {msg ? (
        <View>
          <Text className="font-texto" accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>
            {msg.texto}
          </Text>
          {msg.para ? (
            <Pressable className="min-h-[44px] self-start justify-center" accessibilityRole="link"
              onPress={() => router.push({ pathname: '/conversa/[apelido]', params: { apelido: msg.para! } })}>
              <Text className="font-texto-forte text-destaque underline">Abrir a conversa</Text>
            </Pressable>
          ) : null}
          {msg.galeria ? (
            <>
              <Pressable className="min-h-[44px] self-start justify-center" accessibilityRole="link" onPress={() => router.navigate('/colecao')}>
                <Text className="font-texto-forte text-destaque underline">Ver no museu</Text>
              </Pressable>
              {Platform.OS !== 'web' ? (
                <Pressable className="min-h-[44px] self-start justify-center" accessibilityRole="link" onPress={salvarNoCelular}>
                  <Text className="font-texto-forte text-destaque underline">Salvar também no celular</Text>
                </Pressable>
              ) : null}
            </>
          ) : null}
        </View>
      ) : null}

      <Modal visible={aberto} transparent animationType="slide" onRequestClose={() => setAberto(false)}>
        <Pressable accessibilityLabel="Fechar" onPress={() => setAberto(false)} style={{ flex: 1, backgroundColor: `${PALETA.escuro.fundo}66` }} />
        <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 6, borderTopRightRadius: 6, maxHeight: '70%',
          padding: 16, paddingBottom: baixo + 16, gap: 10 }}>
          <Text accessibilityRole="header" className="font-titulo text-[22px] text-tinta">Enviar para quem?</Text>
          {amigos === null ? <ActivityIndicator color={c.destaque} /> : null}
          {amigos?.length === 0 ? <Apagado>Você ainda não tem amigos no WishLens. Adicione alguém na aba Amigos.</Apagado> : null}
          <ScrollView contentContainerStyle={{ gap: 8 }}>
            {amigos?.map((a) => (
              <Pressable key={a.apelido} accessibilityRole="button" accessibilityLabel={`Enviar para ${a.apelido}`} disabled={ocupado}
                onPress={() => mandar(a.apelido)}
                className="flex-row items-center gap-3 p-3 rounded-ficha bg-ficha active:bg-suave border border-linha"
                style={{ opacity: ocupado ? 0.6 : 1 }}>
                <View className="w-[40px] h-[40px] rounded-full bg-suave items-center justify-center">
                  <Text className="font-texto-forte text-destaque text-[17px]" >{a.apelido.slice(0, 1).toUpperCase()}</Text>
                </View>
                <Text className="font-texto-forte flex-1 text-tinta text-[16px]" >{a.apelido}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <Apagado estilo={{ fontSize: 12 }}>A localização da foto é apagada antes de enviar.</Apagado>
        </View>
      </Modal>
    </View>
  );
}
