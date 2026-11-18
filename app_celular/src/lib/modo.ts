// A aba do jogo escolhida (Mapa livre, Paisagens, Treino, Academias): a câmera julga a foto nela e o Pódio abre
// nela. Fica guardada no aparelho: ao abrir o app de novo, volta na última aba usada.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';

import type { Modo } from './api';
import { useSessao } from './sessao';

const CHAVE = 'wl_aba';
const MODOS: Modo[] = ['livre', 'paisagens', 'treino', 'academia', 'competicao'];
let atual: Modo = 'livre';
const ouvintes = new Set<() => void>();

function avisar(m: Modo) {
  atual = m;
  ouvintes.forEach((f) => f());
}

AsyncStorage.getItem(CHAVE)
  .then((m) => { if (m && MODOS.includes(m as Modo) && m !== atual) avisar(m as Modo); })
  .catch(() => {});

export function escolherModo(m: Modo) {
  avisar(m);
  AsyncStorage.setItem(CHAVE, m).catch(() => {});
}

export function useModo(): Modo {
  const { convidado } = useSessao();
  const modo = useSyncExternalStore((f) => {
    ouvintes.add(f);
    return () => { ouvintes.delete(f); };
  }, () => atual);
  return convidado && modo === 'competicao' ? 'livre' : modo;
}

export const NOME_LIVRE = { id: 'livre', nome: 'Mapa livre', emoji: '', cor: '#3F5F55',
  conta: 'os 5 temas (carros, plantas, frutas e comidas, animais e peças de computador); o tema do dia vale o dobro',
  onde: 'lugares de cada tema' } as const;
