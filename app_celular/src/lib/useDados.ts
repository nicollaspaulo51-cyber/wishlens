// Busca um dado do servidor ao abrir a tela, de novo a cada volta para ela e, opcionalmente, a cada N segundos.
import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';

export function useDados<T>(buscar: () => Promise<T>, chaves: unknown[] = [], aCadaSegundos?: number) {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const atual = useRef(buscar);
  atual.current = buscar;

  const recarregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await atual.current());
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Algo deu errado.');
    } finally {
      setCarregando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, chaves);

  useFocusEffect(
    useCallback(() => {
      recarregar();
      if (!aCadaSegundos) return;
      const id = setInterval(recarregar, aCadaSegundos * 1000);
      return () => clearInterval(id);
    }, [recarregar, aCadaSegundos]),
  );

  return { dados, erro, carregando, recarregar };
}
