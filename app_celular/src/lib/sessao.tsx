import 'react-native-url-polyfill/auto';

import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type Session } from '@supabase/supabase-js';
import { randomUUID } from 'expo-crypto';
import { createContext, useContext, useEffect, useLayoutEffect, useMemo, useState, type ReactNode } from 'react';
import { AppState, Platform } from 'react-native';

import { usarCabecalhos } from './api';

const URL = process.env.EXPO_PUBLIC_SUPABASE_URL;
const CHAVE = process.env.EXPO_PUBLIC_SUPABASE_KEY;
export const supabase = URL && CHAVE
  ? createClient(URL, CHAVE, {
      auth: { storage: AsyncStorage, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false },
    })
  : null;

if (supabase && Platform.OS !== 'web') {
  // O token só se renova com o app aberto
  AppState.addEventListener('change', (estado) =>
    estado === 'active' ? supabase.auth.startAutoRefresh() : supabase.auth.stopAutoRefresh(),
  );
}

const CHAVE_APELIDO = 'wl_apelido';
const CHAVE_MODO = 'wl_modo_sessao';
const CHAVE_APARELHO = 'wl_chave';
type ModoSessao = 'conta' | 'convidado';

// Erros do Supabase Auth vêm em inglês: os mais comuns em português, o resto como veio
const ERROS: [RegExp, string][] = [
  [/invalid login credentials/i, 'E-mail ou senha errados.'],
  [/email not confirmed/i, 'Confirme o seu e-mail antes de entrar: abra o link que chegou na sua caixa de entrada (veja também o spam).'],
  [/already registered|already exists/i, 'Já existe uma conta com este e-mail. Toque em Voltar e depois em Entrar.'],
  [/password should be at least/i, 'A senha precisa ter pelo menos 6 caracteres.'],
  [/unable to validate email|invalid format|invalid email/i, 'Esse e-mail não parece válido.'],
  [/rate limit|too many requests|security purposes/i, 'Muitas tentativas seguidas. Espere um minuto e tente de novo.'],
  [/database error saving new user/i, 'O banco não conseguiu criar o seu perfil. Talvez esse apelido já esteja em uso.'],
  [/network request failed|failed to fetch/i, 'Sem conexão com a internet. Confira e tente de novo.'],
];
function emPortugues(msg: string) {
  return ERROS.find(([r]) => r.test(msg))?.[1] ?? msg;
}

async function chaveDoAparelho() {
  const guardada = await AsyncStorage.getItem(CHAVE_APARELHO);
  if (guardada) return guardada;
  const nova = `${randomUUID()}${randomUUID()}`.replace(/-/g, '');
  await AsyncStorage.setItem(CHAVE_APARELHO, nova);
  return nova;
}

type Sessao = {
  pronto: boolean;
  entrou: boolean;
  convidado: boolean;
  contasDisponiveis: boolean;
  criarAoSair: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  cadastrar: (email: string, senha: string, apelido: string) => Promise<string>;
  entrarComoConvidado: (apelido: string) => Promise<void>;
  sair: (paraCriarConta?: boolean) => Promise<void>;
};

const Contexto = createContext<Sessao | null>(null);

export function ProvedorSessao({ children }: { children: ReactNode }) {
  const [pronto, setPronto] = useState(false);
  const [sessao, setSessao] = useState<Session | null>(null);
  const [apelido, setApelido] = useState<string | null>(null);
  const [modo, setModo] = useState<ModoSessao | null>(null);
  const [criarAoSair, setCriarAoSair] = useState(false);
  const convidado = modo === 'convidado' && !!apelido;

  useEffect(() => {
    const auth = supabase?.auth.onAuthStateChange((_evento, nova) => setSessao(nova));
    let ativo = true;
    AsyncStorage.multiGet([CHAVE_MODO, CHAVE_APELIDO]).then(async ([[, salvo], [, nome]]) => {
      const atual = (await supabase?.auth.getSession())?.data.session;
      if (!ativo) return;
      setSessao(atual ?? null);
      setApelido(salvo === 'convidado' ? nome : null);
      setModo(salvo === 'convidado' && nome ? 'convidado' : atual ? 'conta' : null);
    }).catch(() => {}).finally(() => { if (ativo) setPronto(true); });
    return () => { ativo = false; auth?.data.subscription.unsubscribe(); };
  }, []);

  // Layout: roda antes dos useEffect das telas filhas, então a primeira chamada delas já sai com o apelido
  useLayoutEffect(() => {
    usarCabecalhos(async (): Promise<Record<string, string>> => {
      if (convidado && apelido) return { 'X-Apelido': encodeURIComponent(apelido), 'X-Chave': await chaveDoAparelho(), 'X-Convidado': '1' };
      if (modo === 'conta' && supabase) {
        const { data } = await supabase.auth.getSession(); // já renovado, se estava vencendo
        return data.session ? { Authorization: `Bearer ${data.session.access_token}` } : {};
      }
      return {};
    });
  }, [apelido, convidado, modo]);

  const valor = useMemo<Sessao>(() => ({
    pronto,
    entrou: convidado || (modo === 'conta' && !!sessao),
    convidado,
    contasDisponiveis: !!supabase,
    criarAoSair,
    async entrar(email, senha) {
      const { error } = await supabase!.auth.signInWithPassword({ email: email.trim(), password: senha });
      if (error) throw new Error(emPortugues(error.message));
      await AsyncStorage.setItem(CHAVE_MODO, 'conta');
      setModo('conta');
      setCriarAoSair(false);
    },
    async cadastrar(email, senha, apelidoNovo) {
      // O perfil (apelido público) é criado pelo gatilho criar_perfil do supabase/schema.sql
      const { data, error } = await supabase!.auth.signUp({
        email: email.trim(), password: senha, options: { data: { apelido: apelidoNovo.trim() } },
      });
      if (error) throw new Error(emPortugues(error.message));
      if (data.session) {
        await AsyncStorage.setItem(CHAVE_MODO, 'conta');
        setModo('conta');
        setCriarAoSair(false);
      }
      return data.session ? 'Conta criada.' : 'Conta criada. Confirme o e-mail que chegou e depois entre.';
    },
    async entrarComoConvidado(novo) {
      await chaveDoAparelho();
      await AsyncStorage.multiSet([[CHAVE_MODO, 'convidado'], [CHAVE_APELIDO, novo.trim()]]);
      setApelido(novo.trim());
      setModo('convidado');
      setCriarAoSair(false);
    },
    async sair(paraCriarConta = false) {
      if (supabase && sessao) {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
      }
      await AsyncStorage.multiRemove([CHAVE_MODO, CHAVE_APELIDO]);
      setCriarAoSair(paraCriarConta);
      setModo(null);
      setApelido(null);
    },
  }), [pronto, sessao, modo, convidado, criarAoSair]);

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao() {
  const s = useContext(Contexto);
  if (!s) throw new Error('useSessao fora do ProvedorSessao');
  return s;
}
