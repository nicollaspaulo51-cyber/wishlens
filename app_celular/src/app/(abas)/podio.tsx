import { useState } from 'react';
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Degraus } from '../../componentes/Degraus';
import { SeletorAba } from '../../componentes/SeletorAba';
import { PrecisaDeConta } from '../../componentes/PrecisaDeConta';
import { Apagado, Aviso, Cartaz, Fichas, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { useCores } from '../../lib/cores';
import { useModo } from '../../lib/modo';
import { Surge, useVisita } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';
import { useSessao } from '../../lib/sessao';

type Periodo = 'hoje' | 'semana' | 'geral';

export default function Podio() {
  return useSessao().convidado ? <PrecisaDeConta podio titulo="Pódio" /> : <PodioDaConta />;
}

function PodioDaConta() {
  const c = useCores();
  const [periodo, setPeriodo] = useState<Periodo>('hoje');
  const [tema, setTema] = useState('todos');
  const temas = useDados(api.temas);
  const modo = useModo();
  const podio = useDados(() => api.podio(periodo, modo === 'livre' && tema !== 'todos' ? tema : null, modo), [periodo, tema, modo], 30);
  const ranking = podio.dados?.ranking ?? [];
  const eu = ranking.find((r) => r.voce);
  const visita = useVisita();

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-papel">
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={podio.carregando} onRefresh={podio.recarregar} tintColor={c.destaque} />}>
        <Titulo>Pódio</Titulo>
        <Fichas<Periodo> rotulo="Período" valor={periodo} aoEscolher={setPeriodo}
          opcoes={[{ valor: 'hoje', texto: 'Hoje' }, { valor: 'semana', texto: 'Semana' }, { valor: 'geral', texto: 'Geral' }]} />
        <SeletorAba />
        {modo === 'livre' ? (
          <Fichas rotulo="Tema" valor={tema} aoEscolher={setTema}
            opcoes={[{ valor: 'todos', texto: 'Todos' }, ...(temas.dados?.temas ?? []).map((t) => ({ valor: t.id, texto: t.nome, icone: t }))]} />
        ) : null}
        {podio.erro && !podio.dados ? <Aviso texto={podio.erro} aoTentar={podio.recarregar} /> : null}
        {podio.dados && ranking.length === 0 ? <Aviso texto="Ninguém pontuou neste período ainda. Tire a primeira foto em Jogar." /> : null}
        {ranking.length ? <Degraus ranking={ranking} chave={`${modo}-${periodo}-${tema}-${visita}`} /> : null}
        {eu ? <Text className="font-texto text-tinta text-[16px]" >Você está em <Text className="font-numero">{eu.posicao}º</Text> de <Text className="font-numero">{ranking.length}</Text>.</Text> : null}
        {ranking.length > 3 ? (
          <Cartaz estilo={{ padding: 0, overflow: 'hidden' }}>
            {ranking.slice(3).map((r, i) => (
              <Surge key={r.apelido} ordem={i + 3} chave={visita}><View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, gap: 12,
                borderBottomWidth: i < ranking.length - 4 ? 1 : 0, borderBottomColor: c.linha, backgroundColor: r.voce ? c.suave : 'transparent' }}>
                <Text className="font-numero w-[32px] text-apagado" >{r.posicao}º</Text>
                <Text className="font-texto flex-1 text-tinta text-[16px]" >{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text className="font-texto text-tinta"><Text className="font-numero">{r.pontos}</Text> pts</Text>
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
                  <View key={d.apelido} className="flex-row py-[10px]">
                    <Text className="font-texto flex-1 text-tinta text-[16px]" >{d.apelido}</Text>
                    <Text className="font-texto text-apagado" ><Text className="font-numero">{d.quadrados}</Text> {d.quadrados === 1 ? 'academia' : 'academias'}</Text>
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
              <View key={g.apelido} className="flex-row py-[10px]">
                <Text className="font-texto flex-1 text-tinta text-[16px]" >{g.apelido}</Text>
                <Text className="font-texto text-apagado" ><Text className="font-numero">{g.quadrados}</Text> {g.quadrados === 1 ? 'quadrado' : 'quadrados'}</Text>
              </View>
            ))}
          </Cartaz>
        ) : <Apagado>Ninguém guarda um quadrado ainda.</Apagado>}
        </>) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
