// Conversa com o servidor do juiz (servidor/app.py). Os tipos espelham o que as rotas devolvem.
import { Platform } from 'react-native';

export const SERVIDOR = (process.env.EXPO_PUBLIC_SERVIDOR_URL ?? 'http://localhost:7860').replace(/\/$/, '');

export type Tema = { id: string; nome: string; emoji: string; cor: string; onde: string };
export type Desafio = { texto: string; feito: number; alvo: number; ok: boolean };
export type Estado = {
  apelido: string;
  pontos_hoje: number;
  posicao: number | null;
  tema_do_dia: Tema;
  dia: { lupa: number; lupa_cheia: boolean; desafios: Desafio[] };
  corrente: number;
  meta: { feitas: number; alvo: number; aberta: boolean; cumprida: boolean; faltam_min: number; comeca: string; termina: string };
};
export type Cartao = {
  aceita: boolean;
  pontos: number;
  tema: Tema | null;
  achado: string;
  juizes: string;
  motivo?: string;
  partes?: string[];
  bonus?: string[];
  destaque?: string;
  pode_contestar: boolean;
};
export type Julgamento =
  | { status: 'borrada'; mensagem: string }
  | { status: 'ok'; id: string; cartao: Cartao; avisos: string[]; aviso_juiz: string | null; pontos_hoje: number; posicao: number | null };
export type LinhaPodio = { posicao: number; apelido: string; pontos: number; achados: number; voce: boolean };
export type Podio = { ranking: LinhaPodio[]; guardioes: { apelido: string; quadrados: number }[] };
export type Medalha = { id: string; nome: string; conta: string; nivel: 'bronze' | 'prata' | 'ouro' | null; valor: number; proximo: number };
export type Colecao = {
  resumo: { pontos: number; achados: number; corrente: number; fotos: number; recusadas: number };
  estilo: string | null;
  album: { tema: Tema; colados: { achado: string; turma: number }[]; total: number; faltam: { dica: string; turma: number }[]; medalha: Medalha | null }[];
  medalhas: Medalha[];
};
export type Lugar = { tema: string; nome: string; tipo: string | null; lat: number; lon: number; distancia_km: number; mapa: string };
export type Mancha = { celula: string; tema: string; n: number; achados: string[]; lat: number; lon: number; guardiao: string | null };
export type Mapa = { lugares: Lugar[]; manchas: Mancha[] };

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

// O provedor de sessão (sessao.tsx) diz quais cabeçalhos mandar: o token do Supabase ou o apelido de teste.
let cabecalhos: () => Promise<Record<string, string>> = async () => ({});
export function usarCabecalhos(fonte: typeof cabecalhos) {
  cabecalhos = fonte;
}

async function chamar<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(SERVIDOR + caminho, { ...init, headers: { ...(await cabecalhos()), ...(init.headers as object) } });
  } catch {
    throw new ErroApi(0, 'Sem conexão com o servidor do juiz. Confira a internet e tente de novo.');
  }
  if (!resp.ok) {
    const corpo = await resp.json().catch(() => ({}));
    const detalhe = typeof corpo.detail === 'string' ? corpo.detail : 'O servidor do juiz não respondeu direito.';
    throw new ErroApi(resp.status, detalhe);
  }
  return resp.json() as Promise<T>;
}

const json = (corpo: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(corpo),
});

export const api = {
  estado: () => chamar<Estado>('/estado'),
  podio: (periodo: string, tema?: string | null) =>
    chamar<Podio>(`/podio?periodo=${periodo}${tema ? `&tema=${encodeURIComponent(tema)}` : ''}`),
  colecao: () => chamar<Colecao>('/colecao'),
  temas: () => chamar<{ temas: Tema[]; tema_do_dia: string; modos: string[] }>('/temas'),
  // A posição vai no corpo, nunca na URL (a URL acaba nos logs do servidor)
  mapa: (lat: number, lon: number) => chamar<Mapa>('/mapa', json({ lat, lon })),
  contestar: (id: string, tema: string) => chamar<{ ok: boolean }>('/contestar', json({ id, tema })),
  async julgar(uri: string, posicao: { lat: number; lon: number } | null, modo = 'livre') {
    const form = new FormData();
    if (Platform.OS === 'web') {
      form.append('foto', await (await fetch(uri)).blob(), 'foto.jpg');
    } else {
      // React Native envia o arquivo a partir do uri (objeto próprio do RN, sem tipo no DOM)
      form.append('foto', { uri, name: 'foto.jpg', type: 'image/jpeg' } as unknown as Blob);
    }
    if (posicao) {
      form.append('lat', String(posicao.lat));
      form.append('lon', String(posicao.lon));
    }
    form.append('modo', modo);
    return chamar<Julgamento>('/julgar', { method: 'POST', body: form });
  },
};
