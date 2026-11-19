import { Ionicons } from '@expo/vector-icons';
import { useState, type ReactNode } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { DadosGraficosPodio, LinhaPodio, Tema } from '../lib/api';
import { useCores } from '../lib/cores';
import { useDados } from '../lib/useDados';
import { Barras, Colunas, Legenda, useCoresGrafico } from './Graficos';
import { Apagado, Aviso, Cartaz, ModalTema, Subtitulo } from './ui';

type Pessoa = LinhaPodio & { nome: string; cor: string };
type BuscarDados = (nomes: string[]) => Promise<DadosGraficosPodio | undefined>;

export function GraficosPodio({ ranking, dados, buscarDados, temas, periodo, chave }: {
  ranking: LinhaPodio[]; dados?: DadosGraficosPodio; buscarDados: BuscarDados; temas: Tema[]; periodo: string; chave: string;
}) {
  const [escolhas, setEscolhas] = useState<(string | null)[] | null>(null);
  const [aberto, setAberto] = useState<number | null>(null);
  const cores = useCoresGrafico();
  const paleta = [cores.voce, cores.amigo, cores.terceiro];
  const porApelido = new Map(ranking.map((r) => [r.apelido, r]));
  const nomes = escolhas ?? paleta.map((_, i) => ranking[i]?.apelido ?? null);
  const validos = nomes.map((nome) => nome && porApelido.has(nome) ? nome : null);
  const livres = ranking.map((r) => r.apelido).filter((nome) => !validos.includes(nome));
  const slots = validos.map((nome, i) => nome ?? (i < 2 || nomes[i] !== null ? livres.shift() ?? null : null));
  const pessoas = slots.flatMap((nome, i) => {
    const jogador = nome ? porApelido.get(nome) : undefined;
    return jogador ? [{ ...jogador, nome: jogador.apelido, cor: paleta[i]! }] : [];
  });
  const chaveSelecao = JSON.stringify(slots);
  const chaveGrafico = `${chave}-${chaveSelecao}`;
  const dadosLocais = dados && pessoas.every((p) => dados.jogadores.some((j) => j.apelido === p.apelido)) ? dados : null;

  function escolher(nome: string | null) {
    setEscolhas(slots.map((anterior, i) => i === aberto ? nome : anterior));
    setAberto(null);
  }

  return (
    <View className="gap-[12px]">
      <Subtitulo>Comparativo do pódio</Subtitulo>
      <View className="flex-row gap-[8px]">
        {slots.map((nome, i) => {
          const desativado = ranking.length < (i === 2 ? 3 : 2);
          return (
            <Pressable key={i} accessibilityRole="button" accessibilityLabel={`Jogador ${i + 1}: ${nome ?? 'Selecionar'}`}
              accessibilityState={{ disabled: desativado, expanded: aberto === i }} disabled={desativado} onPress={() => setAberto(i)}
              className="bg-ficha border rounded-ficha flex-1 min-w-0 min-h-[52px] justify-center px-2 py-1 active:opacity-80"
              style={{ borderColor: paleta[i], opacity: desativado && !nome ? 0.55 : 1 }}>
              <View className="flex-row items-center justify-between gap-1">
                <Text className="font-numero text-apagado text-[11px]">{i + 1}</Text>
                {desativado ? null : <Ionicons name="chevron-down" color={paleta[i]} size={14} />}
              </View>
              <Text className="font-texto-forte text-tinta text-[13px]" numberOfLines={1}>{nome ?? 'Selecionar'}</Text>
            </Pressable>
          );
        })}
      </View>
      <Legenda series={pessoas} />
      <CartaoGrafico titulo="Pontos e capturas no período">
        <Barras chave={chaveGrafico} rotulos={['Pontos']} prefixo="total de"
          series={pessoas.map(({ nome, cor, pontos }) => ({ nome, cor, valores: [pontos] }))} />
        <Barras chave={chaveGrafico} rotulos={['Capturas aceitas']} prefixo="total de"
          series={pessoas.map(({ nome, cor, achados }) => ({ nome, cor, valores: [achados] }))} />
      </CartaoGrafico>
      {dadosLocais ? <DetalhesPodio dados={dadosLocais} pessoas={pessoas} temas={temas} periodo={periodo} chave={chaveGrafico} /> :
        <BuscarDetalhes key={chaveSelecao} buscarDados={buscarDados} pessoas={pessoas} temas={temas} periodo={periodo} chave={chaveGrafico} />}
      {aberto !== null ? <SeletorDeJogador indice={aberto} atual={slots[aberto] ?? null}
        opcoes={ranking.filter((r) => !slots.some((nome, i) => i !== aberto && nome === r.apelido))}
        fechar={() => setAberto(null)} escolher={escolher} /> : null}
    </View>
  );
}

function SeletorDeJogador({ indice, atual, opcoes, fechar, escolher }: {
  indice: number; atual: string | null; opcoes: LinhaPodio[]; fechar: () => void; escolher: (nome: string | null) => void;
}) {
  const c = useCores();
  const baixo = useSafeAreaInsets().bottom;
  return (
    <ModalTema visible transparent animationType="slide" onRequestClose={fechar}>
      <Pressable accessibilityRole="button" accessibilityLabel="Fechar seleção" onPress={fechar} style={{ flex: 1, backgroundColor: '#0008' }} />
      <View accessibilityViewIsModal className="bg-papel rounded-t-ficha" style={{ height: '65%', paddingBottom: baixo + 12 }}>
        <Text accessibilityRole="header" className="font-titulo text-[22px] text-tinta px-4 py-3">Escolher jogador {indice + 1}</Text>
        <FlatList data={indice === 2 ? [null, ...opcoes] : opcoes}
          keyExtractor={(jogador) => jogador ? `j:${jogador.apelido}` : 'sem'} contentContainerStyle={{ paddingHorizontal: 16, gap: 6 }}
          renderItem={({ item }) => {
            const nome = item?.apelido ?? null;
            return (
              <Pressable accessibilityRole="radio" accessibilityState={{ selected: nome === atual }} onPress={() => escolher(nome)}
                className="min-h-[44px] flex-row items-center gap-[8px] rounded-ficha border border-linha px-3 py-2 active:opacity-80"
                style={{ backgroundColor: nome === atual ? c.suave : c.superficie }}>
                {item ? <Text className="font-numero text-apagado text-[13px]">{item.posicao}º</Text> : null}
                <Text className="font-texto text-tinta flex-1 text-[15px]">{nome ?? 'Sem terceiro jogador'}</Text>
                {nome === atual ? <Text className="font-texto-forte text-destaque text-[13px]">Atual</Text> : null}
              </Pressable>
            );
          }} />
      </View>
    </ModalTema>
  );
}

function BuscarDetalhes({ buscarDados, ...props }: {
  buscarDados: BuscarDados; pessoas: Pessoa[]; temas: Tema[]; periodo: string; chave: string;
}) {
  const consulta = useDados(async () => {
    const nomes = props.pessoas.map((p) => p.apelido);
    const dados = await buscarDados(nomes);
    if (!dados || !nomes.every((nome) => dados.jogadores.some((j) => j.apelido === nome))) {
      throw new Error('Os detalhes dessa comparação ainda não estão disponíveis.');
    }
    return dados;
  }, [], 30);
  if (consulta.dados) return <DetalhesPodio {...props} dados={consulta.dados} />;
  if (consulta.erro) return <Aviso texto={consulta.erro} aoTentar={consulta.recarregar} />;
  return <Apagado>Carregando gráficos…</Apagado>;
}

function CartaoGrafico({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Cartaz estilo={{ gap: 10 }}>
      <Text className="font-texto-forte text-tinta text-[16px]">{titulo}</Text>
      {children}
    </Cartaz>
  );
}

function DetalhesPodio({ dados, pessoas, temas, periodo, chave }: {
  dados: DadosGraficosPodio; pessoas: Pessoa[]; temas: Tema[]; periodo: string; chave: string;
}) {
  const jogadores = new Map(dados.jogadores.map((j) => [j.apelido, j]));
  const porPessoa = pessoas.map((p) => ({ ...p, dados: jogadores.get(p.apelido)! }));
  const nomeTema = new Map(temas.map((t) => [t.id, t.nome]));
  const dias = dados.dias.map((d) => `${d.slice(8, 10)}/${d.slice(5, 7)}`);
  const rotulosTema = dados.temas.map((t) => nomeTema.get(t) ?? t);
  const serie = (campo: 'por_dia' | 'por_tema' | 'capturas_por_dia' | 'capturas_por_tema') =>
    porPessoa.map(({ nome, cor, dados: d }) => ({ nome, cor, valores: d[campo] ?? [] }));
  const novosAgregados = porPessoa.every(({ dados: d }) =>
    d.pontos_jogo !== undefined && d.bonus !== undefined && d.capturas_por_dia && d.capturas_por_tema);
  const sufixo = periodo === 'geral' ? ' (últimas 2 semanas)' : '';

  return (
    <>
      {novosAgregados ? (
        <CartaoGrafico titulo="De onde vêm os pontos">
          <Barras chave={chave} rotulos={['Pontos de jogo', 'Bônus extras']}
            series={porPessoa.map(({ nome, cor, dados: d }) => ({ nome, cor, valores: [d.pontos_jogo ?? 0, d.bonus ?? 0] }))} />
        </CartaoGrafico>
      ) : null}
      {dias.length > 1 ? (
        <>
          <CartaoGrafico titulo={`Pontos por dia${sufixo}`}>
            <Colunas key={`pontos-${chave}`} chave={chave} prefixo="mais pontos em" rotulos={dias} series={serie('por_dia')} />
          </CartaoGrafico>
          {novosAgregados ? <CartaoGrafico titulo={`Capturas aceitas por dia${sufixo}`}>
            <Colunas key={`capturas-${chave}`} chave={chave} prefixo="mais capturas em" rotulos={dias} series={serie('capturas_por_dia')} />
          </CartaoGrafico> : null}
        </>
      ) : null}
      {rotulosTema.length > 1 ? (
        <>
          <CartaoGrafico titulo="Pontos por tema">
            <Barras chave={chave} icones={dados.temas} rotulos={rotulosTema} series={serie('por_tema')} />
          </CartaoGrafico>
          {novosAgregados ? <CartaoGrafico titulo="Capturas aceitas por tema">
            <Barras chave={chave} icones={dados.temas} rotulos={rotulosTema} series={serie('capturas_por_tema')} />
          </CartaoGrafico> : null}
        </>
      ) : null}
    </>
  );
}
