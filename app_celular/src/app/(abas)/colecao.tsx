// Museu: a galeria das fotos salvas e o álbum de figurinhas por tema. Colada = achado seu; tracejada = a turma já achou e você não.
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Galeria } from '../../componentes/Galeria';
import { Apagado, Aviso, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { api, type Medalha } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { Brilho, Surge, useVisita } from '../../lib/movimento';
import { useDados } from '../../lib/useDados';
import { IconeTema } from '../../componentes/icones/Icone';

const COR_NIVEL = { bronze: '#B87333', prata: '#9AA4AD', ouro: '#FFC83D' } as const;

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
            <View className="flex-row flex-wrap gap-[8px]">
              {[[d.resumo.pontos, 'pontos'], [d.resumo.achados, 'achados diferentes'], [d.resumo.corrente, 'dias seguidos'],
                [d.resumo.fotos, 'fotos'], [`${Math.round(d.resumo.recusadas * 100)}%`, 'recusadas']].map(([valor, rotulo], i) => (
                <Surge key={String(rotulo)} ordem={i} chave={visita} estilo={{ backgroundColor: c.superficie, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8, minWidth: 96 }}>
                  <Text className="font-titulo text-[22px] text-tinta">{valor}</Text>
                  <Text className="font-texto text-apagado text-[12px]" >{rotulo}</Text>
                </Surge>
              ))}
            </View>
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
                  <IconeTema id={p.tema.id} emoji={p.tema.emoji} tamanho={24} cor={p.tema.cor} />
                  <Text accessibilityRole="header" className="flex-1 font-titulo text-[18px] text-tinta">{p.tema.nome}</Text>
                  <Text className="font-texto text-apagado" >{p.colados.length} de {p.total}</Text>
                  {p.medalha?.nivel ? <SeloMedalha m={p.medalha} /> : null}
                </View>
                {p.colados.length === 0 && p.faltam.length === 0 ? (
                  <Apagado>Nenhuma figurinha ainda. Procure em {p.tema.onde}.</Apagado>
                ) : (
                  <View className="flex-row flex-wrap gap-[8px]" accessibilityRole="list">
                    {p.colados.map((f, i) => (
                      <Surge key={f.achado} ordem={i} chave={visita} estilo={{ width: '31%' }}>
                      <View accessibilityLabel={`${f.achado}, achado por ${f.turma} da turma`}
                        style={{ minHeight: 84, overflow: 'hidden', backgroundColor: c.figurinha, borderRadius: 6, borderWidth: 4, borderColor: '#FFFFFF',
                          padding: 6, justifyContent: 'space-between', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 3, elevation: 2,
                          ...(f.turma === 1 ? { borderColor: c.sol } : null) }}>
                        <Text className="font-texto-forte text-tinta text-[13px]"  numberOfLines={3}>{f.achado}</Text>
                        <Text className="font-texto text-apagado text-[11px]" >{f.turma === 1 ? 'só você' : `${f.turma} na turma`}</Text>
                        {f.turma === 1 ? <Brilho pausa={4500} atraso={i * 400} /> : null}
                      </View>
                      </Surge>
                    ))}
                    {p.faltam.map((f, i) => (
                      <View key={`${f.dica}-${f.turma}-${i}`} accessibilityLabel={`Falta: começa com ${f.dica[0]}, ${f.turma} da turma já acharam`}
                        style={{ width: '31%', minHeight: 84, borderRadius: 6, borderWidth: 2, borderStyle: 'dashed', borderColor: c.linha,
                          padding: 6, justifyContent: 'space-between' }}>
                        <Text className="text-apagado font-titulo text-[22px]">{f.dica}</Text>
                        <Text className="font-texto text-apagado text-[11px]" >{f.turma} na turma</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))}
            <Subtitulo>Medalhas</Subtitulo>
            {d.medalhas.map((m) => (
              <View key={m.id} className="flex-row items-center gap-[10px] py-[6px]">
                <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: m.nivel ? COR_NIVEL[m.nivel] : c.suave }} />
                <Text className="font-texto flex-1 text-tinta text-[15px]" >{m.nome}{m.nivel ? ` (${m.nivel})` : ''}</Text>
                <Apagado estilo={{ fontSize: 13 }}>{m.valor} {m.conta}{m.proximo ? ` · faltam ${m.proximo}` : ''}</Apagado>
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
    <View style={{ backgroundColor: COR_NIVEL[m.nivel!], borderRadius: 8, paddingHorizontal: 8, paddingVertical: 2 }}>
      <Text className="font-texto-forte" style={{ fontSize: 12, fontWeight: '700', color: '#1A1A1A' }}>{m.nome}</Text>
    </View>
  );
}
