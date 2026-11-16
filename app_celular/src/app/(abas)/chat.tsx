// Chat: pedidos de amizade, adicionar amigo pelo apelido e a lista de conversas.
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Botao, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { quandoFoi } from '../../lib/quando';
import { useCores } from '../../lib/cores';
import { useDados } from '../../lib/useDados';

export default function Chat() {
  const c = useCores();
  const amigos = useDados(api.amigos, [], 10);
  const [novo, setNovo] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const d = amigos.dados;

  async function fazer(acao: () => Promise<unknown>, ok?: string) {
    setOcupado(true);
    setMsg(null);
    try {
      await acao();
      if (ok) setMsg({ texto: ok, erro: false });
      await amigos.recarregar();
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não deu certo. Tente de novo.', erro: true });
    } finally {
      setOcupado(false);
    }
  }

  async function adicionar() {
    const apelido = novo.trim();
    await fazer(async () => {
      const r = await api.pedirAmizade(apelido);
      setNovo('');
      setMsg({ texto: r.estado === 'aceita' ? `Você e ${apelido} agora são amigos.` : `Pedido enviado para ${apelido}.`, erro: false });
    });
  }

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }} keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={amigos.carregando} onRefresh={amigos.recarregar} tintColor={c.destaque} />}>
        <Titulo>Chat</Titulo>

        <View style={{ flexDirection: 'row', gap: 8 }}>
          <TextInput value={novo} onChangeText={setNovo} placeholder="Apelido do amigo" placeholderTextColor={c.apagado}
            autoCapitalize="none" autoCorrect={false} maxLength={30} accessibilityLabel="Apelido do amigo para adicionar"
            onSubmitEditing={adicionar} returnKeyType="send"
            style={{ flex: 1, minHeight: 48, borderWidth: 1.5, borderColor: c.linha, borderRadius: 14, paddingHorizontal: 14,
              fontSize: 16, color: c.tinta, backgroundColor: c.superficie }} />
          <Botao titulo="Adicionar" aoTocar={adicionar} desativado={novo.trim().length < 2 || ocupado} estilo={{ paddingHorizontal: 16 }} />
        </View>
        {msg ? <Text accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
        {amigos.erro && !d ? <Aviso texto={amigos.erro} aoTentar={amigos.recarregar} /> : null}

        {d?.recebidos.length ? (
          <>
            <Subtitulo>Pedidos de amizade</Subtitulo>
            {d.recebidos.map((a) => (
              <Cartaz key={a} estilo={{ gap: 10 }}>
                <Text style={{ color: c.tinta, fontSize: 16 }}><Text style={{ fontWeight: '700' }}>{a}</Text> quer ser seu amigo.</Text>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <Botao titulo="Aceitar" estilo={{ flex: 1 }} desativado={ocupado} aoTocar={() => fazer(() => api.responderAmizade(a, true))} />
                  <Botao titulo="Recusar" tipo="secundario" estilo={{ flex: 1 }} desativado={ocupado}
                    aoTocar={() => fazer(() => api.responderAmizade(a, false))} />
                </View>
              </Cartaz>
            ))}
          </>
        ) : null}

        <Subtitulo>Conversas</Subtitulo>
        {d && !d.amigos.length ? (
          <Apagado>Você ainda não tem amigos no WishLens. Adicione alguém pelo apelido que aparece no Pódio.</Apagado>
        ) : null}
        {d?.amigos.map((a) => (
          <Pressable key={a.apelido} accessibilityRole="button"
            accessibilityLabel={`Conversa com ${a.apelido}${a.nao_lidas ? `, ${a.nao_lidas} não lidas` : ''}`}
            onPress={() => router.push({ pathname: '/conversa/[apelido]', params: { apelido: a.apelido } })}
            style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 14,
              backgroundColor: pressed ? c.suave : c.superficie, borderWidth: 1, borderColor: c.linha })}>
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: c.suave, alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: c.destaque, fontSize: 18, fontWeight: '800' }}>{a.apelido.slice(0, 1).toUpperCase()}</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={{ color: c.tinta, fontSize: 16, fontWeight: '700' }}>{a.apelido}</Text>
              <Text numberOfLines={1} style={{ color: c.apagado, fontSize: 14 }}>
                {a.ultima ? `${a.ultima.minha ? 'Você: ' : ''}${a.ultima.texto}` : 'Diga oi!'}
              </Text>
            </View>
            <View style={{ alignItems: 'flex-end', gap: 4 }}>
              {a.ultima ? <Text style={{ color: c.apagado, fontSize: 12 }}>{quandoFoi(a.ultima.criado_em)}</Text> : null}
              {a.nao_lidas ? (
                <View style={{ minWidth: 22, height: 22, borderRadius: 11, paddingHorizontal: 6, backgroundColor: c.destaque,
                  alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: c.fundo, fontSize: 12, fontWeight: '800' }}>{a.nao_lidas}</Text>
                </View>
              ) : null}
            </View>
          </Pressable>
        ))}

        {d?.enviados.length ? (
          <Apagado estilo={{ marginTop: 8 }}>Esperando resposta: {d.enviados.join(', ')}.</Apagado>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
