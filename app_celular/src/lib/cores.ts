// Paleta do WishLens: neutros de mapa topográfico com laranja de sinalização.
import { useColorScheme } from 'react-native';

export const PALETA = {
  // LARANJA = ação principal e tema do dia. AZUL = lugar, mapa e progresso. Nada mais ganha cor; sem misturar as duas em gradiente.
  claro: {
    fundo: '#EEF0ED', superficie: '#F8F9F7', tinta: '#191D1B', apagado: '#535B56', linha: '#CDD3CE',
    destaque: '#B23F06', destaqueTinta: '#FFFFFF', suave: '#E1E5E1', sol: '#CD4B09', solTinta: '#FFFFFF',
    recusa: '#B42318', figurinha: '#F8F9F7',
    agua: '#1F6B8C', aguaTinta: '#FFFFFF',
  },
  escuro: {
    fundo: '#111413', superficie: '#1A1E1C', tinta: '#E7EAE7', apagado: '#A2AAA5', linha: '#2D3330',
    destaque: '#FF7A2E', destaqueTinta: '#160800', suave: '#232826', sol: '#FF7A2E', solTinta: '#160800',
    recusa: '#FF8A80', figurinha: '#1A1E1C',
    agua: '#6CB4D4', aguaTinta: '#04161E',
  },
};
export type Cores = typeof PALETA.claro;

export function useCores(): Cores {
  return useColorScheme() === 'dark' ? PALETA.escuro : PALETA.claro;
}

export const FONTE_TITULO = 'Overpass_800ExtraBold';
export const FONTE_TITULO_MEDIA = 'Overpass_700Bold';
export const FONTE_TEXTO = 'Overpass_400Regular';
export const FONTE_TEXTO_FORTE = 'Overpass_700Bold';
export const FONTE_NUMERO = 'OverpassMono_600SemiBold';

// As mesmas cores como variáveis CSS (--fundo, --tinta...) para as classes do NativeWind (tailwind.config.js)
export const variaveis = (c: Cores) => Object.fromEntries(Object.entries(c).map(([k, v]) => [`--${k}`, v]));
