// Entrada: a marca em fundo neutro e o formulário embaixo.
// No celular o formulário é uma folha que sobe de baixo; em tela larga, tudo vira uma coluna centralizada.
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icone } from '../componentes/icones/Icone';
import { Apagado, Botao, Fichas } from '../componentes/ui';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { Surge } from '../lib/movimento';
import { useSessao } from '../lib/sessao';

const APELIDO = /^[\p{L}\p{N} ._-]{2,30}$/u;

function Lupa() {
  const c = useCores();
  return <View accessibilityElementsHidden><Icone nome="lupa" tamanho={96} cor={c.destaque} /></View>;
}

export default function Entrar() {
  const c = useCores();
  const { width } = useWindowDimensions();
  const larga = width >= 640;
  const s = useSessao();
  const [modo, setModo] = useState<'entrar' | 'criar'>('entrar');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [apelido, setApelido] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const campo = { minHeight: 54, borderWidth: 1, borderColor: c.linha, borderRadius: 6, paddingHorizontal: 16,
    fontSize: 16, color: c.tinta, backgroundColor: c.fundo };

  async function enviar() {
    setMsg(null);
    if ((modo === 'criar' || !s.comConta) && !APELIDO.test(apelido.trim())) {
      setMsg({ texto: 'O apelido precisa ter de 2 a 30 letras ou números.', erro: true });
      return;
    }
    setOcupado(true);
    try {
      if (!s.comConta) await s.entrarComApelido(apelido);
      else if (modo === 'entrar') await s.entrar(email, senha);
      else {
        setMsg({ texto: await s.cadastrar(email, senha, apelido), erro: false });
        setModo('entrar');
      }
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não deu certo. Tente de novo.', erro: true });
    } finally {
      setOcupado(false);
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: c.fundo }}>
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: larga ? 'center' : 'flex-start', paddingVertical: larga ? 32 : 0 }}
          keyboardShouldPersistTaps="handled" bounces={false}>
          <View style={{ flexGrow: larga ? 0 : 1, width: '100%', maxWidth: 460, alignSelf: 'center' }}>
          <SafeAreaView edges={['top']} style={{ flexGrow: 1, minHeight: 320, justifyContent: 'center', alignItems: 'center',
            paddingHorizontal: 28, paddingVertical: 32, gap: 6 }}>
            <Surge><Lupa /></Surge>
            <Surge ordem={2}>
              <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 52, color: c.tinta, letterSpacing: -1.5,
                lineHeight: 56, textAlign: 'center' }}>
                WishLens
              </Text>
            </Surge>
            <Surge ordem={4}><Text className="font-texto" style={{ color: c.apagado, fontSize: 18, textAlign: 'center' }}>Fotografe um achado para marcar pontos.</Text></Surge>
          </SafeAreaView>

          <SafeAreaView edges={larga ? [] : ['bottom']} style={{ backgroundColor: c.superficie, borderTopLeftRadius: 6, borderTopRightRadius: 6, borderWidth: 1, borderColor: c.linha,
            ...(larga ? { borderRadius: 6, marginHorizontal: 16 } : null),
            paddingHorizontal: 24, paddingTop: 26, paddingBottom: 24, gap: 14 }}>
            {s.comConta ? (
              <>
                <Fichas rotulo="Entrar ou criar conta" valor={modo} aoEscolher={setModo}
                  opcoes={[{ valor: 'entrar', texto: 'Entrar' }, { valor: 'criar', texto: 'Criar conta' }]} />
                <TextInput style={campo} placeholder="E-mail" placeholderTextColor={c.apagado} value={email} onChangeText={setEmail}
                  autoCapitalize="none" autoComplete="email" keyboardType="email-address" textContentType="emailAddress" accessibilityLabel="E-mail" />
                <TextInput style={campo} placeholder="Senha" placeholderTextColor={c.apagado} value={senha} onChangeText={setSenha}
                  secureTextEntry autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'} accessibilityLabel="Senha" />
              </>
            ) : (
              <>
                <Text className="font-titulo text-[24px] text-tinta">Como quer ser chamado?</Text>
                <Apagado>Sem cadastro: escolha um apelido e comece a fotografar.</Apagado>
              </>
            )}
            {modo === 'criar' || !s.comConta ? (
              <View className="gap-[4px]">
                <TextInput style={campo} placeholder="Seu apelido" placeholderTextColor={c.apagado} value={apelido}
                  onChangeText={setApelido} maxLength={30} accessibilityLabel="Apelido" onSubmitEditing={enviar} returnKeyType="go" />
                <Apagado estilo={{ fontSize: 13 }}>Ele aparece no pódio. Use um apelido, não o seu nome completo.</Apagado>
              </View>
            ) : null}
            {msg ? <Text className="font-texto" accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
            <Botao titulo={!s.comConta ? 'Começar a jogar' : modo === 'entrar' ? 'Entrar' : 'Criar conta'} aoTocar={enviar} carregando={ocupado} />
          </SafeAreaView>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
