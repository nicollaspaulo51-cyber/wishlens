// Museu: a galeria das fotos salvas e o álbum de figurinhas por tema. Colada = achado seu; tracejada = a turma já achou e você não.
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Galeria } from '../../componentes/Galeria';
import { Apagado, Aviso, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { api, type Medalha } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { Surge, useVisita } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';
import { IconeTema } from '../../componentes/icones/Icone';

export default function Colecao() {
  const c = useCores();
  const col = useDados(api.colecao);
  const d = col.dados;
  const visita = useVisita();

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-papel">
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={col.carregando} onRefresh={col.recarregar} tintColor={c.destaque} />}>
        <Titulo>Museu</Titulo>
        <Subtitulo>Sua galeria</Subtitulo>
        <Galeria visita={visita} />
        {col.erro && !d ? <Aviso texto={col.erro} aoTentar={col.recarregar} /> : null}
        {d ? (
          <>
            {/* Pontos em destaque; o resto é apoio numa linha só, sem caixas do mesmo peso */}
            <Surge chave={visita} estilo={{ gap: 4 }}>
              <Text className="font-numero text-[44px] leading-[48px] text-tinta">{d.resumo.pontos}<Text className="font-texto text-apagado text-[16px]"> pontos</Text></Text>
              <Text className="font-texto text-apagado text-[14px] leading-[20px]">
                {[[d.resumo.achados, 'achados diferentes'], [d.resumo.corrente, 'dias seguidos'], [d.resumo.fotos, 'fotos'],
                  [`${Math.round(d.resumo.recusadas * 100)}%`, 'recusadas']].map(([valor, rotulo], i) => (
                  <Text key={String(rotulo)}>{i ? '  ·  ' : ''}<Text className="font-numero text-tinta">{valor}</Text> {rotulo}</Text>
                ))}
              </Text>
            </Surge>
            {d.estilo ? (
              <Cartaz>
                <Text className="font-titulo text-[20px] text-destaque">{d.estilo}</Text>
                <Apagado>Seu estilo de jogador: o grupo em que o K-Means colocou você, comparando o que você fotografa com a turma.</Apagado>
              </Cartaz>
            ) : null}

            <Subtitulo>Figurinhas</Subtitulo>
            {d.album.map((p) => (
              <View key={p.tema.id} className="gap-[8px] mb-[12px]">
                <View className="flex-row items-center gap-[8px]">
                  <IconeTema id={p.tema.id} tamanho={24} cor={c.tinta} />
                  <Text accessibilityRole="header" className="flex-1 font-titulo text-[18px] text-tinta">{p.tema.nome}</Text>
                  <Text className="font-texto text-apagado" ><Text className="font-numero">{p.colados.length}</Text> de <Text className="font-numero">{p.total}</Text></Text>
                  {p.medalha?.nivel ? <SeloMedalha m={p.medalha} /> : null}
                </View>
                {p.colados.length === 0 && p.faltam.length === 0 ? (
                  <Apagado>Nenhuma figurinha ainda. Procure em {p.tema.onde}.</Apagado>
                ) : (
                  <View className="flex-row flex-wrap gap-[8px]" accessibilityRole="list">
                    {p.colados.map((f, i) => (
                      <Surge key={f.achado} ordem={i} chave={visita} estilo={{ width: '31%' }}>
                      <View accessibilityLabel={`${f.achado}, achado por ${f.turma} da turma`}
                        style={{ minHeight: 84, overflow: 'hidden', backgroundColor: c.superficie,
                          borderRadius: 6, borderWidth: 1, borderColor: f.turma === 1 ? c.destaque : c.linha,
                          padding: 6, justifyContent: 'space-between' }}>
                        <Text className="font-texto-forte text-tinta text-[13px]"  numberOfLines={3}>{f.achado}</Text>
                        <Text className="font-texto text-apagado text-[11px]" >{f.turma === 1 ? 'só você' : <><Text className="font-numero">{f.turma}</Text> na turma</>}</Text>
                      </View>
                      </Surge>
                    ))}
                    {p.faltam.map((f, i) => (
                      <View key={`${f.dica}-${f.turma}-${i}`} accessibilityLabel={`Falta: começa com ${f.dica[0]}, ${f.turma} da turma já acharam`}
                        style={{ width: '31%', minHeight: 84, borderRadius: 6, borderWidth: 1, borderStyle: 'dashed', borderColor: c.linha,
                          padding: 6, justifyContent: 'space-between' }}>
                        <Text className="text-apagado font-titulo text-[22px]">{f.dica}</Text>
                        <Text className="font-texto text-apagado text-[11px]" ><Text className="font-numero">{f.turma}</Text> na turma</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))}
            <Subtitulo>Medalhas</Subtitulo>
            {d.medalhas.map((m) => (
              <View key={m.id} className="flex-row items-center gap-[10px] py-[6px]">
                <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: m.nivel ? c.destaque : c.linha }} />
                <Text className="font-texto flex-1 text-tinta text-[15px]" >{m.nome}{m.nivel ? ` (${m.nivel})` : ''}</Text>
                <Apagado estilo={{ fontSize: 13 }}><Text className="font-numero">{m.valor}</Text> {m.conta}{m.proximo ? <> · faltam <Text className="font-numero">{m.proximo}</Text></> : null}</Apagado>
              </View>
            ))}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function SeloMedalha({ m }: { m: Medalha }) {
  return (
    <Text className="font-texto-forte text-apagado text-[12px]">{m.nome} ({m.nivel})</Text>
  );
}
