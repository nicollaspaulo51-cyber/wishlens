// Entrada: a marca no verde do mapa de trilha, com os temas do jogo em volta, e o formulário embaixo.
// No celular o formulário é uma folha que sobe de baixo; em tela larga, tudo vira uma coluna centralizada.
import { useState } from 'react';
import { Animated, KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Topografia } from '../componentes/efeitos/Topografia';
import { Icone, type NomeIcone } from '../componentes/icones/Icone';
import { Apagado, Botao, Fichas } from '../componentes/ui';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { Surge, useLaco } from '../lib/movimento';
import { useSessao } from '../lib/sessao';

const APELIDO = /^[\p{L}\p{N} ._-]{2,30}$/u;
const PINHEIRO = '#0F5A40';

// A lupa da marca: um aro amarelo com o cabo, feita só de formas
function Lupa() {
  const { v } = useLaco(2600);
  const giro = v.interpolate({ inputRange: [0, 0.5, 1], outputRange: ['-12deg', '6deg', '-12deg'] });
  const anda = v.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0, 14, 0] });
  return (
    <Animated.View style={{ width: 96, height: 96, transform: [{ translateX: anda }, { rotate: giro }] }} accessibilityElementsHidden>
      <View style={{ width: 70, height: 70, borderRadius: 35, borderWidth: 9, borderColor: '#FFC83D', backgroundColor: 'rgba(255,255,255,0.14)' }} />
      <View style={{ position: 'absolute', left: 58, top: 60, width: 34, height: 11, borderRadius: 6, backgroundColor: '#FFC83D', transform: [{ rotate: '45deg' }] }} />
    </Animated.View>
  );
}

// Os temas do jogo flutuando em volta da marca, como alfinetes num mapa
const ALFINETES = [
  { id: 'carros', x: '8%', y: '14%' }, { id: 'plantas', x: '82%', y: '10%' }, { id: 'passaros', x: '88%', y: '58%' },
  { id: 'pets', x: '4%', y: '66%' }, { id: 'pecas', x: '70%', y: '82%' },
] as const;

function Alfinete({ id, x, y, i }: { id: NomeIcone; x: string; y: string; i: number }) {
  const { v } = useLaco(2400 + i * 300, 200);
  return (
    <Animated.View accessibilityElementsHidden importantForAccessibility="no-hide-descendants"
      style={{ position: 'absolute', left: x as `${number}%`, top: y as `${number}%`, width: 46, height: 46, borderRadius: 23,
        backgroundColor: 'rgba(255,255,255,0.10)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.18)', alignItems: 'center',
        justifyContent: 'center', transform: [{ translateY: v.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0, -8, 0] }) }] }}>
      <Icone nome={id} tamanho={24} cor="#FFFFFF" />
    </Animated.View>
  );
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
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: larga ? 'center' : 'flex-start', paddingVertical: larga ? 32 : 0 }}
          keyboardShouldPersistTaps="handled" bounces={false}>
          <View style={{ flexGrow: larga ? 0 : 1, width: '100%', maxWidth: 460, alignSelf: 'center' }}>
          <SafeAreaView edges={['top']} style={{ flexGrow: 1, minHeight: 320, justifyContent: 'center', alignItems: 'center',
            paddingHorizontal: 28, paddingVertical: 32, gap: 6 }}>
            <Topografia />
            {ALFINETES.map((a, i) => <Alfinete key={a.id} {...a} i={i} />)}
            <Surge><Lupa /></Surge>
            <Surge ordem={2}>
              <Text accessibilityRole="header" style={{ fontFamily: FONTE_TITULO, fontSize: 52, color: '#FFFFFF', letterSpacing: -1.5,
                lineHeight: 56, textAlign: 'center' }}>
                WishLens
              </Text>
            </Surge>
            <Surge ordem={4}><Text className="font-texto" style={{ color: '#D6EDE2', fontSize: 18, textAlign: 'center' }}>Aponte. Fotografe. Descubra.</Text></Surge>
          </SafeAreaView>

          <SafeAreaView edges={larga ? [] : ['bottom']} style={{ backgroundColor: c.superficie, borderTopLeftRadius: 30, borderTopRightRadius: 30,
            ...(larga ? { borderRadius: 28, marginHorizontal: 16 } : null),
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
