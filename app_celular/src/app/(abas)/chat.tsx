// Chat: a lista de conversas com os amigos (adicionar e aceitar amigos fica na aba Amigos).
import { router } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Botao, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { quandoFoi } from '../../lib/quando';
import { useCores } from '../../lib/cores';
import { Surge, useVisita } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';

export default function Chat() {
  const c = useCores();
  const amigos = useDados(api.amigos, [], 10);
  const d = amigos.dados;
  const visita = useVisita();

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-papel">
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
        {d?.amigos.map((a, i) => (
          <Surge key={a.apelido} ordem={i} chave={visita}><Pressable accessibilityRole="button"
            accessibilityLabel={`Conversa com ${a.apelido}${a.nao_lidas ? `, ${a.nao_lidas} não lidas` : ''}`}
            onPress={() => router.push({ pathname: '/conversa/[apelido]', params: { apelido: a.apelido } })}
            style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 14,
              backgroundColor: pressed ? c.suave : c.superficie, borderWidth: 1, borderColor: c.linha })}>
            <View className="w-[44px] h-[44px] rounded-[22px] bg-suave items-center justify-center">
              <Text className="font-texto-forte text-destaque text-[18px]" >{a.apelido.slice(0, 1).toUpperCase()}</Text>
            </View>
            <View className="flex-1 gap-[2px]">
              <Text className="font-texto-forte text-tinta text-[16px]" >{a.apelido}</Text>
              <Text className="font-texto text-apagado text-[14px]" numberOfLines={1} >
                {a.ultima ? `${a.ultima.minha ? 'Você: ' : ''}${a.ultima.texto}` : 'Diga oi!'}
              </Text>
            </View>
            <View className="items-end gap-[4px]">
              {a.ultima ? <Text className="font-texto text-apagado text-[12px]" >{quandoFoi(a.ultima.criado_em)}</Text> : null}
              {a.nao_lidas ? (
                <View className="min-w-[22px] h-[22px] rounded-[11px] px-[6px] bg-destaque items-center justify-center">
                  <Text className="font-texto-forte text-papel text-[12px]" >{a.nao_lidas}</Text>
                </View>
              ) : null}
            </View>
          </Pressable></Surge>
        ))}

      </ScrollView>
    </SafeAreaView>
  );
}
