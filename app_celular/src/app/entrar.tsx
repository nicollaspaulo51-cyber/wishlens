import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Fichas, Titulo } from '../componentes/ui';
import { useCores } from '../lib/cores';
import { useSessao } from '../lib/sessao';

const APELIDO = /^[\p{L}\p{N} ._-]{2,30}$/u;

export default function Entrar() {
  const c = useCores();
  const s = useSessao();
  const [modo, setModo] = useState<'entrar' | 'criar'>('entrar');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [apelido, setApelido] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const campo = { minHeight: 52, borderWidth: 1, borderColor: c.linha, borderRadius: 12, paddingHorizontal: 14,
    fontSize: 16, color: c.tinta, backgroundColor: c.superficie };

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
    <SafeAreaView style={{ flex: 1, backgroundColor: c.fundo }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ padding: 24, gap: 14, flexGrow: 1, justifyContent: 'center' }} keyboardShouldPersistTaps="handled">
          <Titulo tamanho={44}>WishLens</Titulo>
          <Text style={{ color: c.tinta, fontSize: 18, marginBottom: 12 }}>Aponte. Fotografe. Descubra.</Text>
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
            <Apagado>Modo de teste: sem conta, só um apelido. Os pontos ficam no servidor até ele reiniciar.</Apagado>
          )}
          {modo === 'criar' || !s.comConta ? (
            <View style={{ gap: 4 }}>
              <TextInput style={campo} placeholder="Apelido (aparece no pódio)" placeholderTextColor={c.apagado} value={apelido}
                onChangeText={setApelido} maxLength={30} accessibilityLabel="Apelido" />
              <Apagado estilo={{ fontSize: 13 }}>Use um apelido, não o seu nome completo.</Apagado>
            </View>
          ) : null}
          {msg ? <Text accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
          <Botao titulo={!s.comConta ? 'Jogar' : modo === 'entrar' ? 'Entrar' : 'Criar conta'} aoTocar={enviar} carregando={ocupado} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
