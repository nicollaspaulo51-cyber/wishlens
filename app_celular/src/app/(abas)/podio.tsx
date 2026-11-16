import { useState, type ReactNode } from 'react';
import { Animated, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Cartaz, Fichas, Subtitulo, Titulo } from '../../componentes/ui';
import { api, type LinhaPodio, type Modo } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { escolherModo, NOME_LIVRE, useModo } from '../../lib/modo';
import { Brilho, Surge, useEntrada } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';

type Periodo = 'hoje' | 'semana' | 'geral';

export default function Podio() {
  const c = useCores();
  const [periodo, setPeriodo] = useState<Periodo>('hoje');
  const [tema, setTema] = useState('todos');
  const temas = useDados(api.temas);
  const modo = useModo();
  const podio = useDados(() => api.podio(periodo, modo === 'livre' && tema !== 'todos' ? tema : null, modo), [periodo, tema, modo], 30);
  const ranking = podio.dados?.ranking ?? [];
  const eu = ranking.find((r) => r.voce);

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={podio.carregando} onRefresh={podio.recarregar} tintColor={c.destaque} />}>
        <Titulo>Pódio</Titulo>
        <Fichas<Periodo> rotulo="Período" valor={periodo} aoEscolher={setPeriodo}
          opcoes={[{ valor: 'hoje', texto: 'Hoje' }, { valor: 'semana', texto: 'Semana' }, { valor: 'geral', texto: 'Geral' }]} />
        <Fichas<Modo> rotulo="Aba do jogo" valor={modo} aoEscolher={escolherModo}
          opcoes={[NOME_LIVRE, ...(temas.dados?.abas ?? [])].map((a) => ({ valor: a.id as Modo, texto: `${a.emoji} ${a.nome}` }))} />
        {modo === 'livre' ? (
          <Fichas rotulo="Tema" valor={tema} aoEscolher={setTema}
            opcoes={[{ valor: 'todos', texto: 'Todos' }, ...(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: `${t.emoji} ${t.nome}` }))]} />
        ) : null}
        {podio.erro && !podio.dados ? <Aviso texto={podio.erro} aoTentar={podio.recarregar} /> : null}
        {podio.dados && ranking.length === 0 ? <Aviso texto="Ninguém pontuou neste período ainda. Tire a primeira foto em Jogar." /> : null}
        {ranking.length ? <Degraus ranking={ranking} chave={`${modo}-${periodo}-${tema}`} /> : null}
        {eu ? <Text style={{ color: c.tinta, fontSize: 16 }}>Você está em <Text style={{ fontWeight: '700' }}>{eu.posicao}º</Text> de {ranking.length}.</Text> : null}
        {ranking.length > 3 ? (
          <Cartaz estilo={{ paddingVertical: 4 }}>
            {ranking.slice(3).map((r, i) => (
              <Surge key={r.apelido} ordem={i + 3}><View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 10, gap: 12,
                borderBottomWidth: 1, borderBottomColor: c.linha, backgroundColor: r.voce ? c.suave : 'transparent' }}>
                <Text style={{ width: 32, color: c.apagado, fontWeight: '700' }}>{r.posicao}º</Text>
                <Text style={{ flex: 1, color: c.tinta, fontSize: 16 }}>{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text style={{ color: c.tinta, fontWeight: '700' }}>{r.pontos} pts</Text>
              </View></Surge>
            ))}
          </Cartaz>
        ) : null}

        {modo === 'academia' ? (
          <>
            <Subtitulo>Donos das academias</Subtitulo>
            <Apagado>Quem tem mais aparelhos diferentes numa academia na semana é o dono dela: +5 por dia e +10 a cada 3 dias seguidos. Só contam academias onde 2 pessoas ou mais jogaram.</Apagado>
            {podio.dados?.donos?.length ? (
              <Cartaz estilo={{ paddingVertical: 4 }}>
                {podio.dados.donos.map((d) => (
                  <View key={d.apelido} style={{ flexDirection: 'row', paddingVertical: 10 }}>
                    <Text style={{ flex: 1, color: c.tinta, fontSize: 16 }}>🏋️ {d.apelido}</Text>
                    <Text style={{ color: c.apagado }}>{d.quadrados} {d.quadrados === 1 ? 'academia' : 'academias'}</Text>
                  </View>
                ))}
              </Cartaz>
            ) : <Apagado>Nenhuma academia tem dono ainda.</Apagado>}
          </>
        ) : null}
        {modo === 'livre' ? (<>
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
        </>) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function Degraus({ ranking, chave }: { ranking: LinhaPodio[]; chave: string }) {
  const c = useCores();
  const alturas = { 1: 96, 2: 70, 3: 52 } as const;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: 8 }}>
      {([2, 1, 3] as const).map((pos) => {
        const r = ranking.find((x) => x.posicao === pos);
        return (
          <Degrau key={pos} pos={pos} chave={chave} altura={alturas[pos]}
            rotulo={r ? `${pos}º lugar: ${r.apelido}, ${r.pontos} pontos` : `${pos}º lugar vazio`}>
            {r ? (
              <>
                <Text style={{ fontSize: 26 }}>{pos === 1 ? '🥇' : pos === 2 ? '🥈' : '🥉'}</Text>
                <Text numberOfLines={1} style={{ color: c.tinta, fontWeight: '700', fontSize: 15 }}>{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text style={{ color: c.apagado, fontSize: 13 }}>{r.pontos} pts</Text>
              </>
            ) : null}
          </Degrau>
        );
      })}
    </View>
  );
}

// Um degrau sobe do chão (o 3º primeiro, o 1º por último) e a medalha cai em cima dele
function Degrau({ pos, chave, altura, rotulo, children }: { pos: 1 | 2 | 3; chave: string; altura: number; rotulo: string; children: ReactNode }) {
  const c = useCores();
  const sobe = useEntrada({ 3: 0, 2: 150, 1: 300 }[pos], chave);
  const cai = useEntrada({ 3: 250, 2: 400, 1: 550 }[pos], chave);
  return (
    <View style={{ flex: 1, alignItems: 'center', gap: 4 }} accessible accessibilityLabel={rotulo}>
      <Animated.View style={{ alignItems: 'center', gap: 4, opacity: cai,
        transform: [{ translateY: cai.interpolate({ inputRange: [0, 1], outputRange: [-24, 0] }) }] }}>
        {children}
      </Animated.View>
      <Animated.View style={{ alignSelf: 'stretch', height: altura, borderTopLeftRadius: 10, borderTopRightRadius: 10,
        backgroundColor: pos === 1 ? c.sol : c.suave, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        transformOrigin: 'bottom', transform: [{ scaleY: sobe }] }}>
        <Text style={{ fontFamily: FONTE_TITULO, fontSize: 26, color: pos === 1 ? c.solTinta : c.tinta }}>{pos}</Text>
        {pos === 1 ? <Brilho pausa={4000} /> : null}
      </Animated.View>
    </View>
  );
}
