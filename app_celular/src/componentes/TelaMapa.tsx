// Celular: a página do mapa (src/lib/mapaHtml.ts) numa WebView.
import { forwardRef, useImperativeHandle, useRef } from 'react';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { MAPA_HTML } from '../lib/mapaHtml';

export type TelaMapaRef = { mandar: (mensagem: object) => void; iniciar: (lat: number, lon: number) => void };
type Props = { aoReceber: (mensagem: { tipo: string } & Record<string, unknown>) => void; rotulo: string };

export const TelaMapa = forwardRef<TelaMapaRef, Props>(function TelaMapa({ aoReceber, rotulo }, ref) {
  const web = useRef<WebView<object>>(null);
  useImperativeHandle(ref, () => ({
    mandar: (m) => web.current?.injectJavaScript(`window.receber(${JSON.stringify(m)});true;`),
    iniciar: (lat, lon) => web.current?.injectJavaScript(`window.iniciar(${Number(lat)},${Number(lon)});true;`),
  }));
  return (
    <WebView<object> ref={web} source={{ html: MAPA_HTML, baseUrl: 'https://wishlens.local/' }} originWhitelist={['*']}
      style={{ flex: 1, backgroundColor: 'transparent' }} accessibilityLabel={rotulo}
      // a página não navega para fora (o link da atribuição do OSM abriria dentro do app)
      onShouldStartLoadWithRequest={(pedido: { url: string }) => pedido.url.startsWith('https://wishlens.local') || pedido.url === 'about:blank'}
      onMessage={(evento: WebViewMessageEvent) => {
        try { aoReceber(JSON.parse(evento.nativeEvent.data)); } catch { /* mensagem que não é nossa */ }
      }} />
  );
});
