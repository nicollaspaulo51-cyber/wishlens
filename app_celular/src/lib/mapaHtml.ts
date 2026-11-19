// Página do mapa (MapLibre GL JS, BSD-3; estilo e blocos do OpenFreeMap, MIT, dados © OpenStreetMap, ODbL).
// Roda numa WebView no celular e num iframe na web. Ela só desenha: quem decide grupos, pulsos e cores é o Mapa.tsx.
// Lugares, grupos, "você" e o pulso são camadas do próprio mapa (não elementos HTML por cima): assim ficam
// grudados no mapa em qualquer zoom, mesmo num celular lento. Só o balão é HTML.
// Entrada: receber({tipo: 'desenhar' | 'ir' | 'enquadrar', ...}). Saída: {tipo: 'carregou' | 'pronto' | 'regiao', ...}.
// shortcut: maplibre-gl e o estilo vêm da rede (unpkg e openfreemap); sem internet o mapa não carrega, como antes.
export const MAPA_HTML = `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>
  html, body, #mapa { margin: 0; height: 100%; width: 100%; background: #EEF1EF; }
  body.escuro, body.escuro #mapa { background: #141A1F; }
  .maplibregl-popup-content { padding: 10px 12px; border-radius: 6px; box-shadow: none; border: 1px solid; width: 206px; font-family: system-ui, sans-serif; }
  .maplibregl-popup-tip { display: none; }
  .titulo { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  .linha { font-size: 13px; }
</style>
</head><body>
<div id="mapa"></div>
<script>
  var ATRASOS = [0, 530, 1060]; // três ritmos defasados: os pulsos não acontecem todos juntos
  var enviar = function (m) {
    var s = JSON.stringify(m);
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(s); else window.parent.postMessage(s, '*');
  };
  var mapa = null, montado = false, ultimo = null, escuroAtual = false, cores = {};
  var imagens = {}, popup = null, popupChave = null, raf = 0, pulsando = false;

  function estilo(escuro) { return 'https://tiles.openfreemap.org/styles/' + (escuro ? 'dark' : 'positron'); }

  function regiao() {
    var b = mapa.getBounds(), c = mapa.getCenter();
    enviar({ tipo: 'regiao', latitude: c.lat, longitude: c.lng, latitudeDelta: b.getNorth() - b.getSouth(),
      longitudeDelta: b.getEast() - b.getWest(), largura: mapa.getContainer().clientWidth });
  }

  // Texto de lugar vem do OpenStreetMap: entra sempre como textContent, nunca como HTML
  function balao(titulo, km, linha) {
    var caixa = document.createElement('div');
    caixa.style.color = cores.tinta;
    var t = document.createElement('div'); t.className = 'titulo'; t.textContent = titulo; caixa.appendChild(t);
    var l = document.createElement('div'); l.className = 'linha'; l.style.color = cores.apagado;
    if (km !== undefined && km !== null) {
      var n = document.createElement('span'); n.style.color = cores.agua; n.textContent = km.toFixed(1) + ' km'; l.appendChild(n);
      if (linha) l.appendChild(document.createTextNode('  ·  '));
    }
    if (linha) l.appendChild(document.createTextNode(linha));
    caixa.appendChild(l);
    return new maplibregl.Popup({ offset: 22, closeButton: false, maxWidth: '232px' }).setDOMContent(caixa);
  }

  function fecharBalao() { if (popup) popup.remove(); popup = null; popupChave = null; }

  // Círculo com borda e um texto/emoji, desenhado numa imagem 2x e guardado para o mapa usar como ícone
  function imagem(id, tam, fundo, borda, texto, fonte, corTexto) {
    if (!imagens[id]) {
      var c = document.createElement('canvas'); c.width = c.height = tam * 2;
      var g = c.getContext('2d'); g.scale(2, 2);
      g.beginPath(); g.arc(tam / 2, tam / 2, tam / 2 - 1, 0, Math.PI * 2);
      g.fillStyle = fundo; g.fill(); g.lineWidth = 2; g.strokeStyle = borda; g.stroke();
      if (texto) {
        g.font = fonte; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = corTexto || '#fff';
        g.fillText(texto, tam / 2, tam / 2 + 1);
      }
      imagens[id] = g.getImageData(0, 0, tam * 2, tam * 2);
    }
    if (!mapa.hasImage(id)) mapa.addImage(id, imagens[id], { pixelRatio: 2 });
    return id;
  }

  function montar() {
    if (mapa.getSource('pontos')) return;
    // nomes de comércio e ícones do estilo competiam com os marcadores do jogo
    mapa.getStyle().layers.forEach(function (l) { if (/poi/.test(l.id)) mapa.setLayoutProperty(l.id, 'visibility', 'none'); });
    var vazio = { type: 'FeatureCollection', features: [] };
    mapa.addSource('manchas', { type: 'geojson', data: vazio });
    mapa.addLayer({ id: 'manchas', type: 'circle', source: 'manchas', paint: { 'circle-color': ['get', 'preenche'],
      'circle-stroke-color': ['get', 'borda'], 'circle-stroke-width': 1, 'circle-radius': 10 } });
    mapa.addSource('pulsos', { type: 'geojson', data: vazio });
    ATRASOS.forEach(function (_, i) {
      mapa.addLayer({ id: 'pulso' + i, type: 'circle', source: 'pulsos', filter: ['==', ['get', 'ritmo'], i], paint: {
        'circle-color': ['get', 'cor'], 'circle-radius': ['get', 'r0'], 'circle-opacity': 0,
        'circle-stroke-color': ['get', 'cor'], 'circle-stroke-width': ['get', 'borda'], 'circle-stroke-opacity': 0 } });
    });
    mapa.addSource('pontos', { type: 'geojson', data: vazio });
    mapa.addLayer({ id: 'pontos', type: 'symbol', source: 'pontos', layout: { 'icon-image': ['get', 'img'],
      'icon-allow-overlap': true, 'icon-ignore-placement': true, 'symbol-sort-key': ['get', 'z'] } });
    Object.keys(imagens).forEach(function (id) { if (!mapa.hasImage(id)) mapa.addImage(id, imagens[id], { pixelRatio: 2 }); });
    montado = true;
    if (ultimo) desenhar(ultimo);
  }

  function animar(t) {
    if (!pulsando) { raf = 0; return; }
    if (!animar.ultimo || t - animar.ultimo >= 33) { // ~30 quadros por segundo bastam e poupam o celular
      animar.ultimo = t;
      ATRASOS.forEach(function (atraso, i) {
        var f = (((t - atraso) % 3200) + 3200) % 3200 / 1600; // anel cresce em 1,6 s e espera outros 1,6 s
        var p = f >= 1 ? 1 : 1 - Math.pow(1 - f, 3);
        mapa.setPaintProperty('pulso' + i, 'circle-radius', ['*', ['get', 'r0'], ['+', 1, ['*', ['get', 'alc'], p]]]);
        mapa.setPaintProperty('pulso' + i, 'circle-opacity', ['*', ['get', 'op'], 1 - p]);
        mapa.setPaintProperty('pulso' + i, 'circle-stroke-opacity', ['*', ['get', 'bop'], 1 - p]);
      });
    }
    raf = requestAnimationFrame(animar);
  }

  function desenhar(d) {
    ultimo = d; cores = d.cores;
    if (!!d.escuro !== escuroAtual) { // trocar entre o estilo claro e o escuro apaga as camadas: monta de novo
      escuroAtual = !!d.escuro;
      document.body.classList.toggle('escuro', escuroAtual);
      montado = false;
      mapa.setStyle(estilo(escuroAtual), { diff: false }); // sem diff: começa de um estilo vazio, sem as nossas camadas velhas
      var aoCarregar = function () { // o MapLibre não tem "style.load": o estilo novo chegou quando a fonte dos mapas aparece
        if (!mapa.getSource('openmaptiles')) return;
        mapa.off('styledata', aoCarregar);
        montar();
      };
      mapa.on('styledata', aoCarregar);
      return;
    }
    if (!montado) return;
    var pontos = [], pulsos = [];
    d.itens.forEach(function (it) {
      var id, z;
      if (it.tipo === 'grupo') { id = imagem('g|' + it.cor + '|' + cores.superficie + '|' + it.quantos, 40, it.cor, cores.superficie, String(it.quantos), '700 14px system-ui, sans-serif'); z = 3; }
      else if (it.tipo === 'voce') { id = imagem('v|' + cores.agua + '|' + cores.aguaTinta, 18, cores.agua, cores.aguaTinta); z = 0; }
      else if (it.tipo === 'guardiao') { id = imagem('m|' + cores.ficha + '|' + cores.linha, 44, cores.ficha, cores.linha, '🏅', '22px system-ui, sans-serif'); z = 1; }
      else { id = imagem('l|' + it.cor + '|' + cores.superficie + '|' + it.emoji, 36, it.cor, cores.superficie, it.emoji, '18px system-ui, sans-serif'); z = 2; }
      pontos.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [it.lon, it.lat] }, properties: {
        img: id, z: z, tipo: it.tipo, chave: it.chave, titulo: it.titulo || '', distancia: it.distancia === undefined ? null : it.distancia,
        linha: it.linha || '' } });
      if (it.tipo === 'lugar' && it.pulsa) {
        pulsos.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [it.lon, it.lat] }, properties: {
          cor: it.corPulso, ritmo: Math.max(0, ATRASOS.indexOf(it.atraso)), r0: 18, alc: it.forte ? 1.4 : 0.6,
          op: it.forte ? 0.22 : 0.08, bop: it.forte ? 0.8 : 0.4, borda: it.forte ? 2 : 1 } });
      }
    });
    if (popupChave && !d.itens.some(function (it) { return it.chave === popupChave; })) fecharBalao();
    mapa.getSource('pontos').setData({ type: 'FeatureCollection', features: pontos });
    mapa.getSource('pulsos').setData({ type: 'FeatureCollection', features: pulsos });
    pulsando = pulsos.length > 0;
    if (pulsando && !raf) raf = requestAnimationFrame(animar);
    mapa.getSource('manchas').setData({ type: 'FeatureCollection', features: d.manchas.map(function (m) {
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [m.lon, m.lat] }, properties: { preenche: m.preenche, borda: m.borda } };
    }) });
    // raio de 250 m em pixels: metros por pixel = 156543 * cos(lat) / 2^zoom
    var mpp0 = 156543.03 * Math.cos(d.lat * Math.PI / 180);
    mapa.setPaintProperty('manchas', 'circle-radius', ['interpolate', ['exponential', 2], ['zoom'], 0, 250 / mpp0, 22, 250 / (mpp0 / Math.pow(2, 22))]);
    var s = document.getElementById('estilo-popup') || document.head.appendChild(document.createElement('style'));
    s.id = 'estilo-popup';
    s.textContent = '.maplibregl-popup-content{background:' + cores.superficie + ';border-color:' + cores.linha + '}';
  }

  window.receber = function (m) {
    if (m.tipo === 'desenhar') desenhar(m);
    else if (!montado) return;
    else if (m.tipo === 'ir') mapa.easeTo({ center: [m.lon, m.lat] });
    else if (m.tipo === 'enquadrar') {
      var b = new maplibregl.LngLatBounds();
      m.pontos.forEach(function (p) { b.extend([p.lon, p.lat]); });
      mapa.fitBounds(b, { padding: { top: 72, right: 68, bottom: 48, left: 48 }, maxZoom: 16 });
    }
  };

  window.iniciar = function (lat, lon, escuro) {
    escuroAtual = !!escuro;
    document.body.classList.toggle('escuro', escuroAtual);
    mapa = new maplibregl.Map({ container: 'mapa', style: estilo(escuroAtual),
      center: [lon, lat], zoom: 14.3, attributionControl: { compact: true }, pitchWithRotate: false, dragRotate: false });
    mapa.touchZoomRotate.disableRotation();
    mapa.on('load', function () {
      montar();
      regiao();
      enviar({ tipo: 'pronto' });
    });
    mapa.on('click', 'pontos', function (e) {
      var p = e.features[0].properties, c = e.features[0].geometry.coordinates.slice();
      if (p.tipo === 'grupo') { mapa.easeTo({ center: c, zoom: mapa.getZoom() + 1.6 }); return; }
      if (p.tipo === 'voce') return;
      fecharBalao();
      popup = (p.tipo === 'lugar' ? balao(p.titulo, p.distancia === null ? null : Number(p.distancia), p.linha)
        : balao('Guardião da semana', null, p.linha)).setLngLat(c).addTo(mapa);
      popupChave = p.chave;
    });
    mapa.on('moveend', regiao);
    mapa.on('resize', regiao);
  };
  enviar({ tipo: 'carregou' });
</script>
</body></html>`;
