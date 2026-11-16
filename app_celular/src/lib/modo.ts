// A aba do jogo escolhida em Jogar (Mapa livre, Paisagens, Treino, Academias): a câmera julga a foto nela
// e o Pódio abre nela. Fica só na memória do app: ao abrir de novo, volta ao Mapa livre.
import { useSyncExternalStore } from 'react';

import type { Modo } from './api';

let atual: Modo = 'livre';
const ouvintes = new Set<() => void>();

export function escolherModo(m: Modo) {
  atual = m;
  ouvintes.forEach((f) => f());
}

export function useModo(): Modo {
  return useSyncExternalStore((f) => {
    ouvintes.add(f);
    return () => ouvintes.delete(f);
  }, () => atual);
}

export const NOME_LIVRE = { id: 'livre', nome: 'Mapa livre', emoji: '🗺️' } as const;
