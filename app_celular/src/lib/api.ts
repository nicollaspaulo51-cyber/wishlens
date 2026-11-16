// Conversa com o servidor do juiz (servidor/app.py). Os tipos espelham o que as rotas devolvem.
import { fetch as fetchExpo } from 'expo/fetch';
import { File } from 'expo-file-system';
import { Platform } from 'react-native';

export const SERVIDOR = (process.env.EXPO_PUBLIC_SERVIDOR_URL ?? 'http://localhost:7860').replace(/\/$/, '');

export type Tema = { id: string; nome: string; emoji: string; cor: string; onde: string };
// Aba do jogo além do Mapa livre (Paisagens, Treino ao ar livre, Academias): conta = o que vale nela
export type Aba = Tema & { conta: string };
export type Modo = 'livre' | 'paisagens' | 'treino' | 'academia';
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
  | { status: 'borrada'; titulo?: string; mensagem: string }
  | { status: 'ok'; id: string; cartao: Cartao; avisos: string[]; aviso_juiz: string | null; pontos_hoje: number; posicao: number | null };
export type LinhaPodio = { posicao: number; apelido: string; pontos: number; achados: number; voce: boolean };
export type Podio = { ranking: LinhaPodio[]; guardioes: { apelido: string; quadrados: number }[]; donos?: { apelido: string; quadrados: number }[] };
export type Medalha = { id: string; nome: string; conta: string; nivel: 'bronze' | 'prata' | 'ouro' | null; valor: number; proximo: number };
export type Colecao = {
  resumo: { pontos: number; achados: number; corrente: number; fotos: number; recusadas: number };
  estilo: string | null;
  album: { tema: Tema; colados: { achado: string; turma: number }[]; total: number; faltam: { dica: string; turma: number }[]; medalha: Medalha | null }[];
  medalhas: Medalha[];
};
export type Lugar = { tema: string; nome: string; tipo: string | null; lat: number; lon: number; distancia_km: number; mapa: string };
export type Mancha = { celula: string; tema: string; n: number; achados: string[]; lat: number; lon: number; guardiao: string | null };
export type Mapa = { lugares: Lugar[]; manchas: Mancha[]; lugares_ok?: boolean };

export type TipoAviso = 'juiz' | 'app' | 'outro';

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

async function chamar<T>(caminho: string, init: RequestInit = {}, enviar: typeof fetch = fetch): Promise<T> {
  let resp: Response;
  try {
    resp = await enviar(SERVIDOR + caminho, { ...init, headers: { ...(await cabecalhos()), ...(init.headers as object) } });
  } catch (erro) {
    console.warn('falha ao chamar o juiz', caminho, erro);
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
  podio: (periodo: string, tema?: string | null, modo: Modo = 'livre') =>
    chamar<Podio>(`/podio?periodo=${periodo}&modo=${modo}${tema ? `&tema=${encodeURIComponent(tema)}` : ''}`),
  colecao: () => chamar<Colecao>('/colecao'),
  temas: () => chamar<{ temas: Tema[]; tema_do_dia: string; modos: string[]; abas?: Aba[] }>('/temas'),
  // A posição vai no corpo, nunca na URL (a URL acaba nos logs do servidor)
  mapa: (lat: number, lon: number, modo: Modo = 'livre') => chamar<Mapa>('/mapa', json({ lat, lon, modo })),
  contestar: (id: string, tema: string) => chamar<{ ok: boolean }>('/contestar', json({ id, tema })),
  avisar: (tipo: TipoAviso, texto: string, captura?: string) =>
    chamar<{ ok: boolean }>('/aviso', json({ tipo, texto, captura: captura ?? null, aparelho: `${Platform.OS} ${Platform.Version}` })),
  async julgar(uri: string, posicao: { lat: number; lon: number } | null, modo: Modo = 'livre') {
    const form = new FormData();
    if (Platform.OS === 'web') {
      form.append('foto', await (await fetch(uri)).blob(), 'foto.jpg');
    } else {
      // SDK 58: o arquivo vai como File do expo-file-system, enviado pelo fetch do expo (o {uri, name, type} antigo falha)
      form.append('foto', new File(uri), 'foto.jpg');
    }
    if (posicao) {
      form.append('lat', String(posicao.lat));
      form.append('lon', String(posicao.lon));
    }
    form.append('modo', modo);
    const enviar = Platform.OS === 'web' ? undefined : (fetchExpo as unknown as typeof fetch);
    return chamar<Julgamento>('/julgar', { method: 'POST', body: form }, enviar);
  },
};
