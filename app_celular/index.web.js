// Entrada do app no navegador: o Skia lê o CanvasKit quando é importado, então ele carrega antes de qualquer tela.
// require() dentro do then: o Metro só executa o app depois do CanvasKit pronto (public/canvaskit.wasm).
import { LoadSkiaWeb } from '@shopify/react-native-skia/lib/module/web';

LoadSkiaWeb({ locateFile: (arquivo) => `/${arquivo}` }).then(() => {
  require('expo-router/entry');
});
