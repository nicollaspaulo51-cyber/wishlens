// Coleção: o álbum de figurinhas por tema. Colada = achado seu; tracejada = a turma já achou e você não.
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Aviso, Botao, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { api, type Medalha } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useSessao } from '../../lib/sessao';
import { useDados } from '../../lib/useDados';

const COR_NIVEL = { bronze: '#B87333', prata: '#9AA4AD', ouro: '#FFC83D' } as const;

export default function Colecao() {
  const c = useCores();
  const { sair } = useSessao();
  const col = useDados(api.colecao);
  const d = col.dados;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={col.carregando} onRefresh={col.recarregar} tintColor={c.destaque} />}>
        <Titulo>Minha coleção</Titulo>
        {col.erro && !d ? <Aviso texto={col.erro} aoTentar={col.recarregar} /> : null}
        {d ? (
          <>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {[[d.resumo.pontos, 'pontos'], [d.resumo.achados, 'achados diferentes'], [d.resumo.corrente, 'dias seguidos'],
                [d.resumo.fotos, 'fotos'], [`${Math.round(d.resumo.recusadas * 100)}%`, 'recusadas']].map(([valor, rotulo]) => (
                <View key={String(rotulo)} style={{ backgroundColor: c.superficie, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8, minWidth: 96 }}>
                  <Text style={{ fontFamily: FONTE_TITULO, fontSize: 22, color: c.tinta }}>{valor}</Text>
                  <Text style={{ color: c.apagado, fontSize: 12 }}>{rotulo}</Text>
                </View>
              ))}
            </View>
            {d.estilo ? (
              <Cartaz>
                <Text style={{ fontFamily: FONTE_TITULO, fontSize: 20, color: c.destaque }}>{d.estilo}</Text>
                <Apagado>Seu estilo de jogador: o grupo em que o K-Means colocou você, comparando o que você fotografa com a turma.</Apagado>
              </Cartaz>
            ) : null}

            <Subtitulo>Álbum</Subtitulo>
            {d.album.map((p) => (
              <View key={p.tema.id} style={{ gap: 8, marginBottom: 12 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={{ fontSize: 22 }} accessibilityElementsHidden>{p.tema.emoji}</Text>
                  <Text accessibilityRole="header" style={{ flex: 1, fontFamily: FONTE_TITULO, fontSize: 18, color: c.tinta }}>{p.tema.nome}</Text>
                  <Text style={{ color: c.apagado }}>{p.colados.length} de {p.total}</Text>
                  {p.medalha?.nivel ? <SeloMedalha m={p.medalha} /> : null}
                </View>
                {p.colados.length === 0 && p.faltam.length === 0 ? (
                  <Apagado>Nenhuma figurinha ainda. Procure em {p.tema.onde}.</Apagado>
                ) : (
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }} accessibilityRole="list">
                    {p.colados.map((f) => (
                      <View key={f.achado} accessibilityLabel={`${f.achado}, achado por ${f.turma} da turma`}
                        style={{ width: '31%', minHeight: 84, backgroundColor: c.figurinha, borderRadius: 6, borderWidth: 4, borderColor: '#FFFFFF',
                          padding: 6, justifyContent: 'space-between', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 3, elevation: 2,
                          ...(f.turma === 1 ? { borderColor: c.sol } : null) }}>
                        <Text style={{ color: c.tinta, fontWeight: '700', fontSize: 13 }} numberOfLines={3}>{f.achado}</Text>
                        <Text style={{ color: c.apagado, fontSize: 11 }}>{f.turma === 1 ? 'só você' : `${f.turma} na turma`}</Text>
                      </View>
                    ))}
                    {p.faltam.map((f) => (
                      <View key={f.dica + f.turma} accessibilityLabel={`Falta: começa com ${f.dica[0]}, ${f.turma} da turma já acharam`}
                        style={{ width: '31%', minHeight: 84, borderRadius: 6, borderWidth: 2, borderStyle: 'dashed', borderColor: c.linha,
                          padding: 6, justifyContent: 'space-between' }}>
                        <Text style={{ color: c.apagado, fontFamily: FONTE_TITULO, fontSize: 22 }}>{f.dica}</Text>
                        <Text style={{ color: c.apagado, fontSize: 11 }}>{f.turma} na turma</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))}
            <Subtitulo>Medalhas</Subtitulo>
            {d.medalhas.map((m) => (
              <View key={m.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 }}>
                <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: m.nivel ? COR_NIVEL[m.nivel] : c.suave }} />
                <Text style={{ flex: 1, color: c.tinta, fontSize: 15 }}>{m.nome}{m.nivel ? ` (${m.nivel})` : ''}</Text>
                <Apagado estilo={{ fontSize: 13 }}>{m.valor} {m.conta}{m.proximo ? ` · faltam ${m.proximo}` : ''}</Apagado>
              </View>
            ))}
          </>
        ) : null}
        <Botao titulo="Sair da conta" tipo="secundario" aoTocar={sair} estilo={{ marginTop: 24 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function SeloMedalha({ m }: { m: Medalha }) {
  return (
    <View style={{ backgroundColor: COR_NIVEL[m.nivel!], borderRadius: 8, paddingHorizontal: 8, paddingVertical: 2 }}>
      <Text style={{ fontSize: 12, fontWeight: '700', color: '#1A1A1A' }}>{m.nome}</Text>
    </View>
  );
}
