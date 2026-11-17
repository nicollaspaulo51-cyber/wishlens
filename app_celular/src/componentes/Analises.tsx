// Análises da aba Amigos: seus números e, se escolher um amigo, os dele lado a lado (quem ganha em cada um).
import { useState } from 'react';
import { Text, View } from 'react-native';

import { api, type Balde, type Estatisticas } from '../lib/api';
import { useCores } from '../lib/cores';
import { NOME_LIVRE } from '../lib/modo';
import { useDados } from '../lib/useDados';
import { Barras, Colunas, Legenda, useCoresGrafico } from './Graficos';
import { Pizza, type Fatia } from './Pizza';
import { Apagado, Aviso, Cartaz, Fichas, Subtitulo } from './ui';

const NUMEROS: { id: keyof Estatisticas['resumo']; nome: string; formato?: (v: number) => string }[] = [
  { id: 'pontos', nome: 'pontos' },
  { id: 'achados', nome: 'achados diferentes' },
  { id: 'fotos', nome: 'fotos' },
  { id: 'aceitas', nome: 'fotos aceitas', formato: (v) => `${Math.round(v * 100)}%` },
  { id: 'dias_jogados', nome: 'dias jogados' },
  { id: 'corrente', nome: 'dias seguidos' },
  { id: 'melhor_dia', nome: 'pontos no melhor dia' },
  { id: 'km', nome: 'km entre fotos (aprox.)', formato: (v) => v.toLocaleString('pt-BR') },
];

const valores = (b: Balde[]) => b.map((x) => x.valor);

export function Analises({ amigos, visita }: { amigos: string[]; visita: number }) {
  const c = useCores();
  const cor = useCoresGrafico();
  const [com, setCom] = useState('');
  const est = useDados(() => api.estatisticas(com || null), [com]);
  const temas = useDados(api.temas);
  const eu = est.dados?.eu;
  const outro = est.dados?.amigo ?? null;
  const chave = `${visita}-${com}`;

  const nomeTema = Object.fromEntries((temas.dados?.temas ?? []).map((t) => [t.id, `${t.emoji} ${t.nome}`]));
  const nomeAba: Record<string, string> = { livre: `${NOME_LIVRE.emoji} ${NOME_LIVRE.nome}`,
    ...Object.fromEntries((temas.dados?.abas ?? []).map((a) => [a.id, `${a.emoji} ${a.nome}`])) };
  // Pizza: uma por pessoa, com os nomes dos baldes
  const pizza = (f: (e: Estatisticas) => Fatia[]) =>
    [eu, outro].filter((e): e is Estatisticas => !!e).map((e, i) => ({ nome: i ? e.apelido : 'Você', fatias: f(e) }));
  const fatias = (b: Balde[], nome: (chave: string) => string) => b.map((x) => ({ nome: nome(x.chave), valor: x.valor }));
  const series = (f: (e: Estatisticas) => Balde[]) =>
    [eu, outro].filter((e): e is Estatisticas => !!e).map((e, i) => ({ nome: i ? e.apelido : 'Você', valores: valores(f(e)) }));

  // Os achados mais fotografados não se alinham entre duas pessoas: cada um tem a sua lista
  const Top = ({ e, nome }: { e: Estatisticas; nome: string }) => (
    <View className="flex-1 gap-[6px]">
      <Text className="font-texto text-apagado text-[13px]" >{nome}</Text>
      {e.top_achados.length ? e.top_achados.map((t, i) => (
        <Text className="font-texto text-tinta text-[14px]" key={t.chave} numberOfLines={1} >{i + 1}. {t.chave} <Text className="font-texto text-apagado" >×{t.valor}</Text></Text>
      )) : <Apagado>Nada ainda.</Apagado>}
    </View>
  );

  return (
    <View className="gap-[12px]">
      <Subtitulo>Análises</Subtitulo>
      <Fichas rotulo="Comparar com" valor={com} aoEscolher={setCom}
        opcoes={[{ valor: '', texto: 'Só você' }, ...amigos.map((a) => ({ valor: a, texto: `vs ${a}` }))]} />
      {!amigos.length ? <Apagado>Adicione um amigo para comparar os seus números com os dele.</Apagado> : null}
      {est.erro && !est.dados ? <Aviso texto={est.erro} aoTentar={est.recarregar} /> : null}

      {eu ? (
        <>
          {/* Números lado a lado, com a coroa em quem ganha (em texto, não só na cor) */}
          <Legenda series={series((e) => e.por_dia)} />
          <View className="flex-row flex-wrap gap-[8px]">
            {NUMEROS.map((n) => {
              const a = eu.resumo[n.id];
              const b = outro?.resumo[n.id];
              const f = n.formato ?? ((v: number) => String(v));
              const ganha = b === undefined || a === b ? null : a > b ? 'voce' : 'amigo';
              return (
                <View key={n.id} accessible accessibilityLabel={`${n.nome}: você ${f(a)}${outro ? `, ${outro.apelido} ${f(b!)}` : ''}${ganha ? `. Ganha: ${ganha === 'voce' ? 'você' : outro!.apelido}` : ''}`}
                  style={{ width: '48%', flexGrow: 1, backgroundColor: c.superficie, borderRadius: 12, padding: 10, gap: 2,
                    borderWidth: 1, borderColor: c.linha }}>
                  <View className="flex-row items-center gap-[10px] flex-wrap">
                    {[[f(a), cor.voce, ganha === 'voce'], ...(outro ? [[f(b!), cor.amigo, ganha === 'amigo']] : [])].map(([v, tom, coroa], i) => (
                      <View key={i} className="flex-row items-center gap-[5px]">
                        <View style={{ width: 4, height: 18, borderRadius: 2, backgroundColor: tom as string }} />
                        <Text className="font-texto-forte text-tinta text-[20px]" >{coroa ? '👑 ' : ''}{v as string}</Text>
                      </View>
                    ))}
                  </View>
                  <Text className="font-texto text-apagado text-[12px]" >{n.nome}</Text>
                </View>
              );
            })}
          </View>

          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Pontos por dia (últimas 2 semanas)</Text>
            <Colunas chave={chave} prefixo="melhor dia" rotulos={eu.por_dia.map((d) => d.chave.slice(8, 10))} series={series((e) => e.por_dia)} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Pontos por tema</Text>
            <Barras chave={chave} rotulos={eu.por_tema.map((t) => nomeTema[t.chave] ?? t.chave)} series={series((e) => e.por_tema)} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Pontos divididos por tema</Text>
            <Pizza pessoas={pizza((e) => fatias(e.por_tema, (k) => nomeTema[k] ?? k))} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Pontos por aba do jogo</Text>
            <Pizza pessoas={pizza((e) => fatias(e.por_aba, (k) => nomeAba[k] ?? k))} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Fotos aceitas e recusadas</Text>
            <Pizza pessoas={pizza((e) => {
              const aceitas = Math.round(e.resumo.fotos * e.resumo.aceitas);
              return [{ nome: '✔ aceitas', valor: aceitas }, { nome: '✖ recusadas', valor: e.resumo.fotos - aceitas }];
            })} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Que horas você fotografa</Text>
            <Colunas chave={chave} prefixo="mais às" rotulos={eu.por_hora.map((h) => h.chave)} series={series((e) => e.por_hora)} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Fotos por dia da semana</Text>
            <Colunas chave={chave} prefixo="mais na" rotulos={eu.por_semana.map((d) => d.chave)} series={series((e) => e.por_semana)} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Fotos por clima</Text>
            <Pizza pessoas={pizza((e) => fatias(e.por_clima, (k) => ({ sol: '☀️ sol', nublado: '☁️ nublado', chuva: '🌧️ chuva' })[k] ?? 'sem dado'))} />
          </Cartaz>
          <Cartaz estilo={{ gap: 10 }}>
            <Text className="font-texto-forte text-tinta text-[16px]" >Achados mais fotografados</Text>
            <View className="flex-row gap-[16px]">
              <Top e={eu} nome="Você" />
              {outro ? <Top e={outro} nome={outro.apelido} /> : null}
            </View>
          </Cartaz>
          <Apagado estilo={{ fontSize: 12 }}>Só amigos aceitos podem comparar. Nada mostra onde as fotos foram tiradas.</Apagado>
        </>
      ) : null}
    </View>
  );
}
