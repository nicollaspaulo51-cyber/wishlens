"""WishLens — página principal: enviar foto ou usar a câmera.

Rodar localmente:  streamlit run app/Home.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from PIL import Image

from src.fotos import ler_metadados, preparar_para_salvar
from src.links import links_para
from src.lugares import buscar_proximos
from src.reconhecimento import reconhecer

st.set_page_config(page_title="WishLens", page_icon="🔍", layout="centered")

st.title("🔍 WishLens")
st.caption("Point. Snap. Want. Aponte para qualquer coisa e descubra onde conseguir.")

aba_camera, aba_upload = st.tabs(["📷 Câmera", "🖼️ Enviar foto"])
with aba_camera:
    foto_camera = st.camera_input("Aponte a câmera")
with aba_upload:
    foto_upload = st.file_uploader("Envie uma foto", type=["jpg", "jpeg", "png", "webp"])

arquivo = foto_camera or foto_upload
if not arquivo:
    st.info("Tire uma foto ou envie uma imagem para começar.")
    st.stop()

imagem = Image.open(arquivo)
meta = ler_metadados(imagem)
st.image(preparar_para_salvar(imagem), use_container_width=True)

with st.spinner("Reconhecendo..."):
    resultados = reconhecer(imagem, top_k=3)

opcoes = {f"{r.item.nome} ({r.confianca:.0%})": r for r in resultados}
escolha = st.radio("O que é isso?", list(opcoes), horizontal=True,
                   help="Confirme a opção certa: isso melhora a qualidade dos dados.")
r = opcoes[escolha]
item = r.item

icone = {"comprar": "🛍️", "receita": "🍲", "adotar": "🐶"}[item.tipo]
st.subheader(f"{icone} {item.nome.capitalize()}")
st.write(f"**Categoria:** {item.categoria} · **Faixa de preço:** {r.faixa_preco}")

titulo_links = {"comprar": "Lojas online", "receita": "Receitas e delivery", "adotar": "Adoção"}[item.tipo]
st.markdown(f"#### {titulo_links}")
for nome, url in links_para(item).items():
    st.link_button(nome, url)

st.markdown("#### 📍 Lugares próximos")
lat, lon = meta["lat"], meta["lon"]
if lat is None:
    st.caption("A foto não tem localização. Informe a posição (ex.: centro de Vitória - ES):")
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitude", value=-20.3155, format="%.4f")
    lon = c2.number_input("Longitude", value=-40.3128, format="%.4f")

raio = st.slider("Raio de busca (km)", 1, 10, 3)
if st.button("Buscar lugares próximos"):
    try:
        lugares = buscar_proximos(item, lat, lon, raio_m=raio * 1000)
    except Exception as erro:  # rede/Overpass fora do ar
        st.error(f"Não foi possível consultar o OpenStreetMap: {erro}")
        lugares = []
    if lugares:
        df = pd.DataFrame(lugares)
        st.map(df, latitude="lat", longitude="lon")
        st.dataframe(df[["nome", "tipo", "distancia_km", "mapa"]], hide_index=True,
                     column_config={"mapa": st.column_config.LinkColumn("mapa")})
    else:
        st.warning("Nenhum lugar encontrado no mapa aberto (OSM) nesse raio. Use os links online acima.")

# TODO (semana 2): salvar o desejo no Supabase (src/banco.py) com login do usuário.
