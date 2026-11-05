"""WishLens · Início: enviar foto ou usar a câmera.

Rodar localmente:  streamlit run app/Home.py
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from PIL import Image

from src import armazenamento, ui
from src.categorias import FAIXA_PRECO, ITENS
from src.fotos import ler_metadados, preparar_para_salvar
from src.links import links_para
from src.lugares import buscar_proximos

ui.configurar("Início")

MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
ICONE = {"comprar": "🛍️", "receita": "🍲", "adotar": "🐶"}
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
    c1.markdown('<div class="wl-card">🛍️ <b>Comprar</b><br><small>lojas perto de você e online</small></div>', unsafe_allow_html=True)
    c2.markdown('<div class="wl-card">🍲 <b>Comer</b><br><small>receitas, restaurantes e delivery</small></div>', unsafe_allow_html=True)
    c3.markdown('<div class="wl-card">🐶 <b>Adotar</b><br><small>abrigos e ONGs próximos</small></div>', unsafe_allow_html=True)
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
    opcoes = {f"{r.item.nome} ({r.confianca:.0%})": r for r in resultados}
    opcoes["Outra coisa…"] = None
    escolha = st.radio("O que é isso?", list(opcoes), horizontal=True,
                       help="Confirme a opção certa: isso melhora a qualidade dos dados.")
    if opcoes[escolha]:
        item, confianca = opcoes[escolha].item, opcoes[escolha].confianca
    else:
        item = st.selectbox("Escolha o item", ITENS, format_func=lambda i: f"{ICONE[i.tipo]} {i.nome}")
else:
    st.info("Reconhecimento automático ainda não instalado: escolha o item manualmente.")
    item = st.selectbox("O que é isso?", ITENS, format_func=lambda i: f"{ICONE[i.tipo]} {i.nome}")

st.markdown(
    f'<div class="wl-card"><h3 style="margin:0">{ICONE[item.tipo]} {item.nome.capitalize()}</h3>'
    f'{ui.badge(item.categoria)}{ui.badge(item.tipo)}'
    f'{ui.badge("💰 " + FAIXA_PRECO[item.categoria])}'
    f'</div>', unsafe_allow_html=True)

if st.button("⭐ Salvar nos meus desejos", type="primary", use_container_width=True):
    armazenamento.salvar_desejo(item, confianca, meta["data_hora"], cidade=None)
    st.success("Salvo! Veja em **Meus Desejos**.")

# ---------- Onde conseguir ----------
st.markdown(f"#### {TITULO_LINKS[item.tipo]}")
links = links_para(item)
for col, (nome, url) in zip(st.columns(len(links)), links.items()):
    col.link_button(nome, url, use_container_width=True)

st.markdown("#### 📍 Perto de você")
lat, lon = meta["lat"], meta["lon"]
if lat is None:
    st.caption("A foto não tem localização. Informe a posição (padrão: centro de Vitória - ES).")
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitude", value=-20.3155, format="%.4f")
    lon = c2.number_input("Longitude", value=-40.3128, format="%.4f")

raio = st.slider("Raio de busca (km)", 1, 10, 3)
if st.button("Buscar lugares próximos", use_container_width=True):
    try:
        with st.spinner("Consultando o OpenStreetMap..."):
            lugares = buscar_proximos(item, lat, lon, raio_m=raio * 1000)
    except Exception as erro:
        st.error(f"Não foi possível consultar o OpenStreetMap agora ({type(erro).__name__}).")
        lugares = None
    if lugares:
        df = pd.DataFrame(lugares)
        st.map(df, latitude="lat", longitude="lon")
        st.dataframe(df[["nome", "tipo", "distancia_km", "mapa"]], hide_index=True,
                     use_container_width=True,
                     column_config={"mapa": st.column_config.LinkColumn("mapa", display_text="abrir")})
    elif lugares == []:
        st.warning("Nenhum lugar encontrado no mapa aberto (OSM) nesse raio. Use os links online acima.")
