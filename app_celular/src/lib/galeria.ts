// Galeria do Museu: as fotos que a pessoa salvou, guardadas só neste celular (documentos do app + a lista no
// AsyncStorage). Somem se o app for desinstalado ou os dados do Expo Go forem apagados.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Directory, File, Paths } from 'expo-file-system';
import { useSyncExternalStore } from 'react';
import { Platform } from 'react-native';

export type FotoGaleria = {
  id: string; // id da captura (salvar de novo não duplica)
  arquivo: string; // no celular: nome em documentos/galeria; no navegador: a própria foto em data URL
  achado: string;
  emoji: string;
  tema: string;
  cor: string;
  pontos: number;
  criado_em: string;
};

const CHAVE = 'wl_galeria';
const MAX_WEB = 10; // o localStorage do navegador é pequeno; no navegador a galeria é só para testar

let fotos: FotoGaleria[] = [];
const ouvintes = new Set<() => void>();

function pasta() {
  return new Directory(Paths.document, 'galeria');
}

export function enderecoDa(f: FotoGaleria): string {
  return Platform.OS === 'web' ? f.arquivo : new File(pasta(), f.arquivo).uri;
}

function publicar(novas: FotoGaleria[]) {
  fotos = novas;
  ouvintes.forEach((o) => o());
  AsyncStorage.setItem(CHAVE, JSON.stringify(novas)).catch(() => {});
}

// Carrega uma vez ao abrir o app e descarta as entradas cujo arquivo sumiu
AsyncStorage.getItem(CHAVE)
  .then((t) => {
    const lidas: FotoGaleria[] = t ? JSON.parse(t) : [];
    const vivas = Platform.OS === 'web' ? lidas : lidas.filter((f) => new File(pasta(), f.arquivo).exists);
    fotos = vivas;
    ouvintes.forEach((o) => o());
    if (vivas.length !== lidas.length) AsyncStorage.setItem(CHAVE, JSON.stringify(vivas)).catch(() => {});
  })
  .catch(() => {});

async function comoDataUrl(uri: string): Promise<string> {
  const blob = await (await fetch(uri)).blob();
  return new Promise((ok, falha) => {
    const leitor = new FileReader();
    leitor.onload = () => ok(String(leitor.result));
    leitor.onerror = () => falha(leitor.error);
    leitor.readAsDataURL(blob);
  });
}

/** Guarda a foto (a versão de 1024 px que foi ao juiz) na galeria. Devolve false se ela já estava lá. */
export async function salvarNaGaleria(uri: string, dados: Omit<FotoGaleria, 'arquivo' | 'criado_em'>): Promise<boolean> {
  if (fotos.some((f) => f.id === dados.id)) return false;
  let arquivo: string;
  if (Platform.OS === 'web') {
    arquivo = await comoDataUrl(uri);
  } else {
    const destino = pasta();
    destino.create({ idempotent: true, intermediates: true });
    arquivo = `${dados.id.replace(/[^\w-]/g, '')}.jpg`;
    const alvo = new File(destino, arquivo);
    if (!alvo.exists) new File(uri).copy(alvo); // a foto da câmera fica no cache, que o sistema pode limpar
  }
  const nova: FotoGaleria = { ...dados, arquivo, criado_em: new Date().toISOString() };
  publicar([nova, ...fotos].slice(0, Platform.OS === 'web' ? MAX_WEB : undefined));
  return true;
}

export function apagarDaGaleria(id: string) {
  const f = fotos.find((x) => x.id === id);
  if (!f) return;
  if (Platform.OS !== 'web') {
    try {
      const arquivo = new File(pasta(), f.arquivo);
      if (arquivo.exists) arquivo.delete();
    } catch {
      // o arquivo já não existe: basta tirar da lista
    }
  }
  publicar(fotos.filter((x) => x.id !== id));
}

export function useGaleria(): FotoGaleria[] {
  return useSyncExternalStore((o) => {
    ouvintes.add(o);
    return () => { ouvintes.delete(o); };
  }, () => fotos);
}
