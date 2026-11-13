"""Mapa da tela principal: o personagem do WishLens anda sobre o mapa e os lugares dos temas piscam e somem.

Tudo roda no navegador (Leaflet), dentro de um componente HTML do Streamlit:
- o personagem (um explorador com uma lupa, desenho próprio do WishLens) fica na posição do jogador e
  acompanha o GPS (watchPosition), sem recarregar a página;
- cada lugar onde dá para achar um tema aparece, pisca e some num ritmo próprio; os do tema do dia são
  maiores e aparecem mais;
- 🟡 = onde a turma já achou coisas (quadrado de ~500 m, sem dizer quem), com o guardião da semana;
- mirante: o lugar a até 40 m de você para de piscar e pulsa (foto ali vale +5); a distância até o mais perto
  aparece no topo e muda enquanto você anda;
- tocar num ponto abre um cartão com o que procurar ali, a pista da turma para aquele tipo de lugar e "Como chegar".

Segurança: os dados vão como JSON e o JavaScript só usa textContent (nunca innerHTML com dados do OSM).
"""

from __future__ import annotations

import json
import random

from src.jogo import MIRANTE, MIRANTE_M

LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"

# Personagem: explorador com boné, mochila e uma lupa grande (a "lens" do WishLens). {cor} = cor do app.
PERSONAGEM_SVG = """
<svg viewBox="0 0 64 72" width="56" height="63" xmlns="http://www.w3.org/2000/svg" aria-label="Você">
  <ellipse cx="32" cy="68" rx="15" ry="3.5" fill="rgba(0,0,0,.28)"/>
  <rect x="17" y="34" width="9" height="17" rx="4" fill="#5B3A1E"/>
  <rect x="23" y="56" width="7" height="11" rx="3" fill="#2B2540"/>
  <rect x="34" y="56" width="7" height="11" rx="3" fill="#2B2540"/>
  <path d="M21 36 Q32 29 43 36 L45 58 Q32 62 19 58 Z" fill="{cor}"/>
  <path d="M27 40 L37 40 L36 46 L28 46 Z" fill="rgba(255,255,255,.35)"/>
  <circle cx="32" cy="22" r="11" fill="#F2C8A0"/>
  <path d="M20.5 20 Q32 6 43.5 20 Z" fill="{cor}"/>
  <rect x="30" y="16.5" width="18" height="4" rx="2" fill="{cor}"/>
  <circle cx="28" cy="24" r="1.6" fill="#1B1830"/>
  <circle cx="36" cy="24" r="1.6" fill="#1B1830"/>
  <path d="M29 28.5 Q32 30.5 35 28.5" stroke="#1B1830" stroke-width="1.4" fill="none" stroke-linecap="round"/>
  <line x1="44" y1="44" x2="53" y2="53" stroke="#5B3A1E" stroke-width="4" stroke-linecap="round"/>
  <circle cx="46" cy="40" r="8" fill="rgba(180,230,255,.55)" stroke="#FFD166" stroke-width="3"/>
  <circle cx="43.5" cy="37.5" r="2" fill="rgba(255,255,255,.9)"/>
  <path d="M43 44 Q40 43 39 40" stroke="#F2C8A0" stroke-width="3.5" fill="none" stroke-linecap="round"/>
</svg>
"""

PAGINA = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="__CSS__">
<style>
  html, body { margin:0; padding:0; height:100%; background:__FUNDO__; font-family: system-ui, sans-serif; }
  #mapa { position:absolute; inset:0; border-radius:18px; overflow:hidden; }
  .escuro .leaflet-tile-pane { filter: invert(1) hue-rotate(185deg) brightness(.85) contrast(.9) saturate(.6); }
  .leaflet-container { background:__FUNDO__; }
  .wl-personagem { animation: balanca 1.6s ease-in-out infinite; transform-origin: 50% 100%; }
  @keyframes balanca { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }
  .wl-alcance { width:120px; height:120px; border-radius:50%; border:2px solid __COR__;
                background: radial-gradient(circle, rgba(255,255,255,0) 55%, __COR_FRACA__);
                animation: alcance 2.6s ease-out infinite; }
  @keyframes alcance { 0% { transform:scale(.35); opacity:.9 } 100% { transform:scale(1.15); opacity:0 } }
  .wl-ponto { width:var(--t); height:var(--t); border-radius:50%; background:var(--c); position:relative;
              box-shadow: 0 0 0 3px rgba(255,255,255,.85), 0 0 18px var(--c);
              animation: piscar var(--d) ease-in-out var(--atraso) infinite; opacity:0; cursor:pointer; }
  .wl-ponto::after { content:""; position:absolute; inset:-6px; border-radius:50%; border:2px solid var(--c);
                     animation: onda 1.2s ease-out infinite; }
  .wl-ponto .wl-emoji { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
                        font-size: calc(var(--t) * .62); }
  .wl-ponto.turma { background:#FFC83D; box-shadow:0 0 0 3px #fff, 0 0 14px #FFC83D; }
  /* aparece, pisca e some: cada ponto com duração e atraso próprios */
  @keyframes piscar {
    0% { opacity:0; transform:scale(.3) } 12% { opacity:1; transform:scale(1.1) } 20% { transform:scale(1) }
    35% { opacity:.55 } 50% { opacity:1 } 65% { opacity:.55 } 78% { opacity:1; transform:scale(1) }
    92% { opacity:0; transform:scale(.4) } 100% { opacity:0; transform:scale(.3) }
  }
  @keyframes onda { 0% { transform:scale(.6); opacity:.9 } 100% { transform:scale(1.8); opacity:0 } }
  /* mirante: você está a até 40 m; para de sumir e pulsa */
  .wl-ponto.perto { animation: pulso 1s ease-in-out infinite; opacity:1;
                    box-shadow: 0 0 0 4px #FFC83D, 0 0 22px #FFC83D; }
  @keyframes pulso { 0%,100% { transform:scale(1) } 50% { transform:scale(1.25) } }
  .chip.mirante { background:#FFC83D; color:#2A2000; font-weight:700; }
  #hud { position:absolute; top:10px; left:10px; right:10px; z-index:500; display:flex; gap:6px; flex-wrap:wrap;
         pointer-events:none; }
  .chip { background:rgba(20,17,31,.78); color:#fff; padding:5px 10px; border-radius:999px; font-size:12px;
          backdrop-filter: blur(4px); }
  .chip b { color:#FFC83D; }
  #cartao { position:absolute; left:10px; right:10px; bottom:10px; z-index:600; display:none;
            background:__SUPERFICIE__; color:__TINTA__; border-radius:16px; padding:12px 14px;
            box-shadow:0 8px 30px rgba(0,0,0,.35); }
  #cartao h4 { margin:0 0 4px; font-size:16px; }
  #cartao .sub { font-size:13px; opacity:.8; margin-bottom:6px; }
  #cartao .linha { font-size:13px; margin:2px 0; }
  #cartao .botoes { display:flex; gap:6px; margin-top:8px; }
  #cartao a { flex:1; text-align:center; text-decoration:none; padding:12px 4px; border-radius:999px;
              background:__COR__; color:__TINTA_COR__; font-size:14px; font-weight:700; }
  #fechar { position:absolute; top:0; right:0; width:44px; height:44px; border:0; background:none; font-size:22px;
            color:inherit; cursor:pointer; }
  #cartao a:focus-visible, #fechar:focus-visible { outline:3px solid __TINTA__; outline-offset:2px; }
  @media (prefers-reduced-motion: reduce) {
    .wl-personagem, .wl-alcance, .wl-ponto, .wl-ponto::after, .wl-ponto.perto { animation:none !important; opacity:1; }
  }
</style></head>
<body class="__CLASSE__">
<div id="mapa"></div>
<div id="hud" aria-live="polite"></div>
<div id="cartao" role="dialog"><button id="fechar" aria-label="Fechar">×</button>
  <h4 id="c-titulo"></h4><div class="sub" id="c-sub"></div>
  <div class="linha" id="c-pista"></div><div class="linha" id="c-dist"></div><div class="linha" id="c-end"></div><div class="linha" id="c-hora"></div>
  <div class="botoes" id="c-botoes"></div></div>
<script src="__JS__"></script>
<script>
const D = __DADOS__;
const mapa = L.map("mapa", { zoomControl:false, attributionControl:true }).setView([D.lat, D.lon], 16);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            { maxZoom:19, attribution:"© OpenStreetMap" }).addTo(mapa);

const alcance = L.marker([D.lat, D.lon], { interactive:false, icon: L.divIcon({ className:"",
  html:'<div class="wl-alcance"></div>', iconSize:[120,120], iconAnchor:[60,60] }) }).addTo(mapa);
const eu = L.marker([D.lat, D.lon], { zIndexOffset:1000, icon: L.divIcon({ className:"",
  html:'<div class="wl-personagem">' + D.personagem + '</div>', iconSize:[56,63], iconAnchor:[28,60] }) }).addTo(mapa);
let posicao = [D.lat, D.lon];

function km(a, b) {
  const r = 6371, p1 = a[0]*Math.PI/180, p2 = b[0]*Math.PI/180;
  const dp = (b[0]-a[0])*Math.PI/180, dl = (b[1]-a[1])*Math.PI/180;
  const h = Math.sin(dp/2)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
  return 2*r*Math.asin(Math.sqrt(h));
}

// HUD: tema do dia
const hud = document.getElementById("hud");
const chip = document.createElement("div"); chip.className = "chip";
chip.append(D.hoje.emoji + " Tema do dia: ");
const forte = document.createElement("b"); forte.textContent = D.hoje.nome + " ×2"; chip.append(forte);
hud.append(chip);
const chip2 = document.createElement("div"); chip2.className = "chip"; hud.append(chip2);

// Cartão do ponto tocado (só textContent)
const cartao = document.getElementById("cartao");
document.getElementById("fechar").onclick = () => { cartao.style.display = "none"; };
function abrir(p) {
  const t = D.temas[p.tema];
  document.getElementById("c-titulo").textContent = p.turma ? "🟡 " + p.n + " achados da turma por aqui"
                                                             : t.emoji + " " + p.nome;
  document.getElementById("c-sub").textContent = p.turma ? "Mais raros: " + p.raros.join(", ")
                                                         : "Procure " + t.nome.toLowerCase() + " aqui";
  const pista = p.turma ? (p.guardiao ? "🛡️ Guardião da semana: " + p.guardiao : "")
                        : ((D.pistas[p.tipo] || []).length ? "🔎 A turma já achou em lugares assim: "
                                                             + D.pistas[p.tipo].join(", ") : "");
  document.getElementById("c-pista").textContent = pista;
  document.getElementById("c-dist").textContent = "📏 " + km(posicao, [p.lat, p.lon]).toFixed(1).replace(".", ",") + " km";
  document.getElementById("c-end").textContent = p.endereco ? "📍 " + p.endereco : "";
  document.getElementById("c-hora").textContent = p.horario ? "🕒 " + p.horario : "";
  const botoes = document.getElementById("c-botoes"); botoes.replaceChildren();
  const rotas = [["Google Maps", "https://www.google.com/maps/dir/?api=1&destination=" + p.lat + "," + p.lon],
                 ["Waze", "https://waze.com/ul?ll=" + p.lat + "," + p.lon + "&navigate=yes"]];
  for (const [nome, url] of rotas) {
    const a = document.createElement("a"); a.textContent = "🧭 " + nome; a.href = url;
    a.target = "_blank"; a.rel = "noopener"; botoes.append(a);
  }
  cartao.style.display = "block";
}

// Pontos que aparecem, piscam e somem
function ponto(p, turma) {
  const t = D.temas[p.tema], doDia = p.tema === D.hoje.id;
  const tam = turma ? 16 : (doDia ? 30 : 22);
  const el = document.createElement("div");
  el.className = "wl-ponto" + (turma ? " turma" : "");
  el.style.setProperty("--c", t.cor);
  el.style.setProperty("--t", tam + "px");
  el.style.setProperty("--d", p.duracao + "s");
  el.style.setProperty("--atraso", p.atraso + "s");
  if (!turma) { const e = document.createElement("span"); e.className = "wl-emoji"; e.textContent = t.emoji; el.append(e); }
  const m = L.marker([p.lat, p.lon], { icon: L.divIcon({ className:"", html: el, iconSize:[tam, tam],
                                                          iconAnchor:[tam/2, tam/2] }) }).addTo(mapa);
  m.on("click", () => abrir(p));
  if (!turma) lugares.push({ p, el });
}
const lugares = [];
D.pontos.forEach(p => ponto(p, false));
D.manchas.forEach(p => ponto(p, true));

// Mirante: o lugar mais perto, recalculado a cada passo
function atualizarPerto() {
  let melhor = null, dist = Infinity;
  for (const l of lugares) {
    const d = km(posicao, [l.p.lat, l.p.lon]);
    l.el.classList.toggle("perto", d * 1000 <= D.mirante_m);
    if (d < dist) { dist = d; melhor = l.p; }
  }
  chip2.classList.toggle("mirante", !!melhor && dist * 1000 <= D.mirante_m);
  if (!melhor) chip2.textContent = "Nenhum lugar por perto";
  else if (dist * 1000 <= D.mirante_m) chip2.textContent = "📍 Mirante: " + melhor.nome + ". Fotografe aqui: +" + D.mirante_bonus;
  else chip2.textContent = "Mirante mais perto: " + (dist < 1 ? Math.round(dist * 1000) + " m"
                                                              : dist.toFixed(1).replace(".", ",") + " km");
}
atualizarPerto();

// O personagem anda com você (GPS contínuo); sem permissão, fica na posição inicial
if (D.gps_vivo && navigator.geolocation) {
  navigator.geolocation.watchPosition(pos => {
    posicao = [pos.coords.latitude, pos.coords.longitude];
    eu.setLatLng(posicao); alcance.setLatLng(posicao); mapa.panTo(posicao, { animate:true });
    atualizarPerto();
  }, () => {}, { enableHighAccuracy:true, maximumAge:5000, timeout:20000 });
}
</script></body></html>
"""


def _json_seguro(dados) -> str:
    """JSON que não fecha a tag <script> no meio."""
    return json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")


def montar(lat: float, lon: float, pontos: list[dict], manchas: list[dict], hoje, temas, escuro: bool = False,
           cor: str = "#136B4C", gps_vivo: bool = True, semente: int = 0, pistas: dict | None = None,
           leaflet_js: str = LEAFLET_JS, leaflet_css: str = LEAFLET_CSS) -> str:
    """Página HTML do mapa do jogo.

    pontos: lugares do OSM (tema, nome, lat, lon, endereco, horario já legível);
    manchas: descobertas da turma (tema, lat, lon, n, raros e, se houver, guardiao);
    pistas: o que a turma mais achou em cada tipo de lugar (jogo.pistas_por_tipo).
    Duração e atraso do piscar saem de um sorteio com `semente`, para cada ponto ter seu ritmo.
    """
    rng = random.Random(semente)

    def ritmo(do_dia: bool) -> dict:
        duracao = rng.uniform(4, 6) if do_dia else rng.uniform(5.5, 8)
        return {"duracao": round(duracao, 2), "atraso": round(-rng.uniform(0, duracao), 2)}

    dados = {
        "lat": lat, "lon": lon, "gps_vivo": gps_vivo, "mirante_m": MIRANTE_M, "mirante_bonus": MIRANTE,
        "pistas": {str(k): [str(x) for x in v] for k, v in (pistas or {}).items()},
        "personagem": PERSONAGEM_SVG.replace("{cor}", cor),
        "hoje": {"id": hoje.id, "nome": hoje.nome, "emoji": hoje.emoji},
        "temas": {t.id: {"nome": t.nome, "emoji": t.emoji, "cor": t.cor} for t in temas},
        "pontos": [{"tema": p["tema"], "nome": str(p.get("nome") or ""), "lat": float(p["lat"]),
                    "lon": float(p["lon"]), "tipo": str(p.get("tipo") or ""), "endereco": p.get("endereco") or "", "horario": p.get("horario") or "",
                    **ritmo(p["tema"] == hoje.id)} for p in pontos],
        "manchas": [{"tema": m["tema"], "lat": float(m["lat"]), "lon": float(m["lon"]), "n": int(m["n"]),
                     "raros": [str(x) for x in (m.get("raros") or [])], "turma": True,
                     "guardiao": str(m.get("guardiao") or ""),
                     **ritmo(False)} for m in manchas],
    }
    fundo, superficie, tinta = ("#0E1914", "#16251E", "#E4EEE8") if escuro else ("#DDE8DF", "#FFFFFF", "#12241D")
    trocas = {"__CSS__": leaflet_css, "__JS__": leaflet_js, "__FUNDO__": fundo, "__SUPERFICIE__": superficie,
              "__TINTA__": tinta, "__TINTA_COR__": "#06130D" if escuro else "#FFFFFF", "__COR__": cor, "__COR_FRACA__": cor + "40", "__CLASSE__": "escuro" if escuro else "",
              "__DADOS__": _json_seguro(dados)}
    html = PAGINA
    for chave, valor in sorted(trocas.items(), key=lambda kv: -len(kv[0])):  # chave mais longa primeiro
        html = html.replace(chave, valor)
    return html
