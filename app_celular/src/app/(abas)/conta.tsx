// Conta: quem você é no jogo, como pontuar e o que o app guarda sobre você.
import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { BotaoCriarConta } from '../../componentes/PrecisaDeConta';
import { api } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useSessao } from '../../lib/sessao';
import { useDados } from '../../lib/useDados';

const REGRAS = [
  ['+10', 'toda foto aceita'],
  ['+10', 'primeira vez que você acha aquilo'],
  ['+20', 'raridade: até 20 para quem acha primeiro, menos para os seguintes'],
  ['×2', 'tudo que é do tema do dia'],
  ['+5', 'mirante: a até 40 m de um lugar do mapa (3 por dia)'],
  ['+50%', 'lupa cheia: depois de 3 temas diferentes no dia'],
  ['+15', 'cada desafio do dia'],
  ['0', 'foto repetida, de tela, borrada ou fora dos temas'],
] as const;

export default function Conta() {
  const c = useCores();
  const { sair, convidado } = useSessao();
  const [erroSaida, setErroSaida] = useState(false);
  const estado = useDados(api.estado);
  const apelido = estado.dados?.apelido;

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-papel">
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}>
        <Titulo>Conta</Titulo>
        <Cartaz estilo={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <View className="w-[56px] h-[56px] rounded-full bg-suave items-center justify-center">
            <Text className="font-titulo text-[26px] text-tinta">{(apelido ?? '?').charAt(0).toUpperCase()}</Text>
          </View>
          <View className="flex-1">
            <Text className="font-titulo text-[22px] text-tinta">{convidado ? 'Convidado: ' : ''}{apelido ?? '...'}</Text>
            <Apagado>{convidado ? 'Seus pontos ficam só até o servidor reiniciar.' : 'É assim que a turma vê você no pódio.'}</Apagado>
          </View>
        </Cartaz>
        {convidado ? <BotaoCriarConta /> : null}

        <Subtitulo>Como pontuar</Subtitulo>
        <Cartaz estilo={{ paddingVertical: 6 }}>
          {REGRAS.map(([valor, texto]) => (
            <View key={texto} className="flex-row items-center gap-[12px] py-[8px]">
              <Text className="w-[68px] font-numero text-[17px] text-destaque">{valor}</Text>
              <Text className="font-texto flex-1 text-tinta text-[15px] leading-[20px]" >{texto}</Text>
            </View>
          ))}
        </Cartaz>

        <Subtitulo>Sua privacidade</Subtitulo>
        <Apagado>
          A foto vai só para o juiz dizer o que é. Da sua localização, o jogo guarda o bairro e um quadrado de ~500 m,
          nunca o ponto exato. A turma vê seu apelido, seus pontos e seus achados.
        </Apagado>

        <Subtitulo>Achou um problema?</Subtitulo>
        <Apagado>O juiz errou, o app travou ou algo ficou estranho? Mande um aviso: ele é lido e corrigido.</Apagado>
        <Botao titulo="Avisar um problema" aoTocar={() => router.push('/avisar')} />

        <Botao titulo={convidado ? 'Sair' : 'Sair da conta'} tipo="secundario"
          aoTocar={() => { setErroSaida(false); sair().catch(() => setErroSaida(true)); }} estilo={{ marginTop: 20 }} />
        {erroSaida ? <Text accessibilityLiveRegion="polite" className="font-texto text-tinta">Não deu para sair. Tente de novo.</Text> : null}
      </ScrollView>
    </SafeAreaView>
  );
}
