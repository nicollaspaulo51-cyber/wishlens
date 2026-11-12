"""WishLens · Início: enviar foto ou usar a câmera.

Rodar localmente:  streamlit run app/Home.py
"""

import html
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from src import armazenamento, localizacao, ui
from src.categorias import CATEGORIAS, Item, faixa_preco, nome_valido, tipo_da_categoria
from src.fotos import ler_metadados, preparar_para_salvar
from src.links import links_para
from src.lugares import buscar_proximos

ui.configurar("Início")

# Cache no app (os módulos de src/ não dependem do Streamlit); poupa os servidores públicos do OSM
lugares_proximos = st.cache_data(ttl=3600, show_spinner=False)(buscar_proximos)
geocodificar = st.cache_data(ttl=86400, show_spinner=False)(localizacao.geocodificar)
bairro_de = st.cache_data(ttl=86400, show_spinner=False)(localizacao.bairro_de)

MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
ICONE = {"comprar": "🛍️", "receita": "🍲", "adotar": "🐶"}
# Para que serve cada local no mapa: rótulo, ícone (Font Awesome 6, já carregado pelo folium) e cor
FINALIDADE = {
    "comprar": ("Comprar", "cart-shopping", "blue"),
    "jogar": ("Jogar", "gamepad", "orange"),
    "consertar": ("Consertar", "screwdriver-wrench", "gray"),
    "adotar": ("Adotar", "paw", "green"),
    "cuidar": ("Veterinário", "stethoscope", "darkgreen"),
    "comer": ("Comer", "utensils", "red"),
}
TITULO_LINKS = {"comprar": "Lojas online", "receita": "Receitas e delivery", "adotar": "Adoção"}

st.title("🔍 WishLens")
st.markdown("##### Aponte para qualquer coisa e descubra onde conseguir.")

aba_camera, aba_upload = st.tabs(["📷 Câmera", "🖼️ Enviar foto"])
with aba_camera:
    foto_camera = st.camera_input("Aponte a câmera", label_visibility="collapsed")
with aba_upload:
    foto_upload = st.file_uploader("Envie uma foto", type=["jpg", "jpeg", "png", "webp"])

arquivo = foto_camera or foto_upload
if not arquivo:
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="wl-card">🛍️ <b>Comprar</b><br><small>lojas perto e online</small></div>', unsafe_allow_html=True)
    c2.markdown('<div class="wl-card">🍲 <b>Comer</b><br><small>receitas e restaurantes</small></div>', unsafe_allow_html=True)
    c3.markdown('<div class="wl-card">🐶 <b>Adotar</b><br><small>abrigos e ONGs</small></div>', unsafe_allow_html=True)
    st.stop()

imagem = Image.open(arquivo)
meta = ler_metadados(imagem)
st.image(preparar_para_salvar(imagem), use_container_width=True)

# ---------- O que é isso? ----------
confianca = None
if MODELO_DISPONIVEL:
    from src.reconhecimento import reconhecer

    with st.spinner("Reconhecendo..."):
        resultados = reconhecer(imagem, top_k=3)
    repetidos = {r.item.nome for r in resultados if [x.item.nome for x in resultados].count(r.item.nome) > 1}
    opcoes = {(f"{r.item.nome} · {r.item.categoria}" if r.item.nome in repetidos else r.item.nome)
              + f" ({r.confianca:.0%})": r for r in resultados}
    opcoes["Outra coisa…"] = None
    escolha = st.radio("O que é isso?", list(opcoes), horizontal=True,
                       help="Confirme a opção certa: isso melhora a qualidade dos dados.")
    item = opcoes[escolha].item if opcoes[escolha] else None
    confianca = opcoes[escolha].confianca if opcoes[escolha] else None
else:
    st.info("Reconhecimento automático ainda não instalado: diga o que é.")
    item = None

if item is None:  # texto livre: qualquer coisa, desde que a pessoa diga a categoria
    c1, c2 = st.columns([2, 1])
    nome = c1.text_input("O que é?", max_chars=60, placeholder="Ex.: garrafa térmica").strip()
    categoria = c2.selectbox("Categoria", CATEGORIAS, index=None, placeholder="Escolha...")
    if not nome or not categoria:
        st.stop()
    if not nome_valido(nome):
        st.warning("Use só letras, números e pontuação simples (sem < > & \" ;).")
        st.stop()
    item = Item(nome, nome.lower(), categoria, tipo_da_categoria(categoria))

st.markdown(
    f'<div class="wl-card"><h3 style="margin:0">{ICONE[item.tipo]} {item.nome.capitalize()}</h3>'
    f'{ui.badge(item.categoria)}{ui.badge(item.tipo)}'
    f'{ui.badge("💰 " + faixa_preco(item))}'
    f'</div>', unsafe_allow_html=True)

if st.button("⭐ Salvar nos meus desejos", type="primary", use_container_width=True):
    cidade = None
    if pos := st.session_state.get("posicao"):
        try:
            cidade = bairro_de(*pos)  # só bairro/cidade; a coordenada exata não é guardada
        except Exception:
            pass
    armazenamento.salvar_desejo(item, confianca, meta["data_hora"], cidade=cidade)
    st.success("Salvo! Veja em **Meus Desejos**.")

# ---------- Onde conseguir ----------
st.markdown(f"#### {TITULO_LINKS[item.tipo]}")
links = links_para(item)
for col, (nome, url) in zip(st.columns(len(links)), links.items()):
    col.link_button(nome, url, use_container_width=True)

st.markdown("#### 📍 Perto de você")
# Ordem: GPS da foto → GPS do navegador (com permissão) → endereço digitado
lat, lon, origem = meta["lat"], meta["lon"], "GPS da foto"
if lat is None:
    gps = get_geolocation()  # o navegador pergunta se a pessoa permite; None até responder
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
    st.session_state.pop("posicao", None)
    st.stop()
st.session_state["posicao"] = (round(lat, 3), round(lon, 3))  # ~100 m: usado só para achar o bairro
st.caption(f"📍 Usando: {origem}")

raio = st.slider("Raio de busca (km)", 1, 10, 3)
if st.button("Buscar lugares próximos", use_container_width=True):
    st.session_state["busca"] = (item, lat, lon, raio)

if st.session_state.get("busca") == (item, lat, lon, raio):  # mantém o mapa após interações
    try:
        with st.spinner("Consultando o OpenStreetMap..."):
            lugares = lugares_proximos(item, lat, lon, raio_m=raio * 1000)
    except Exception as erro:
        st.error(f"Não foi possível consultar o OpenStreetMap agora ({type(erro).__name__}). "
                 "Tente de novo em instantes ou use os links online acima.")
        lugares = None
    if lugares:
        mapa = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap")
        folium.Marker([lat, lon], tooltip="Você", icon=folium.Icon(color="purple", icon="user")).add_to(mapa)
        for l in lugares:
            rotulo, icone, cor = FINALIDADE[l.get("finalidade", "comprar")]
            nome = html.escape(l["nome"])  # nome vem do OSM (editável por qualquer um): nunca HTML cru
            # folium.Icon: o ícone padrão do Leaflet é uma imagem que não carrega no st_folium
            folium.Marker([l["lat"], l["lon"]], tooltip=f'{nome} · {rotulo} · {l["distancia_km"]} km',
                          popup=folium.Popup(f'<b>{nome}</b><br>Para: {rotulo}<br>{l["distancia_km"]} km<br>'
                                             f'<a href="{html.escape(l["mapa"])}" target="_blank">ver no mapa</a>',
                                             max_width=220),
                          icon=folium.Icon(color=cor, icon=icone, prefix="fa")).add_to(mapa)
        presentes = dict.fromkeys(l.get("finalidade", "comprar") for l in lugares)
        st.caption("  ·  ".join(f"{FINALIDADE[f][0]}" for f in presentes) + "  — toque no marcador para ver")
        st_folium(mapa, height=380, use_container_width=True, returned_objects=[])
        df = pd.DataFrame(lugares)
        df["para"] = [FINALIDADE[l.get("finalidade", "comprar")][0] for l in lugares]
        st.dataframe(df[["nome", "para", "distancia_km", "mapa"]], hide_index=True,
                     use_container_width=True,
                     column_config={"mapa": st.column_config.LinkColumn("mapa", display_text="abrir")})
    elif lugares == []:
        st.warning("Nenhum lugar encontrado no mapa aberto (OSM) nesse raio. Use os links online acima.")
