// Quem está jogando. Com o Supabase configurado: e-mail e senha (o mesmo login do app web).
// Sem ele: só um apelido, guardado no aparelho, e o servidor joga em memória (para testar).
import 'react-native-url-polyfill/auto';

import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type Session } from '@supabase/supabase-js';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
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

type Sessao = {
  pronto: boolean;
  entrou: boolean;
  comConta: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  cadastrar: (email: string, senha: string, apelido: string) => Promise<string>;
  entrarComApelido: (apelido: string) => Promise<void>;
  sair: () => Promise<void>;
};

const Contexto = createContext<Sessao | null>(null);

export function ProvedorSessao({ children }: { children: ReactNode }) {
  const [pronto, setPronto] = useState(false);
  const [sessao, setSessao] = useState<Session | null>(null);
  const [apelido, setApelido] = useState<string | null>(null);

  useEffect(() => {
    if (supabase) {
      supabase.auth.getSession().then(({ data }) => {
        setSessao(data.session);
        setPronto(true);
      });
      const { data } = supabase.auth.onAuthStateChange((_evento, nova) => setSessao(nova));
      return () => data.subscription.unsubscribe();
    }
    AsyncStorage.getItem(CHAVE_APELIDO).then((a) => {
      setApelido(a);
      setPronto(true);
    });
  }, []);

  useEffect(() => {
    usarCabecalhos(async (): Promise<Record<string, string>> => {
      if (supabase) {
        const { data } = await supabase.auth.getSession(); // já renovado, se estava vencendo
        return data.session ? { Authorization: `Bearer ${data.session.access_token}` } : {};
      }
      return apelido ? { 'X-Apelido': apelido } : {};
    });
  }, [apelido, sessao]);

  const valor = useMemo<Sessao>(() => ({
    pronto,
    entrou: supabase ? !!sessao : !!apelido,
    comConta: !!supabase,
    async entrar(email, senha) {
      const { error } = await supabase!.auth.signInWithPassword({ email: email.trim(), password: senha });
      if (error) throw new Error(error.message === 'Invalid login credentials' ? 'E-mail ou senha errados.' : error.message);
    },
    async cadastrar(email, senha, apelidoNovo) {
      // O perfil (apelido público) é criado pelo gatilho criar_perfil do supabase/schema.sql
      const { data, error } = await supabase!.auth.signUp({
        email: email.trim(), password: senha, options: { data: { apelido: apelidoNovo.trim() } },
      });
      if (error) throw new Error(error.message);
      return data.session ? 'Conta criada.' : 'Conta criada. Confirme o e-mail que chegou e depois entre.';
    },
    async entrarComApelido(novo) {
      await AsyncStorage.setItem(CHAVE_APELIDO, novo.trim());
      setApelido(novo.trim());
    },
    async sair() {
      if (supabase) await supabase.auth.signOut();
      await AsyncStorage.removeItem(CHAVE_APELIDO);
      setApelido(null);
    },
  }), [pronto, sessao, apelido]);

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao() {
  const s = useContext(Contexto);
  if (!s) throw new Error('useSessao fora do ProvedorSessao');
  return s;
}
