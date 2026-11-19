import { useState } from 'react';
import { Text, View } from 'react-native';

import type { DadosGraficosPodio, LinhaPodio, Tema } from '../lib/api';
import { Barras, Colunas, Legenda, useCoresGrafico } from './Graficos';
import { Cartaz, Fichas, Subtitulo } from './ui';

export function GraficosPodio({ lideres, dados, temas, periodo, chave }: {
  lideres: LinhaPodio[]; dados?: DadosGraficosPodio; temas: Tema[]; periodo: string; chave: string;
}) {
  const [par, setPar] = useState('');
  const cores = useCoresGrafico();
  const paleta = [cores.voce, cores.amigo, cores.terceiro];
  const pares = lideres.length === 3 ? lideres.flatMap((a, i) => lideres.slice(i + 1).map((b) => ({
    valor: JSON.stringify([a.apelido, b.apelido].sort()), texto: `${a.apelido} + ${b.apelido}`, nomes: [a.apelido, b.apelido],
  }))) : [];
  const selecionado = pares.find((opcao) => opcao.valor === par);
  const pessoas = lideres.map((r, i) => ({ ...r, nome: r.apelido, cor: paleta[i] }))
    .filter((r) => !selecionado || selecionado.nomes.includes(r.apelido));
  const series = (campo: 'por_dia' | 'por_tema') => pessoas.flatMap(({ nome, cor }) => {
    const jogador = dados?.jogadores.find((j) => j.apelido === nome);
    return jogador ? [{ nome, cor, valores: jogador[campo] }] : [];
  });
  const nomeTema = new Map(temas.map((t) => [t.id, t.nome]));
  const chaveGrafico = `${chave}-${selecionado?.valor ?? 'todos'}`;

  return (
    <View className="gap-[12px]">
      <Subtitulo>Comparativo do pódio</Subtitulo>
      {pares.length ? <Fichas rotulo="Jogadores a comparar" valor={selecionado?.valor ?? ''} aoEscolher={setPar}
        opcoes={[{ valor: '', texto: 'Todos os 3' }, ...pares]} /> : null}
      <Legenda series={pessoas} />
      <Cartaz estilo={{ gap: 10 }}>
        <Text className="font-texto-forte text-tinta text-[16px]">Pontos e capturas no período</Text>
        <Barras chave={chaveGrafico} rotulos={['Pontos']} prefixo="total de"
          series={pessoas.map(({ nome, cor, pontos }) => ({ nome, cor, valores: [pontos] }))} />
        <Barras chave={chaveGrafico} rotulos={['Capturas aceitas']} prefixo="total de"
          series={pessoas.map(({ nome, cor, achados }) => ({ nome, cor, valores: [achados] }))} />
      </Cartaz>
      {dados && dados.dias.length > 1 ? (
        <Cartaz estilo={{ gap: 10 }}>
          <Text className="font-texto-forte text-tinta text-[16px]">{periodo === 'geral' ? 'Pontos por dia (últimas 2 semanas)' : 'Pontos por dia'}</Text>
          <Colunas key={chaveGrafico} chave={chaveGrafico} prefixo="mais pontos em"
            rotulos={dados.dias.map((d) => `${d.slice(8, 10)}/${d.slice(5, 7)}`)} series={series('por_dia')} />
        </Cartaz>
      ) : null}
      {dados && dados.temas.length > 1 ? (
        <Cartaz estilo={{ gap: 10 }}>
          <Text className="font-texto-forte text-tinta text-[16px]">Pontos por tema</Text>
          <Barras chave={chaveGrafico} icones={dados.temas} rotulos={dados.temas.map((t) => nomeTema.get(t) ?? t)}
            series={series('por_tema')} />
        </Cartaz>
      ) : null}
    </View>
  );
}
