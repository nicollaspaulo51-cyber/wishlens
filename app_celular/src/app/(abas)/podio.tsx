import { useState } from 'react';
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Cartaz, Fichas, Subtitulo, Titulo } from '../../componentes/ui';
import { api, type LinhaPodio } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useDados } from '../../lib/useDados';

type Periodo = 'hoje' | 'semana' | 'geral';

export default function Podio() {
  const c = useCores();
  const [periodo, setPeriodo] = useState<Periodo>('hoje');
  const [tema, setTema] = useState('todos');
  const temas = useDados(api.temas);
  const podio = useDados(() => api.podio(periodo, tema === 'todos' ? null : tema), [periodo, tema], 30);
  const ranking = podio.dados?.ranking ?? [];
  const eu = ranking.find((r) => r.voce);

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={podio.carregando} onRefresh={podio.recarregar} tintColor={c.destaque} />}>
        <Titulo>Pódio</Titulo>
        <Fichas<Periodo> rotulo="Período" valor={periodo} aoEscolher={setPeriodo}
          opcoes={[{ valor: 'hoje', texto: 'Hoje' }, { valor: 'semana', texto: 'Semana' }, { valor: 'geral', texto: 'Geral' }]} />
        <Fichas rotulo="Tema" valor={tema} aoEscolher={setTema}
          opcoes={[{ valor: 'todos', texto: 'Todos' }, ...(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: `${t.emoji} ${t.nome}` }))]} />
        {podio.erro && !podio.dados ? <Aviso texto={podio.erro} aoTentar={podio.recarregar} /> : null}
        {podio.dados && ranking.length === 0 ? <Aviso texto="Ninguém pontuou neste período ainda. Tire a primeira foto em Jogar." /> : null}
        {ranking.length ? <Degraus ranking={ranking} /> : null}
        {eu ? <Text style={{ color: c.tinta, fontSize: 16 }}>Você está em <Text style={{ fontWeight: '700' }}>{eu.posicao}º</Text> de {ranking.length}.</Text> : null}
        {ranking.length > 3 ? (
          <Cartaz estilo={{ paddingVertical: 4 }}>
            {ranking.slice(3).map((r) => (
              <View key={r.apelido} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 10, gap: 12,
                borderBottomWidth: 1, borderBottomColor: c.linha, backgroundColor: r.voce ? c.suave : 'transparent' }}>
                <Text style={{ width: 32, color: c.apagado, fontWeight: '700' }}>{r.posicao}º</Text>
                <Text style={{ flex: 1, color: c.tinta, fontSize: 16 }}>{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text style={{ color: c.tinta, fontWeight: '700' }}>{r.pontos} pts</Text>
              </View>
            ))}
          </Cartaz>
        ) : null}

        <Subtitulo>Guardiões da semana</Subtitulo>
        <Apagado>Quem tem mais achados diferentes num quadrado de ~500 m guarda aquele quadrado até domingo. Só contam quadrados onde 2 pessoas ou mais jogaram.</Apagado>
        {podio.dados?.guardioes.length ? (
          <Cartaz estilo={{ paddingVertical: 4 }}>
            {podio.dados.guardioes.map((g) => (
              <View key={g.apelido} style={{ flexDirection: 'row', paddingVertical: 10 }}>
                <Text style={{ flex: 1, color: c.tinta, fontSize: 16 }}>🛡️ {g.apelido}</Text>
                <Text style={{ color: c.apagado }}>{g.quadrados} {g.quadrados === 1 ? 'quadrado' : 'quadrados'}</Text>
              </View>
            ))}
          </Cartaz>
        ) : <Apagado>Ninguém guarda um quadrado ainda.</Apagado>}
      </ScrollView>
    </SafeAreaView>
  );
}

function Degraus({ ranking }: { ranking: LinhaPodio[] }) {
  const c = useCores();
  const alturas = { 1: 96, 2: 70, 3: 52 } as const;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: 8 }}>
      {([2, 1, 3] as const).map((pos) => {
        const r = ranking.find((x) => x.posicao === pos);
        return (
          <View key={pos} style={{ flex: 1, alignItems: 'center', gap: 4 }}
            accessible accessibilityLabel={r ? `${pos}º lugar: ${r.apelido}, ${r.pontos} pontos` : `${pos}º lugar vazio`}>
            {r ? (
              <>
                <Text style={{ fontSize: 26 }}>{pos === 1 ? '🥇' : pos === 2 ? '🥈' : '🥉'}</Text>
                <Text numberOfLines={1} style={{ color: c.tinta, fontWeight: '700', fontSize: 15 }}>{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text style={{ color: c.apagado, fontSize: 13 }}>{r.pontos} pts</Text>
              </>
            ) : null}
            <View style={{ alignSelf: 'stretch', height: alturas[pos], borderTopLeftRadius: 10, borderTopRightRadius: 10,
              backgroundColor: pos === 1 ? c.sol : c.suave, alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ fontFamily: FONTE_TITULO, fontSize: 26, color: pos === 1 ? c.solTinta : c.tinta }}>{pos}</Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}
