// Chat: a lista de conversas com os amigos (adicionar e aceitar amigos fica na aba Amigos).
import { router } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Botao, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { quandoFoi } from '../../lib/quando';
import { useCores } from '../../lib/cores';
import { useDados } from '../../lib/useDados';

export default function Chat() {
  const c = useCores();
  const amigos = useDados(api.amigos, [], 10);
  const d = amigos.dados;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }} keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={amigos.carregando} onRefresh={amigos.recarregar} tintColor={c.destaque} />}>
        <Titulo>Chat</Titulo>

        {amigos.erro && !d ? <Aviso texto={amigos.erro} aoTentar={amigos.recarregar} /> : null}
        {d?.recebidos.length ? (
          <Botao titulo={`${d.recebidos.length} ${d.recebidos.length === 1 ? 'pedido' : 'pedidos'} de amizade`} tipo="secundario"
            aoTocar={() => router.navigate('/amigos')} rotulo="Ver os pedidos de amizade na aba Amigos" />
        ) : null}
        <Subtitulo>Conversas</Subtitulo>
        {d && !d.amigos.length ? (
          <Apagado>Você ainda não tem amigos no WishLens. Adicione alguém na aba Amigos.</Apagado>
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

      </ScrollView>
    </SafeAreaView>
  );
}
