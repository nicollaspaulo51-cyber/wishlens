// Tokens do mapa topográfico. As cores vêm de variáveis (--fundo, --tinta...) que o _layout.tsx preenche com a
// PALETA de src/lib/cores.ts: um lugar só para as cores, e o tema claro/escuro troca sozinho.
const cor = (nome) => `var(--${nome})`;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  darkMode: 'class', // o tema claro/escuro já vem das variáveis (vars) no _layout.tsx
  theme: {
    extend: {
      colors: {
        papel: cor('fundo'), ficha: cor('superficie'), tinta: cor('tinta'), apagado: cor('apagado'), linha: cor('linha'),
        destaque: cor('destaque'), 'destaque-tinta': cor('destaqueTinta'), suave: cor('suave'), sol: cor('sol'),
        'sol-tinta': cor('solTinta'), carimbo: cor('recusa'), figurinha: cor('figurinha'),
        agua: cor('agua'), 'agua-tinta': cor('aguaTinta'),
      },
      fontFamily: {
        titulo: ['Overpass_800ExtraBold'], 'titulo-media': ['Overpass_700Bold'],
        texto: ['Overpass_400Regular'], 'texto-forte': ['Overpass_700Bold'], numero: ['OverpassMono_600SemiBold'],
      },
      borderRadius: { ficha: '6px' },
    },
  },
  plugins: [],
};
