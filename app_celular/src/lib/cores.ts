// Paleta do WishLens: verde-pinheiro de mapa de trilha e o
// amarelo-sol da lupa, que só aparece em pontos e no tema do dia.
import { useColorScheme } from 'react-native';

export const PALETA = {
  // Caderno de campo: papel creme, tinta verde-pinheiro, sol da lupa e vermelho de carimbo
  claro: {
    fundo: '#F3EEDF', superficie: '#FBF8EF', tinta: '#1C2A22', apagado: '#55624F', linha: '#D8CFB8',
    destaque: '#136B4C', destaqueTinta: '#FFFFFF', suave: '#E6DEC8', sol: '#FFC83D', solTinta: '#2A2000',
    recusa: '#B4232A', figurinha: '#FFFDF6',
  },
  escuro: {
    fundo: '#141A16', superficie: '#1C241F', tinta: '#ECE6D6', apagado: '#A9B3A4', linha: '#323D35',
    destaque: '#4CC793', destaqueTinta: '#06130D', suave: '#26302A', sol: '#FFC83D', solTinta: '#2A2000',
    recusa: '#FF8A8F', figurinha: '#232D27',
  },
};
export type Cores = typeof PALETA.claro;

export function useCores(): Cores {
  return useColorScheme() === 'dark' ? PALETA.escuro : PALETA.claro;
}

export const FONTE_TITULO = 'BricolageGrotesque_800ExtraBold';
export const FONTE_TITULO_MEDIA = 'BricolageGrotesque_600SemiBold';
export const FONTE_TEXTO = 'AtkinsonHyperlegible_400Regular';
export const FONTE_TEXTO_FORTE = 'AtkinsonHyperlegible_700Bold';
export const FONTE_MAO = 'Caveat_700Bold';

// As mesmas cores como variáveis CSS (--fundo, --tinta...) para as classes do NativeWind (tailwind.config.js)
export const variaveis = (c: Cores) => Object.fromEntries(Object.entries(c).map(([k, v]) => [`--${k}`, v]));
