import { useState } from 'react';
import { Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useSessao } from '../lib/sessao';
import { useCores } from '../lib/cores';
import { Apagado, Botao, Cartaz, Subtitulo, Titulo } from './ui';

export function BotaoCriarConta() {
  const { sair, contasDisponiveis } = useSessao();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(false);

  async function criar() {
    setErro(false);
    setOcupado(true);
    try {
      await sair(true);
    } catch {
      setErro(true);
    } finally {
      setOcupado(false);
    }
  }

  return <>
    <Botao titulo="Criar conta" aoTocar={criar} desativado={!contasDisponiveis} carregando={ocupado} />
    {!contasDisponiveis ? <Apagado>Contas ainda não estão ligadas neste servidor.</Apagado> : null}
    {erro ? <Text accessibilityLiveRegion="polite" className="font-texto text-tinta">Não deu para sair. Tente de novo.</Text> : null}
  </>;
}

export function PrecisaDeConta({ podio = false, titulo }: { podio?: boolean; titulo: string }) {
  const c = useCores();
  // style e não className: as classes não chegam ao SafeAreaView (o bloco ficava colado nas bordas)
  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.fundo, padding: 16, gap: 12 }}>
      <Titulo>{titulo}</Titulo>
      <Cartaz estilo={{ gap: 12 }}>
        <Subtitulo>{podio ? 'O pódio é para quem tem conta' : 'Amigos e chat precisam de conta'}</Subtitulo>
        <Apagado>{podio ? 'Crie uma conta para entrar no pódio e participar das competições.' : 'Crie uma conta para adicionar amigos e conversar.'}</Apagado>
        <BotaoCriarConta />
      </Cartaz>
    </SafeAreaView>
  );
}
