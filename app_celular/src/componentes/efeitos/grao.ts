// Grão de papel: um ladrilho de ruído desenhado uma vez pelo Skia e usado como imagem repetida atrás das fichas.
// Fica em memória como data URI: nenhuma imagem nova no projeto e o mesmo desenho no celular e no navegador.
import { Skia } from '@shopify/react-native-skia';

let ladrilho: string | null | undefined;

export function graoDePapel(): string | null {
  if (ladrilho !== undefined) return ladrilho;
  try {
    const tamanho = 128;
    const superficie = Skia.Surface.Make(tamanho, tamanho);
    if (!superficie) return (ladrilho = null);
    const tela = superficie.getCanvas();
    const tinta = Skia.Paint();
    tinta.setShader(Skia.Shader.MakeFractalNoise(0.9, 0.9, 3, 7, tamanho, tamanho));
    tela.drawPaint(tinta);
    superficie.flush();
    ladrilho = `data:image/png;base64,${superficie.makeImageSnapshot().encodeToBase64()}`;
  } catch {
    ladrilho = null; // sem Skia (ainda carregando no navegador): a ficha fica lisa
  }
  return ladrilho;
}
