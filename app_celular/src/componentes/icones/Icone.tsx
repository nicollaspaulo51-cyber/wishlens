// Ícones lineares do WishLens, desenhados em SVG sobre uma grade de 24×24.
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

// Círculo como traço de caminho (dois arcos), para tudo ser só <Path>
const o = (x: number, y: number, r: number) => `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;

const TRACOS = {
  // barra de baixo
  mapa: ['M3 6.6l5.6-2.4 6.9 2.5 5.5-2.3v13.4l-5.5 2.4-6.9-2.5L3 20.1z', 'M8.6 4.3v13.3', 'M15.5 6.8v13.2'],
  trofeu: ['M7.1 4h9.8v4.6a4.9 4.9 0 0 1-9.8 0z', 'M7.1 6.1H4.6a2.6 2.6 0 0 0 2.7 3.4', 'M16.9 6.1h2.5a2.6 2.6 0 0 1-2.7 3.4',
    'M12 13.6v3.3', 'M8.7 20.4h6.6', 'M10 16.9h4l.5 3.5H9.5z'],
  amigos: [o(8.6, 7.4, 3.2), 'M3 19.6c.6-3.6 2.8-5.6 5.6-5.6s4.9 2 5.5 5.6', 'M15.8 4.9a2.7 2.7 0 1 1 .2 5.4', 'M17.1 14.1c2.1.5 3.5 2.4 3.9 5.2'],
  chat: ['M4 5.4h16.1v10.3H10.4L6 19.6v-3.9H4z', 'M8 9.4h8.1', 'M8 12.4h5'],
  museu: ['M3 9.5 12 4l9 5.5z', 'M5.1 9.6v7.9', 'M9.7 9.6v7.9', 'M14.3 9.6v7.9', 'M18.9 9.6v7.9', 'M4 17.5h16', 'M2.9 20.1h18.2'],
  bussola: [o(12, 12, 9), 'M15.8 8.2l-2.2 5.4-5.4 2.2 2.2-5.4z'],
  camera: ['M4 7.6h3.6L9.1 5h5.8l1.5 2.6H20v11.5H4z', o(12, 13.1, 3.6)],
  lupa: [o(10.4, 10.4, 6.1), 'M14.9 14.9l5.6 5.6'],
  cadeado: ['M7 10V7a5 5 0 0 1 10 0v3', 'M5 10h14v11H5z', 'M12 14v3'],
  // temas do Mapa livre
  // carro de lado: capô, teto com duas janelas e as rodas
  carros: ['M4.8 16.5H3v-3.7l3.3-1.2 2.9-3.8h5.9l3.3 3.8 2.6.6v4.3h-1.8', 'M9.2 16.5h5.6', 'M6.6 11.6h11.6', 'M12 7.9v3.7',
    o(7, 16.8, 2.2), o(17, 16.8, 2.2)],
  plantas: ['M5 19.1C5 10.2 10.1 5 19.6 4.4 19 14 14 19.1 5 19.1z', 'M5 19.1l8.6-8.7'],
  // maçã com cabinho e folha
  comidas: ['M12 7.6c-1.4-1-4.6-1.6-6.2.8-1.8 2.7-.9 7.6 1.5 10.4 1.3 1.5 2.6 1.7 4.7.9 2.1.8 3.4.6 4.7-.9 2.4-2.8 3.3-7.7 1.5-10.4-1.6-2.4-4.8-1.8-6.2-.8z',
    'M12 7.6c0-1.6.4-3 1.5-4.1', 'M13.5 5.2c1.2-1.4 3.1-1.6 4.3-1.1-.6 1.6-2.4 2.4-4.3 1.1z'],
  // tema antigo (as aves agora são do tema Animais): fica para as capturas de antes
  passaros: ['M4 13.6c3 0 4.6-1.5 5.6-4.1a4 4 0 0 1 7.6 1.2l3.3.3-3.2 1.4c-.6 4-3.8 6.1-7.6 6.1H6z', 'M14.7 9.6h.02',
    'M10 18.5l-1.5 2.6', 'M12.6 18l.4 2.9'],
  pets: [o(6.9, 9.1, 1.7), o(10.4, 5.9, 1.8), o(14.6, 5.9, 1.8), o(18.1, 9.1, 1.7),
    'M8 17c0-3 2-5.3 4.5-5.3S17 14 17 17c0 2-1.6 2.6-2.8 2.2-1.3-.4-2.1-.4-3.4 0C9.6 19.6 8 19 8 17z'],
  pecas: ['M3.5 4.6h17v10.9h-17z', 'M9 20h6.1', 'M12 15.5V20', 'M6.5 7.6l2.3 2.2', 'M11 7.5l-1 .9'],
  // abas do jogo
  livre: ['M3 6.6l5.6-2.4 6.9 2.5 5.5-2.3v13.4l-5.5 2.4-6.9-2.5L3 20.1z', 'M8.6 4.3v13.3', 'M15.5 6.8v13.2'],
  paisagens: ['M2.5 19.5 9 9.1l4 6 2.5-3.6 6 8z', o(16.5, 6.6, 2)],
  treino: ['M5 20V6.5', 'M19 20V6.5', 'M3.5 6.5h17', 'M9.5 6.5v3', 'M14.5 6.5v3', o(12, 12.5, 1.9)],
  academia: ['M3 9.6v4.9', 'M6.1 7.4v9.2', 'M17.9 7.4v9.2', 'M21 9.6v4.9', 'M6.1 12h11.8'],
  competicao: ['M7.5 8h9a4.5 4.5 0 0 1 4.3 5.8l-.9 3a2.2 2.2 0 0 1-3.8.7L14 15.5h-4l-2.1 2a2.2 2.2 0 0 1-3.8-.7l-.9-3A4.5 4.5 0 0 1 7.5 8z',
    'M8 10.5v3', 'M6.5 12h3', 'M15.5 11h.02', 'M17.5 13h.02'],
  // pequenos
  medalha: [o(12, 15, 5.2), 'M8.4 3.4l2.4 6.6', 'M15.6 3.4l-2.4 6.6', 'M8.4 3.4h7.2'],
  fechar: ['M6 6l12 12', 'M18 6 6 18'],
  mira: [o(12, 12, 6.5), 'M12 2.5v4', 'M12 17.5v4', 'M2.5 12h4', 'M17.5 12h4', o(12, 12, 1.2)],
  alfinete: ['M12 21s-6.5-6.2-6.5-11.2a6.5 6.5 0 0 1 13 0C18.5 14.8 12 21 12 21z', o(12, 9.8, 2.3)],
} as const;

export type NomeIcone = keyof typeof TRACOS;
export const temIcone = (nome: string): nome is NomeIcone => Object.hasOwn(TRACOS, nome);

export function Icone({ nome, tamanho = 24, cor, traco = 2, ativo = false }: {
  nome: NomeIcone; tamanho?: number; cor: string; traco?: number; ativo?: boolean;
}) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 24 24" pointerEvents="none">
      {/* marca-texto: o 1º traço preenchido bem claro, numa camada à parte */}
      {ativo ? <Path d={TRACOS[nome][0]} fill={cor} opacity={0.2} /> : null}
      {TRACOS[nome].map((d, i) => (
        <Path key={i} d={d} stroke={cor} strokeWidth={traco} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      ))}
    </Svg>
  );
}

/** Ícone do tema ou da aba pelo id ("carros", "academia"...), com um ponto se não houver desenho. */
export function IconeTema({ id, tamanho = 22, cor }: { id: string; tamanho?: number; cor: string }) {
  if (temIcone(id)) return <Icone nome={id} tamanho={tamanho} cor={cor} />;
  return <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: cor }} />;
}
