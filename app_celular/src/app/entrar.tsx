// Entrada: a marca em cima, no verde do mapa de trilha, e o formulário numa folha que sobe de baixo.
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Fichas } from '../componentes/ui';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { useSessao } from '../lib/sessao';

const APELIDO = /^[\p{L}\p{N} ._-]{2,30}$/u;
const PINHEIRO = '#0F5A40';

// A lupa da marca: um aro amarelo com o cabo, feita só de formas
function Lupa() {
  return (
    <View style={{ width: 96, height: 96, transform: [{ rotate: '-12deg' }] }} accessibilityElementsHidden>
      <View style={{ width: 70, height: 70, borderRadius: 35, borderWidth: 9, borderColor: '#FFC83D', backgroundColor: 'rgba(255,255,255,0.14)' }} />
      <View style={{ position: 'absolute', left: 58, top: 60, width: 34, height: 11, borderRadius: 6, backgroundColor: '#FFC83D', transform: [{ rotate: '45deg' }] }} />
    </View>
  );
}

export default function Entrar() {
  const c = useCores();
  const s = useSessao();
  const [modo, setModo] = useState<'entrar' | 'criar'>('entrar');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [apelido, setApelido] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const campo = { minHeight: 54, borderWidth: 1.5, borderColor: c.linha, borderRadius: 14, paddingHorizontal: 16,
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
    <View style={{ flex: 1, backgroundColor: PINHEIRO }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled" bounces={false}>
          <SafeAreaView edges={['top']} style={{ flex: 1, minHeight: 280, justifyContent: 'center', paddingHorizontal: 28, paddingVertical: 24, gap: 8 }}>
            <Lupa />
            <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 52, color: '#FFFFFF', letterSpacing: -1.5, lineHeight: 56 }}>
              WishLens
            </Text>
            <Text style={{ color: '#D6EDE2', fontSize: 19 }}>Aponte. Fotografe. Descubra.</Text>
          </SafeAreaView>

          <SafeAreaView edges={['bottom']} style={{ backgroundColor: c.superficie, borderTopLeftRadius: 30, borderTopRightRadius: 30,
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
                <Text style={{ fontFamily: FONTE_TITULO, fontSize: 22, color: c.tinta }}>Como a turma te chama?</Text>
                <Apagado>Modo de teste: sem conta, só um apelido. Os pontos ficam no servidor até ele reiniciar.</Apagado>
              </>
            )}
            {modo === 'criar' || !s.comConta ? (
              <View style={{ gap: 4 }}>
                <TextInput style={campo} placeholder="Apelido (aparece no pódio)" placeholderTextColor={c.apagado} value={apelido}
                  onChangeText={setApelido} maxLength={30} accessibilityLabel="Apelido" onSubmitEditing={enviar} returnKeyType="go" />
                <Apagado estilo={{ fontSize: 13 }}>Use um apelido, não o seu nome completo.</Apagado>
              </View>
            ) : null}
            {msg ? <Text accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
            <Botao titulo={!s.comConta ? 'Começar a jogar' : modo === 'entrar' ? 'Entrar' : 'Criar conta'} aoTocar={enviar} carregando={ocupado} />
          </SafeAreaView>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
