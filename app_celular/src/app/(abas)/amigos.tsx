// Amigos: adicionar pelo apelido, responder pedidos e comparar os pontos com os amigos, como no Pódio.
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Analises } from '../../componentes/Analises';
import { Degraus } from '../../componentes/Degraus';
import { SeletorAba } from '../../componentes/SeletorAba';
import { Apagado, Aviso, Botao, Cartaz, Fichas, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { useCores } from '../../lib/cores';
import { useModo } from '../../lib/modo';
import { useVisita } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';

type Periodo = 'hoje' | 'semana' | 'geral';

export default function Amigos() {
  const c = useCores();
  const modo = useModo();
  const [periodo, setPeriodo] = useState<Periodo>('hoje');
  const amigos = useDados(api.amigos, [], 10);
  const placar = useDados(() => api.placarAmigos(periodo, modo), [periodo, modo], 30);
  const [novo, setNovo] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const d = amigos.dados;
  const visita = useVisita();
  const ranking = placar.dados?.ranking ?? [];
  const eu = ranking.find((r) => r.voce);
  const acima = eu && eu.posicao > 1 ? ranking[eu.posicao - 2] : null;
  const falta = eu && acima ? acima.pontos - eu.pontos + 1 : 0;

  async function fazer(acao: () => Promise<unknown>) {
    setOcupado(true);
    setMsg(null);
    try {
      await acao();
      await Promise.all([amigos.recarregar(), placar.recarregar()]);
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
    <SafeAreaView edges={['top']} className="flex-1 bg-papel">
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }} keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={placar.carregando} onRefresh={() => fazer(async () => {})} tintColor={c.destaque} />}>
        <Titulo>Amigos</Titulo>

        <View className="flex-row gap-[8px]">
          <TextInput value={novo} onChangeText={setNovo} placeholder="Apelido do amigo" placeholderTextColor={c.apagado}
            autoCapitalize="none" autoCorrect={false} maxLength={30} accessibilityLabel="Apelido do amigo para adicionar"
            onSubmitEditing={adicionar} returnKeyType="send"
            className="flex-1 min-h-[48px] border border-linha rounded-ficha px-[14px] text-[16px] text-tinta bg-ficha" />
          <Botao titulo="Adicionar" aoTocar={adicionar} desativado={novo.trim().length < 2 || ocupado} estilo={{ paddingHorizontal: 16 }} />
        </View>
        {msg ? <Text className="font-texto" accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
        {amigos.erro && !d ? <Aviso texto={amigos.erro} aoTentar={amigos.recarregar} /> : null}

        {d?.recebidos.length ? (
          <>
            <Subtitulo>Pedidos de amizade</Subtitulo>
            {d.recebidos.map((a) => (
              <Cartaz key={a} estilo={{ gap: 10 }}>
                <Text className="font-texto text-tinta text-[16px]" ><Text className="font-texto-forte" >{a}</Text> quer ser seu amigo.</Text>
                <View className="flex-row gap-[8px]">
                  <Botao titulo="Aceitar" estilo={{ flex: 1 }} desativado={ocupado} aoTocar={() => fazer(() => api.responderAmizade(a, true))} />
                  <Botao titulo="Recusar" tipo="secundario" estilo={{ flex: 1 }} desativado={ocupado}
                    aoTocar={() => fazer(() => api.responderAmizade(a, false))} />
                </View>
              </Cartaz>
            ))}
          </>
        ) : null}
        {d?.enviados.length ? <Apagado>Esperando resposta: {d.enviados.join(', ')}.</Apagado> : null}

        <Subtitulo>Placar entre amigos</Subtitulo>
        <Fichas<Periodo> rotulo="Período" valor={periodo} aoEscolher={setPeriodo}
          opcoes={[{ valor: 'hoje', texto: 'Hoje' }, { valor: 'semana', texto: 'Semana' }, { valor: 'geral', texto: 'Geral' }]} />
        <SeletorAba />
        {placar.erro && !placar.dados ? <Aviso texto={placar.erro} aoTentar={placar.recarregar} /> : null}
        {d && !d.amigos.length ? (
          <Apagado>Adicione um amigo pelo apelido (o mesmo que aparece no Pódio) para comparar os pontos.</Apagado>
        ) : null}
        {ranking.length > 1 && ranking[0].pontos > 0 ? <Degraus ranking={ranking} chave={`amigos-${modo}-${periodo}-${visita}`} /> : null}
        {eu && ranking.length > 1 ? (
          <Text className="font-texto text-tinta text-[16px]" >
            {ranking[0].pontos === 0 ? 'Ninguém pontuou ainda. Tire a primeira foto!'
              : acima ? <>Faltam <Text className="font-numero">{falta}</Text> {falta === 1 ? 'ponto' : 'pontos'} para passar {acima.apelido}.</>
              : 'Você lidera entre seus amigos.'}
          </Text>
        ) : null}
        {ranking.length > 1 ? (
          <Cartaz estilo={{ padding: 0, overflow: 'hidden' }}>
            {ranking.map((r, i) => (
              <Pressable key={r.apelido} disabled={r.voce} accessibilityRole={r.voce ? undefined : 'button'}
                accessibilityLabel={`${r.posicao}º, ${r.apelido}${r.voce ? ' (você)' : ''}, ${r.pontos} pontos, ${r.achados} achados${r.voce ? '' : '. Abrir a conversa'}`}
                onPress={() => router.push({ pathname: '/conversa/[apelido]', params: { apelido: r.apelido } })}
                className={`flex-row items-center py-3 px-4 gap-3 border-linha active:bg-suave ${r.voce ? 'bg-suave' : ''} ${i < ranking.length - 1 ? 'border-b' : ''}`}>
                <Text className="font-numero w-[32px] text-apagado" >{r.posicao}º</Text>
                <View className="flex-1">
                  <Text className="font-texto text-tinta text-[16px]" >{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                  <Text className="font-texto text-apagado text-[13px]" ><Text className="font-numero">{r.achados}</Text> {r.achados === 1 ? 'achado' : 'achados'}</Text>
                </View>
                <Text className="font-texto text-tinta"><Text className="font-numero">{r.pontos}</Text> pts</Text>
              </Pressable>
            ))}
          </Cartaz>
        ) : null}

        <Analises amigos={(d?.amigos ?? []).map((a) => a.apelido)} visita={visita} />
      </ScrollView>
    </SafeAreaView>
  );
}
