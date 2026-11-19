// Entrada: a marca em fundo neutro e o formulário embaixo.
// No celular o formulário é uma folha que sobe de baixo; em tela larga, tudo vira uma coluna centralizada.
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Pressable, ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icone } from '../componentes/icones/Icone';
import { Apagado, Botao } from '../componentes/ui';
import { FONTE_TITULO, useCores } from '../lib/cores';
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
  const rota = useLocalSearchParams<{ modo?: string }>();
  const [modo, setModo] = useState<'entrar' | 'criar' | 'convidado' | null>(
    (rota.modo === 'criar' || s.criarAoSair) && s.contasDisponiveis ? 'criar' : null,
  );
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirma, setConfirma] = useState('');
  const [verSenha, setVerSenha] = useState(false);
  const [apelido, setApelido] = useState('');
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (s.criarAoSair) router.setParams({ modo: 'criar' });
  }, [s.criarAoSair]);

  const campo = { minHeight: 54, borderWidth: 1, borderColor: c.linha, borderRadius: 6, paddingHorizontal: 16,
    fontSize: 16, color: c.tinta, backgroundColor: c.fundo };

  async function enviar() {
    if (!modo || ocupado || (modo !== 'convidado' && !s.contasDisponiveis)) return;
    setMsg(null);
    if (modo !== 'entrar' && !APELIDO.test(apelido.trim())) {
      setMsg({ texto: 'O apelido precisa ter de 2 a 30 letras ou números.', erro: true });
      return;
    }
    if (modo === 'criar' && senha.length < 6) {
      setMsg({ texto: 'A senha precisa ter pelo menos 6 caracteres.', erro: true });
      return;
    }
    if (modo === 'criar' && senha !== confirma) {
      setMsg({ texto: 'As duas senhas não são iguais.', erro: true });
      return;
    }
    setOcupado(true);
    try {
      if (modo === 'convidado') await s.entrarComoConvidado(apelido);
      else if (modo === 'entrar') await s.entrar(email, senha);
      else {
        setMsg({ texto: await s.cadastrar(email, senha, apelido), erro: false });
        setConfirma('');
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
      <KeyboardAvoidingView className="flex-1" behavior="padding">
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: larga ? 'center' : 'flex-start', paddingVertical: larga ? 32 : 0 }}
          keyboardShouldPersistTaps="handled" bounces={false}>
          <View style={{ flexGrow: larga ? 0 : 1, width: '100%', maxWidth: 460, alignSelf: 'center' }}>
          <SafeAreaView edges={['top']} style={{ flexGrow: 1, minHeight: 320, justifyContent: 'center', alignItems: 'center',
            paddingHorizontal: 28, paddingVertical: 32, gap: 6 }}>
            <Lupa />
              <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 52, color: c.tinta, letterSpacing: -1.5,
                lineHeight: 56, textAlign: 'center' }}>
                WishLens
              </Text>
            <Text className="font-texto" style={{ color: c.apagado, fontSize: 18, textAlign: 'center' }}>Fotografe um achado para marcar pontos.</Text>
          </SafeAreaView>

          <SafeAreaView edges={larga ? [] : ['bottom']} style={{ backgroundColor: c.superficie, borderTopLeftRadius: 6, borderTopRightRadius: 6, borderWidth: 1, borderColor: c.linha,
            ...(larga ? { borderRadius: 6, marginHorizontal: 16 } : null),
            paddingHorizontal: 24, paddingTop: 26, paddingBottom: 24, gap: 14 }}>
            {!modo ? (
              <>
                <Botao titulo="Criar conta" aoTocar={() => setModo('criar')} desativado={!s.contasDisponiveis} />
                <Botao titulo="Entrar" tipo="secundario" aoTocar={() => setModo('entrar')} desativado={!s.contasDisponiveis} />
                <Pressable accessibilityRole="link" onPress={() => setModo('convidado')} className="min-h-[44px] items-center justify-center">
                  <Text className="font-texto-forte text-destaque underline">Continuar sem conta</Text>
                </Pressable>
                {!s.contasDisponiveis ? <Apagado>Contas ainda não estão ligadas neste servidor.</Apagado> : null}
              </>
            ) : (
              <>
                <Text accessibilityRole="header" className="font-titulo text-[24px] text-tinta">
                  {modo === 'convidado' ? 'Continuar sem conta' : modo === 'criar' ? 'Criar conta' : 'Entrar'}
                </Text>
                {modo === 'convidado' ? <Apagado>Sem conta você joga e vê seus pontos, mas não entra no pódio, nas competições nem adiciona amigos. Seus pontos ficam só até o servidor reiniciar.</Apagado> : null}
                {modo !== 'entrar' ? (
                  <View className="gap-[4px]">
                    <TextInput style={campo} placeholder="Seu apelido" placeholderTextColor={c.apagado} value={apelido}
                      onChangeText={setApelido} maxLength={30} accessibilityLabel="Apelido"
                      onSubmitEditing={modo === 'convidado' ? enviar : undefined} returnKeyType={modo === 'convidado' ? 'go' : 'done'} />
                    <Apagado estilo={{ fontSize: 13 }}>
                      {modo === 'criar' ? 'Ele aparece no pódio. ' : ''}Use um apelido, não o seu nome completo.
                    </Apagado>
                  </View>
                ) : null}
                {modo !== 'convidado' ? (
                  <>
                    <TextInput style={campo} placeholder="E-mail" placeholderTextColor={c.apagado} value={email} onChangeText={setEmail}
                      autoCapitalize="none" autoComplete="email" keyboardType="email-address" textContentType="emailAddress" accessibilityLabel="E-mail" />
                    <View>
                      <TextInput style={[campo, { paddingRight: 96 }]} placeholder="Senha" placeholderTextColor={c.apagado} value={senha}
                        onChangeText={setSenha} secureTextEntry={!verSenha} autoCapitalize="none" autoCorrect={false}
                        autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'} accessibilityLabel="Senha"
                        onSubmitEditing={modo === 'entrar' ? enviar : undefined} returnKeyType={modo === 'entrar' ? 'go' : 'next'} />
                      <Pressable accessibilityRole="button" accessibilityLabel={verSenha ? 'Ocultar a senha' : 'Mostrar a senha'}
                        onPress={() => setVerSenha((v) => !v)} hitSlop={8}
                        style={{ position: 'absolute', right: 0, top: 0, bottom: 0, minWidth: 88, alignItems: 'center', justifyContent: 'center' }}>
                        <Text className="font-texto-forte text-destaque text-[15px]">{verSenha ? 'Ocultar' : 'Mostrar'}</Text>
                      </Pressable>
                    </View>
                    {modo === 'criar' ? (
                      <TextInput style={campo} placeholder="Confirme a senha" placeholderTextColor={c.apagado} value={confirma}
                        onChangeText={setConfirma} secureTextEntry={!verSenha} autoCapitalize="none" autoCorrect={false}
                        autoComplete="new-password" accessibilityLabel="Confirme a senha" onSubmitEditing={enviar} returnKeyType="go" />
                    ) : null}
                  </>
                ) : null}
                {msg ? <Text className="font-texto" accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text> : null}
                <Botao titulo={modo === 'convidado' ? 'Começar a jogar' : modo === 'entrar' ? 'Entrar' : 'Criar conta'} aoTocar={enviar} carregando={ocupado} />
                <Botao titulo="Voltar" tipo="secundario" desativado={ocupado} aoTocar={() => { setMsg(null); setSenha(''); setConfirma(''); setModo(null); }} />
              </>
            )}
          </SafeAreaView>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
