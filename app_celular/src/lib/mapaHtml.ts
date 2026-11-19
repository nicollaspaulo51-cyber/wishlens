// Página do mapa (MapLibre GL JS, BSD-3; estilo e blocos do OpenFreeMap, MIT, dados © OpenStreetMap, ODbL).
// Roda numa WebView no celular e num iframe na web. Ela só desenha: quem decide grupos, pulsos e cores é o Mapa.tsx.
// Entrada: receber({tipo: 'desenhar' | 'ir' | 'enquadrar', ...}). Saída: {tipo: 'pronto' | 'regiao', ...}.
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
  body.escuro .maplibregl-canvas { filter: invert(1) hue-rotate(180deg) brightness(0.85) contrast(0.9); }
  .lugar, .grupo, .voce, .guardiao { display: flex; align-items: center; justify-content: center; border-radius: 50%;
    box-sizing: border-box; cursor: pointer; font-family: system-ui, sans-serif; }
  .lugar { width: 36px; height: 36px; border: 2px solid; font-size: 18px; position: relative; }
  .grupo { width: 40px; height: 40px; border: 2px solid; color: #fff; font-size: 14px; font-weight: 700; }
  .voce { width: 18px; height: 18px; border: 2px solid; cursor: default; }
  .guardiao { width: 44px; height: 44px; border: 1px solid; font-size: 22px; opacity: 0.9; }
  .lugar.pulsa::before { content: ''; position: absolute; inset: -2px; border-radius: 50%; background: var(--cor);
    opacity: var(--miolo); border: var(--borda) solid var(--cor); animation: pulso 3.2s cubic-bezier(.2,.7,.3,1) infinite;
    animation-delay: var(--atraso); z-index: -1; }
  @keyframes pulso { 0% { transform: scale(1); opacity: var(--miolo-ini); } 50%, 100% { transform: scale(var(--alcance)); opacity: 0; } }
  .maplibregl-popup-content { padding: 10px 12px; border-radius: 6px; box-shadow: none; border: 1px solid; width: 206px; font-family: system-ui, sans-serif; }
  .maplibregl-popup-tip { display: none; }
  .titulo { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  .linha { font-size: 13px; }
</style>
</head><body>
<div id="mapa"></div>
<script>
  var enviar = function (m) {
    var s = JSON.stringify(m);
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(s); else window.parent.postMessage(s, '*');
  };
  var mapa = null, pronto = false, pendente = null, cores = {}, marcadores = {};

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

  function elemento(item) {
    var e = document.createElement('div');
    e.setAttribute('role', 'button');
    if (item.tipo === 'grupo') {
      e.className = 'grupo'; e.style.background = item.cor; e.style.borderColor = cores.superficie;
      e.textContent = String(item.quantos);
      e.setAttribute('aria-label', item.quantos + ' lugares. Toque para aproximar');
      e.addEventListener('click', function (ev) {
        ev.stopPropagation();
        mapa.easeTo({ center: [item.lon, item.lat], zoom: mapa.getZoom() + 1.6 });
      });
    } else if (item.tipo === 'voce') {
      e.className = 'voce'; e.style.background = cores.agua; e.style.borderColor = cores.aguaTinta;
      e.setAttribute('aria-label', 'Você'); e.removeAttribute('role');
    } else if (item.tipo === 'guardiao') {
      e.className = 'guardiao'; e.style.background = cores.ficha; e.style.borderColor = cores.linha; e.textContent = '🏅';
      e.setAttribute('aria-label', 'Guardião da semana');
    } else {
      e.className = 'lugar'; e.style.background = item.cor; e.style.borderColor = cores.superficie;
      e.textContent = item.emoji;
      e.setAttribute('aria-label', item.titulo + ', ' + item.distancia.toFixed(1) + ' km');
    }
    return e;
  }

  function pulso(e, item) {
    e.classList.toggle('pulsa', !!item.pulsa);
    if (!item.pulsa) return;
    var forte = item.forte;
    e.style.setProperty('--cor', item.corPulso);
    e.style.setProperty('--alcance', forte ? '2.4' : '1.6');
    e.style.setProperty('--miolo', forte ? '0.22' : '0.08');
    e.style.setProperty('--miolo-ini', forte ? '0.8' : '0.4');
    e.style.setProperty('--borda', forte ? '2px' : '1px');
    e.style.setProperty('--atraso', item.atraso + 'ms');
  }

  function desenhar(d) {
    cores = d.cores;
    document.body.classList.toggle('escuro', !!d.escuro);
    var novos = {};
    d.itens.forEach(function (item) {
      var chave = item.chave + '|' + (item.cor || '') + '|' + (item.emoji || '') + '|' + (item.quantos || '');
      var m = marcadores[chave];
      if (!m) {
        var e = elemento(item);
        m = new maplibregl.Marker({ element: e }).setLngLat([item.lon, item.lat]);
        if (item.tipo === 'lugar') m.setPopup(balao(item.titulo, item.distancia, item.linha));
        if (item.tipo === 'guardiao') m.setPopup(balao('Guardião da semana', null, item.linha));
        m.addTo(mapa);
      } else {
        m.setLngLat([item.lon, item.lat]);
      }
      if (item.tipo === 'lugar') pulso(m.getElement(), item);
      novos[chave] = m;
    });
    Object.keys(marcadores).forEach(function (k) { if (!novos[k]) marcadores[k].remove(); });
    marcadores = novos;
    mapa.getSource('manchas').setData({ type: 'FeatureCollection', features: d.manchas.map(function (m) {
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [m.lon, m.lat] },
        properties: { preenche: m.preenche, borda: m.borda } };
    }) });
    // raio de 250 m em pixels: metros por pixel = 156543 * cos(lat) / 2^zoom
    var mpp0 = 156543.03 * Math.cos(d.lat * Math.PI / 180);
    mapa.setPaintProperty('manchas', 'circle-radius', ['interpolate', ['exponential', 2], ['zoom'], 0, 250 / mpp0, 22, 250 / (mpp0 / Math.pow(2, 22))]);
  }

  function estiloPopup() {
    var s = document.getElementById('estilo-popup') || document.head.appendChild(document.createElement('style'));
    s.id = 'estilo-popup';
    s.textContent = '.maplibregl-popup-content{background:' + cores.superficie + ';border-color:' + cores.linha + '}';
  }

  window.receber = function (m) {
    if (!pronto) { if (m.tipo === 'desenhar') pendente = m; return; }
    if (m.tipo === 'desenhar') { desenhar(m); estiloPopup(); }
    else if (m.tipo === 'ir') mapa.easeTo({ center: [m.lon, m.lat] });
    else if (m.tipo === 'enquadrar') {
      var b = new maplibregl.LngLatBounds();
      m.pontos.forEach(function (p) { b.extend([p.lon, p.lat]); });
      mapa.fitBounds(b, { padding: { top: 72, right: 68, bottom: 48, left: 48 }, maxZoom: 16 });
    }
  };

  function iniciar(lat, lon) {
    mapa = new maplibregl.Map({ container: 'mapa', style: 'https://tiles.openfreemap.org/styles/positron',
      center: [lon, lat], zoom: 14.3, attributionControl: { compact: true }, pitchWithRotate: false, dragRotate: false });
    mapa.touchZoomRotate.disableRotation();
    mapa.on('load', function () {
      // nomes de comércio e ícones do estilo competiam com os marcadores do jogo
      mapa.getStyle().layers.forEach(function (l) { if (/poi/.test(l.id)) mapa.setLayoutProperty(l.id, 'visibility', 'none'); });
      mapa.addSource('manchas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      mapa.addLayer({ id: 'manchas', type: 'circle', source: 'manchas', paint: { 'circle-color': ['get', 'preenche'],
        'circle-stroke-color': ['get', 'borda'], 'circle-stroke-width': 1, 'circle-radius': 10 } });
      pronto = true;
      if (pendente) { window.receber(pendente); pendente = null; }
      regiao();
      enviar({ tipo: 'pronto' });
    });
    mapa.on('moveend', regiao);
    mapa.on('resize', regiao);
  }
  window.iniciar = iniciar;
  enviar({ tipo: 'carregou' });
</script>
</body></html>`;
