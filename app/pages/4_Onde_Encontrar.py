"""WishLens · Onde encontrar: preço, lojas online e lugares próximos de um achado.

Chega aqui pelo botão "Onde encontrar" depois de uma captura do jogo (o achado vem em
st.session_state["encontrar"]) ou sozinha, com uma foto de qualquer coisa.
"""

import html
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import folium
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from src import armazenamento, localizacao, precos, ui, visao
from src.categorias import CATEGORIAS, Item, nome_valido, rotulo_exibicao, tipo_da_categoria
from src.fotos import ler_metadados, preparar_para_salvar
from src.links import links_para
from src.lugares import buscar_proximos, como_chegar, horario_legivel, lugar_mais_proximo

ui.configurar("Onde encontrar", "🔎")

# Cache no app (os módulos de src/ não dependem do Streamlit); poupa os servidores públicos do OSM
lugares_proximos = st.cache_data(ttl=3600, show_spinner=False)(buscar_proximos)
geocodificar = st.cache_data(ttl=86400, show_spinner=False)(localizacao.geocodificar)
bairro_de = st.cache_data(ttl=86400, show_spinner=False)(localizacao.bairro_de)
estimar_preco = st.cache_data(ttl=6 * 3600, show_spinner=False)(precos.estimar)


def _segredo(nome: str) -> str | None:
    try:
        return st.secrets[nome] or None
    except Exception:  # sem secrets.toml o Streamlit lança erros próprios
        return None


CHAVE_GEMMA = _segredo("GEMINI_API_KEY")
MODELO_GEMMA = _segredo("GEMMA_MODELO") or visao.MODELO_PADRAO


@st.cache_data(ttl=86400, show_spinner=False, max_entries=200)
def identificar_gemma(jpeg: bytes, modelo: str) -> visao.Identificacao:
    """Mesma foto = mesma resposta (economiza a cota gratuita). Erros não ficam em cache."""
    return visao.identificar(jpeg, CHAVE_GEMMA, modelo)


MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
ICONE = {"comprar": "🛍️", "receita": "🍲", "adotar": "🐶"}
# Para que serve cada local no mapa: rótulo, ícone (Font Awesome 6, já carregado pelo folium) e cor
FINALIDADE = {
    "comprar": ("Comprar", "cart-shopping", "blue", "🛍️"),
    "jogar": ("Jogar", "gamepad", "orange", "🎮"),
    "consertar": ("Consertar", "screwdriver-wrench", "gray", "🔧"),
    "adotar": ("Adotar", "paw", "green", "🐾"),
    "cuidar": ("Veterinário", "stethoscope", "darkgreen", "🩺"),
    "comer": ("Comer", "utensils", "red", "🍽️"),
}
TITULO_LINKS = {"comprar": "Lojas online", "receita": "Receitas e delivery", "adotar": "Adoção"}

st.title("🔎 Onde encontrar")
st.markdown("##### Preço, lojas online e lugares perto de você.")

vindo = st.session_state.get("encontrar")  # Item vindo da captura do jogo
if vindo is not None:
    item, confianca, escolhida = vindo, None, None
    meta = {"lat": None, "lon": None, "data_hora": None}
    if st.button("📷 Usar outra foto", help="Esquece o achado do jogo e escolhe outra coisa"):
        st.session_state.pop("encontrar", None)
        st.rerun()
else:
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
    jpeg = preparar_para_salvar(imagem)  # sem EXIF/GPS: é o que vai para a IA e para o banco
    st.image(jpeg, use_container_width=True)

    # ---------- O que é isso? ----------
    # Com GEMINI_API_KEY: Gemma (marca, modelo e preço) como 1ª opção + CLIP abaixo. Sem chave: só o CLIP.
    identificacao, aviso_ia = None, None
    if CHAVE_GEMMA:
        try:
            with st.spinner("Identificando marca e modelo..."):
                identificacao = identificar_gemma(jpeg, MODELO_GEMMA)
        except visao.ErroVisao as erro:
            aviso_ia = str(erro)

    resultados = []
    if MODELO_DISPONIVEL:
        from src.reconhecimento import reconhecer

        with st.spinner("Reconhecendo..."):
            resultados = reconhecer(imagem, top_k=3)

    # rótulo do radio -> (item, confiança, identificação do Gemma ou None)
    opcoes: dict[str, tuple | None] = {}
    if identificacao:
        opcoes[f"✨ {rotulo_exibicao(identificacao.item)}"] = (identificacao.item, identificacao.confianca, identificacao)
    nomes = [r.item.nome for r in resultados]
    for r in resultados[: 2 if identificacao else 3]:
        if identificacao and r.item.nome == identificacao.item.nome:
            continue
        rotulo = rotulo_exibicao(r.item) + (f" · {r.item.categoria}" if nomes.count(r.item.nome) > 1 else "")
        opcoes[f"{rotulo} ({r.confianca:.0%})"] = (r.item, r.confianca, None)

    if aviso_ia:
        st.caption(f"⚠️ IA de marcas indisponível agora ({aviso_ia}). Usando só o reconhecimento básico.")
    item, confianca, escolhida = None, None, None
    if opcoes:
        opcoes["Outra coisa…"] = None
        escolha = st.radio("O que é isso?", list(opcoes), horizontal=True,
                           help="✨ = identificado com marca/modelo pela IA (Gemma). "
                                "Confirme a opção certa: isso melhora a qualidade dos dados.")
        if opcoes[escolha]:
            item, confianca, escolhida = opcoes[escolha]
    else:
        st.info("Reconhecimento automático ainda não instalado: diga o que é.")

    if item is None:  # texto livre: qualquer coisa, desde que a pessoa diga a categoria
        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        nome = c1.text_input("O que é?", max_chars=60, placeholder="Ex.: garrafa térmica").strip()
        marca = c2.text_input("Marca (opcional)", max_chars=40, placeholder="Ex.: Stanley").strip()
        categoria = c3.selectbox("Categoria", CATEGORIAS, index=None, placeholder="Escolha...")
        if not nome or not categoria:
            st.stop()
        if not nome_valido(nome) or (marca and not nome_valido(marca)):
            st.warning("Use só letras, números e pontuação simples (sem < > & \" ;).")
            st.stop()
        item = Item(nome, nome.lower(), categoria, tipo_da_categoria(categoria), marca=marca)

ia = (escolhida.preco_min, escolhida.preco_max) if escolhida else None
with st.spinner("Estimando preço..."):
    preco = estimar_preco(item, ia)

st.markdown(
    f'<div class="wl-card"><h3 style="margin:0">{ICONE[item.tipo]} {rotulo_exibicao(item)}</h3>'
    f'{ui.badge(item.categoria)}{ui.badge(item.tipo)}'
    f'{ui.badge("💰 " + preco.texto)}'
    f'<div class="wl-muted" style="font-size:.8rem">Preço: {preco.fonte}</div>'
    f'</div>', unsafe_allow_html=True)

if st.button("⭐ Salvar nos meus desejos", type="primary", use_container_width=True):
    cidade = None
    if pos := st.session_state.get("posicao"):
        try:
            cidade = bairro_de(*pos)  # só bairro/cidade; a coordenada exata não é guardada
        except Exception:
            pass
    armazenamento.salvar_desejo(item, confianca, meta["data_hora"], cidade=cidade, faixa=preco.texto)
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
    st.session_state.pop("lugar_escolhido", None)

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
            rotulo, icone, cor, _ = FINALIDADE[l.get("finalidade", "comprar")]
            nome = html.escape(l["nome"])  # nome vem do OSM (editável por qualquer um): nunca HTML cru
            # folium.Icon: o ícone padrão do Leaflet é uma imagem que não carrega no st_folium
            folium.Marker([l["lat"], l["lon"]], tooltip=f'{nome} · {rotulo} · {l["distancia_km"]} km',
                          popup=folium.Popup(f'<b>{nome}</b><br>{rotulo} · {l["distancia_km"]} km<br>'
                                             '<small>detalhes abaixo do mapa</small>', max_width=200),
                          icon=folium.Icon(color=cor, icon=icone, prefix="fa")).add_to(mapa)
        presentes = dict.fromkeys(l.get("finalidade", "comprar") for l in lugares)
        st.caption("  ·  ".join(f"{FINALIDADE[f][3]} {FINALIDADE[f][0]}" for f in presentes)
                   + "  — toque num marcador (ou numa linha da tabela) para ver os detalhes")
        # Só o clique volta para o Python: mover/zoom no mapa não recarrega a página
        saida = st_folium(mapa, height=380, use_container_width=True,
                          returned_objects=["last_object_clicked"], key="mapa_lugares")
        cartao = st.container()

        df = pd.DataFrame(lugares)
        df["para"] = [FINALIDADE[l.get("finalidade", "comprar")][0] for l in lugares]
        tabela = st.dataframe(df[["nome", "para", "distancia_km", "endereco"]], hide_index=True,
                              use_container_width=True, on_select="rerun", selection_mode="single-row",
                              key="tabela_lugares",
                              column_config={"distancia_km": st.column_config.NumberColumn("km", format="%.2f"),
                                             "endereco": "endereço"})

        # O último gesto vence: clique no mapa ou linha da tabela
        clique = (saida or {}).get("last_object_clicked")
        if clique and clique != st.session_state.get("_ultimo_clique"):
            st.session_state["_ultimo_clique"] = clique
            st.session_state["lugar_escolhido"] = lugar_mais_proximo(lugares, clique["lat"], clique["lng"])
        linhas = tabela.selection.rows if tabela else []
        if linhas and linhas != st.session_state.get("_ultima_linha"):
            st.session_state["lugar_escolhido"] = lugares[linhas[0]]
        st.session_state["_ultima_linha"] = linhas

        escolhido = st.session_state.get("lugar_escolhido")
        if escolhido in lugares:
            with cartao:
                ui.cartao_lugar(escolhido, FINALIDADE[escolhido.get("finalidade", "comprar")],
                                horario_legivel(escolhido.get("horario")), preco, rotulo_exibicao(item),
                                como_chegar(escolhido["lat"], escolhido["lon"]))
    elif lugares == []:
        st.warning("Nenhum lugar encontrado no mapa aberto (OSM) nesse raio. Use os links online acima.")
