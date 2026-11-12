"""WishLens · Explorar: mapa com os lugares onde procurar cada tema, piscando.

Os pontos que piscam vêm do OpenStreetMap (parques para pássaros e plantas, estacionamentos para
carros...) e das descobertas da turma (por quadrado de ~500 m, nunca a coordenada exata).
O tema do dia pisca mais forte. O mapa é só um guia: estar no lugar não dá ponto.
"""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from src import armazenamento, jogo, localizacao, ui
from src.lugares import buscar_pontos_temas, como_chegar, distancia_km, horario_legivel, lugar_mais_proximo
from src.temas import POR_ID, TEMAS, tema_do_dia

ui.configurar("Explorar", "🗺️")

pontos_temas = st.cache_data(ttl=3600, show_spinner=False)(buscar_pontos_temas)
geocodificar = st.cache_data(ttl=86400, show_spinner=False)(localizacao.geocodificar)

# Cor de cada tema (legível no mapa claro do OSM)
COR = {"carros": "#E5484D", "plantas": "#30A46C", "passaros": "#0091FF", "pets": "#F76B15", "pecas": "#8E4EC6"}
CSS = """
<style>
.wl-pulso { width:16px; height:16px; border-radius:50%; background:var(--c); position:relative;
            box-shadow:0 0 0 2px #fff; }
.wl-pulso::after { content:""; position:absolute; inset:0; border-radius:50%; background:var(--c);
                   animation: wl-pulsar 1.8s ease-out infinite; }
.wl-pulso.forte { width:22px; height:22px; }
.wl-pulso.forte::after { animation-duration:1.1s; }
.wl-pulso.fraco { opacity:.75; }
.wl-pulso.fraco::after { animation-duration:2.8s; }
.wl-pulso.turma { background:#FFC53D; box-shadow:0 0 0 2px #fff, 0 0 0 4px var(--c); }
@keyframes wl-pulsar { 0% { transform:scale(1); opacity:.7; } 100% { transform:scale(3.2); opacity:0; } }
@media (prefers-reduced-motion: reduce) { .wl-pulso::after { animation:none; } }
</style>
"""

hoje = tema_do_dia()
st.title("🗺️ Explorar")
st.markdown(f"Os pontos que piscam são lugares bons para procurar. **{hoje.emoji} {hoje.nome}** "
            "(tema do dia) pisca mais forte. 🟡 = onde a turma já achou coisas.")

# ---------- Onde você está ----------
lat = lon = None
origem = ""
gps = get_geolocation()
if gps and "coords" in gps:
    lat, lon, origem = gps["coords"]["latitude"], gps["coords"]["longitude"], "GPS do aparelho"
if lat is None:
    st.caption("Sem GPS (ou permissão negada): digite um endereço, bairro ou cidade.")
    endereco = st.text_input("Endereço", placeholder="Ex.: Jardim da Penha, Vitória")
    if endereco:
        try:
            achado = geocodificar(endereco)
        except Exception as erro:
            achado = None
            st.error(f"Não foi possível consultar o endereço agora ({type(erro).__name__}).")
        if achado:
            lat, lon, origem = achado
        else:
            st.warning("Endereço não encontrado no OpenStreetMap. Tente incluir a cidade.")
if lat is None:
    st.stop()
st.caption(f"📍 Usando: {origem}")

c1, c2 = st.columns([2, 1])
escolhidos = c1.multiselect("Temas", [t.id for t in TEMAS], default=[t.id for t in TEMAS],
                            format_func=lambda i: f"{POR_ID[i].emoji} {POR_ID[i].nome}")
raio = c2.slider("Raio (km)", 1, 5, 2)
temas = [POR_ID[i] for i in escolhidos]
if not temas:
    st.stop()

try:
    with st.spinner("Procurando lugares no OpenStreetMap..."):
        pontos = pontos_temas(temas, round(lat, 4), round(lon, 4), raio_m=raio * 1000)
except Exception as erro:
    st.error(f"Não foi possível consultar o OpenStreetMap agora ({erro}). Tente de novo em instantes.")
    pontos = []

# ---------- Descobertas da turma (por quadrado de ~500 m, sem dizer quem) ----------
manchas = []
for r in armazenamento.manchas().itertuples():
    if r.tema not in escolhidos:
        continue
    la, lo = jogo.centro_celula(r.celula)
    if distancia_km(lat, lon, la, lo) <= raio + 0.5:
        manchas.append({"lat": la, "lon": lo, "tema": r.tema, "n": int(r.n), "raros": list(r.achados or [])})

# ---------- Mapa ----------
mapa = folium.Map(location=[lat, lon], zoom_start=15 if raio <= 2 else 14, tiles="OpenStreetMap")
mapa.get_root().header.add_child(folium.Element(CSS))
folium.Marker([lat, lon], tooltip="Você", icon=folium.Icon(color="purple", icon="user")).add_to(mapa)
for p in pontos:
    t = POR_ID[p["tema"]]
    forca = "forte" if t.id == hoje.id else "fraco"
    tamanho = 22 if forca == "forte" else 16
    folium.Marker(
        [p["lat"], p["lon"]], tooltip=f'{t.emoji} {html.escape(p["nome"])} · {p["distancia_km"]} km',
        icon=folium.DivIcon(html=f'<div class="wl-pulso {forca}" style="--c:{COR[t.id]}"></div>',
                            icon_size=(tamanho, tamanho), icon_anchor=(tamanho // 2, tamanho // 2)),
    ).add_to(mapa)
for m in manchas:
    t = POR_ID[m["tema"]]
    texto = ", ".join(html.escape(a) for a in m["raros"])
    folium.Marker(
        [m["lat"], m["lon"]], tooltip=f'🟡 {m["n"]} achados da turma aqui: {texto}',
        icon=folium.DivIcon(html=f'<div class="wl-pulso turma" style="--c:{COR[t.id]}"></div>',
                            icon_size=(16, 16), icon_anchor=(8, 8)),
    ).add_to(mapa)

legenda = " ".join(f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
                   f'background:{COR[t.id]};margin:0 .25rem 0 .6rem"></span>{t.emoji} {t.nome}' for t in temas)
st.markdown(f'<div class="wl-muted" style="font-size:.85rem">{legenda}</div>', unsafe_allow_html=True)
saida = st_folium(mapa, height=430, use_container_width=True,
                  returned_objects=["last_object_clicked"], key="mapa_explorar")

# ---------- Cartão do ponto clicado ----------
clique = (saida or {}).get("last_object_clicked")
if clique:
    p = lugar_mais_proximo(pontos, clique["lat"], clique["lng"])
    m = lugar_mais_proximo(manchas, clique["lat"], clique["lng"]) if not p else None
    if p:
        t = POR_ID[p["tema"]]
        ui.cartao_lugar(p, (f"Procurar {t.nome.lower()}", "", "", t.emoji), horario_legivel(p.get("horario")),
                        None, f"o tema {t.nome}", como_chegar(p["lat"], p["lon"]))
    elif m:
        t = POR_ID[m["tema"]]
        st.markdown(
            f'<div class="wl-card"><h3 style="margin:0">🟡 {m["n"]} achados da turma por aqui</h3>'
            f'<div class="wl-muted">Mais raros: {", ".join(html.escape(a) for a in m["raros"])}</div></div>',
            unsafe_allow_html=True)
else:
    st.caption("Toque num ponto para ver o que procurar e como chegar.")

if not pontos and not manchas:
    st.info("Nada encontrado nesse raio. Aumente o raio ou escolha outros temas.")
