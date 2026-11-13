// A mesma paleta do app web (src/ui.py e .streamlit/config.toml): verde-pinheiro de mapa de trilha e o
// amarelo-sol da lupa, que só aparece em pontos e no tema do dia.
import { useColorScheme } from 'react-native';

export const PALETA = {
  claro: {
    fundo: '#EEF2EC', superficie: '#FFFFFF', tinta: '#12241D', apagado: '#4A5F55', linha: '#C9D4CB',
    destaque: '#136B4C', destaqueTinta: '#FFFFFF', suave: '#DDE8DF', sol: '#FFC83D', solTinta: '#2A2000',
    recusa: '#B4232A', figurinha: '#FFFFFF',
  },
  escuro: {
    fundo: '#0E1914', superficie: '#16251E', tinta: '#E4EEE8', apagado: '#A3B8AD', linha: '#2C4136',
    destaque: '#4CC793', destaqueTinta: '#06130D', suave: '#1E3329', sol: '#FFC83D', solTinta: '#2A2000',
    recusa: '#FF8A8F', figurinha: '#22362C',
  },
};
export type Cores = typeof PALETA.claro;

export function useCores(): Cores {
  return useColorScheme() === 'dark' ? PALETA.escuro : PALETA.claro;
}

export const FONTE_TITULO = 'BricolageGrotesque_800ExtraBold';
export const FONTE_TITULO_MEDIA = 'BricolageGrotesque_600SemiBold';
