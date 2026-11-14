// Conta: quem você é no jogo, como pontuar e o que o app guarda sobre você.
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Cartaz, Subtitulo, Titulo } from '../../componentes/ui';
import { api } from '../../lib/api';
import { FONTE_TITULO, useCores } from '../../lib/cores';
import { useSessao } from '../../lib/sessao';
import { useDados } from '../../lib/useDados';

const REGRAS = [
  ['+10', 'toda foto aceita'],
  ['+10', 'primeira vez que você acha aquilo'],
  ['até +20', 'raridade: quem acha primeiro ganha mais'],
  ['×2', 'tudo que é do tema do dia'],
  ['+5', 'mirante: a até 40 m de um lugar do mapa (3 por dia)'],
  ['+50%', 'lupa cheia: depois de 3 temas diferentes no dia'],
  ['+15', 'cada desafio do dia'],
  ['0', 'foto repetida, de tela, borrada ou fora dos temas'],
] as const;

export default function Conta() {
  const c = useCores();
  const { sair, comConta } = useSessao();
  const estado = useDados(api.estado);
  const apelido = estado.dados?.apelido;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo }}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 32 }}>
        <Titulo>Conta</Titulo>
        <Cartaz estilo={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: c.sol, alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ fontFamily: FONTE_TITULO, fontSize: 26, color: c.solTinta }}>{(apelido ?? '?').charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontFamily: FONTE_TITULO, fontSize: 22, color: c.tinta }}>{apelido ?? '...'}</Text>
            <Apagado>{comConta ? 'É assim que a turma vê você no pódio.' : 'Modo de teste, sem conta.'}</Apagado>
          </View>
        </Cartaz>

        <Subtitulo>Como pontuar</Subtitulo>
        <Cartaz estilo={{ paddingVertical: 6 }}>
          {REGRAS.map(([valor, texto]) => (
            <View key={texto} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8 }}>
              <Text style={{ width: 68, fontFamily: FONTE_TITULO, fontSize: 17, color: c.destaque }}>{valor}</Text>
              <Text style={{ flex: 1, color: c.tinta, fontSize: 15, lineHeight: 20 }}>{texto}</Text>
            </View>
          ))}
        </Cartaz>

        <Subtitulo>Sua privacidade</Subtitulo>
        <Apagado>
          A foto vai só para o juiz dizer o que é. Da sua localização, o jogo guarda o bairro e um quadrado de ~500 m,
          nunca o ponto exato. A turma vê seu apelido, seus pontos e seus achados.
        </Apagado>

        <Botao titulo="Sair da conta" tipo="secundario" aoTocar={sair} estilo={{ marginTop: 20 }} />
      </ScrollView>
    </SafeAreaView>
  );
}
