"""WishLens · Jogar: o personagem no mapa, os lugares dos temas piscando, e a câmera para pontuar.

Rodar localmente:  streamlit run app/Home.py
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from PIL import Image
from streamlit_js_eval import get_geolocation

import streamlit.components.v1 as components

from src import armazenamento, jogo, localizacao, mapa_jogo, ui, visao
from src.categorias import nome_valido
from src.fotos import preparar_para_salvar
from src.lugares import buscar_pontos_temas, distancia_km, horario_legivel
from src.temas import POR_ID, TEMAS, tema_do_dia

ui.configurar("Jogar", "🎯")

MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
bairro_de = st.cache_data(ttl=86400, show_spinner=False)(localizacao.bairro_de)
geocodificar = st.cache_data(ttl=86400, show_spinner=False)(localizacao.geocodificar)
pontos_temas = st.cache_data(ttl=3600, show_spinner=False)(buscar_pontos_temas)


def _segredo(nome: str) -> str | None:
    try:
        return st.secrets[nome] or None
    except Exception:  # sem secrets.toml o Streamlit lança erros próprios
        return None


CHAVE_GEMMA = _segredo("GEMINI_API_KEY")
MODELO_GEMMA = _segredo("GEMMA_MODELO") or visao.MODELO_PADRAO


@st.cache_data(ttl=86400, show_spinner=False, max_entries=300)
def julgar_gemma(jpeg: bytes, modelo: str) -> visao.Captura:
    """Mesma foto = mesma resposta (economiza a cota gratuita). Erros não ficam em cache."""
    return visao.identificar_captura(jpeg, CHAVE_GEMMA, modelo)


# Posição: GPS do navegador (pedido logo ao abrir); sem ele, um endereço digitado
_gps = get_geolocation()
if _gps and "coords" in _gps:
    st.session_state["gps"] = (_gps["coords"]["latitude"], _gps["coords"]["longitude"])

hoje = tema_do_dia()
eu = armazenamento.usuario_atual()
pontuadas = jogo.calcular_pontos(armazenamento.capturas())
ranking = jogo.podio(pontuadas, "hoje")
meus = ranking[ranking["usuario"] == eu]

# ---------- Barra compacta (uma linha também no celular) ----------
pontos_hoje = int(meus["pontos"].iloc[0]) if not meus.empty else 0
posicao_hoje = f'{int(meus["posicao"].iloc[0])}º' if not meus.empty else "—"
st.markdown(
    f'<div class="wl-barra"><div><div class="wl-brand">🎯 WishLens</div>'
    f'<div class="wl-muted" style="font-size:.8rem">Tema do dia: {hoje.emoji} <b>{hoje.nome}</b> ×2</div></div>'
    f'<div class="wl-placar"><span>⭐ <b>{pontos_hoje}</b> pts</span><span>🏆 <b>{posicao_hoje}</b></span></div></div>',
    unsafe_allow_html=True)

# ---------- Mapa com o personagem ----------
posicao = st.session_state.get("gps")
if posicao is None:
    endereco = st.text_input("Sem GPS: onde você está?", placeholder="Ex.: Jardim da Penha, Vitória",
                             help="Permita a localização no navegador para o personagem andar com você.")
    if endereco:
        try:
            achado_end = geocodificar(endereco)
        except Exception as erro:
            achado_end = None
            st.error(f"Não foi possível consultar o endereço agora ({type(erro).__name__}).")
        if achado_end:
            posicao = achado_end[:2]
        else:
            st.warning("Endereço não encontrado. Tente incluir a cidade.")

escolhidos = st.pills("Temas no mapa", [t.id for t in TEMAS], selection_mode="multi",
                      default=[t.id for t in TEMAS], format_func=lambda i: f"{POR_ID[i].emoji} {POR_ID[i].nome}",
                      label_visibility="collapsed") or []
if posicao is not None:
    lat, lon = posicao
    centro = (round(lat, 3), round(lon, 3))  # ~100 m: a busca no OSM fica em cache enquanto você anda perto
    if st.session_state.get("_centro_mapa") is None or st.button("🔄 Atualizar lugares", help="Busca de novo a partir de onde você está"):
        st.session_state["_centro_mapa"] = centro
    centro = st.session_state["_centro_mapa"]
    temas_mapa = [POR_ID[i] for i in escolhidos]
    pontos = []
    if temas_mapa:
        try:
            with st.spinner("Procurando lugares por perto..."):
                pontos = pontos_temas(temas_mapa, centro[0], centro[1], raio_m=1500, por_tema=12)
        except Exception as erro:
            st.caption(f"⚠️ OpenStreetMap fora do ar agora ({erro}). O mapa mostra só o personagem.")
    for p in pontos:
        p["horario"] = horario_legivel(p.get("horario"))
    manchas = []
    for r in armazenamento.manchas().itertuples():
        if r.tema in escolhidos:
            la, lo = jogo.centro_celula(r.celula)
            if distancia_km(lat, lon, la, lo) <= 2:
                manchas.append({"tema": r.tema, "lat": la, "lon": lo, "n": int(r.n), "raros": list(r.achados or [])})
    html = mapa_jogo.montar(lat, lon, pontos, manchas, hoje, TEMAS, escuro=ui.tema() == "escuro",
                            cor=ui.cores()["accent"], semente=hash(centro) % 10_000)
    components.html(html, height=480)
else:
    st.info("📍 Permita a localização (ou digite onde você está) para ver o mapa com o seu personagem.")

# ---------- Câmera ----------
if st.button("📷 Fotografar", type="primary", use_container_width=True):
    st.session_state["camera_aberta"] = True
foto = None
if st.session_state.get("camera_aberta"):
    foto = st.camera_input("Fotografe algo de um dos temas",
                           help="Só vale foto tirada agora pela câmera, de algo real na sua frente.")
if not foto:
    st.caption("Regras: base 10 · +10 se é novo pra você · até +20 pela raridade (quem acha primeiro ganha mais) "
               "· tema do dia ×2. Foto repetida, de tela ou fora dos temas vale 0.")
    st.stop()

# Cada foto é julgada e salva uma vez só (o Streamlit roda a página de novo a cada clique)
dados = foto.getvalue()
id_foto = hashlib.sha256(dados).hexdigest()
feita = st.session_state.get("ultima_captura")

if not feita or feita["id"] != id_foto:
    imagem = Image.open(foto)
    jpeg = preparar_para_salvar(imagem)  # sem EXIF/GPS: é o que vai para a IA
    # Dois juízes em toda foto: Gemma (se houver chave) e CLIP (se instalado). O que cada um disse fica gravado.
    captura, aviso, clip = None, None, None
    if CHAVE_GEMMA:
        try:
            with st.spinner("O juiz está olhando sua foto..."):
                captura = julgar_gemma(jpeg, MODELO_GEMMA)
        except visao.ErroVisao as erro:
            aviso = str(erro)
    if MODELO_DISPONIVEL:
        from src.reconhecimento import julgar_clip

        with st.spinner("O segundo juiz (CLIP) está conferindo..."):
            clip = julgar_clip(imagem)
    if aviso:
        st.caption(f"⚠️ Juiz com IA indisponível agora ({aviso}). Usando só o CLIP.")
    juiz = ("gemma+clip" if clip else "gemma") if captura else ("clip" if clip else "manual")
    if captura is None and clip:  # sem Gemma: o CLIP decide sozinho (achado genérico)
        captura = visao.Captura(clip["tema"], clip["achado"], clip["foto_real"], clip["confianca"])

    if captura is None:  # protótipo sem nenhum modelo: a pessoa diz o que é
        st.info("Reconhecimento automático não instalado: diga o que você fotografou.")
        c1, c2 = st.columns([1, 2])
        tema_id = c1.selectbox("Tema", [t.id for t in TEMAS], format_func=lambda i: POR_ID[i].nome)
        achado = c2.text_input("O que é?", max_chars=60, placeholder=POR_ID[tema_id].achado[:40]).strip()
        if not achado or not st.button("Valer!", type="primary"):
            st.stop()
        if not nome_valido(achado):
            st.warning("Use só letras, números e pontuação simples.")
            st.stop()
        captura = visao.Captura(tema_id, achado, True, None)

    # Localização aproximada (opcional): bairro + quadrado de ~500 m para o mapa da turma
    cidade = celula = None
    if gps := st.session_state.get("gps"):
        lat, lon = gps
        celula = jogo.celula(lat, lon)
        try:
            cidade = bairro_de(round(lat, 3), round(lon, 3))
        except Exception:
            pass

    juizes = {"juiz": juiz, "clip_tema": clip["tema"] if clip else None,
              "clip_foto_real": clip["foto_real"] if clip else None,
              "clip_prob_tema": round(clip["probs"].get(captura.tema, 0.0), 4) if clip and captura.tema else None,
              "clip_prob_tela": round(clip["probs"].get("tela", 0.0), 4) if clip else None,
              "clip_rank_tema": jogo.posicao(clip["probs"], captura.tema) if clip and captura.tema else None}
    h = jogo.hash_foto(imagem)
    historico = armazenamento.capturas()
    nova = {"usuario": eu, "criado_em": jogo.agora_naive(), "tema": captura.tema or "nenhum",
            "achado": captura.achado, "foto_real": captura.foto_real, "foto_hash": h, **juizes}
    resultado = jogo.pontuar_nova(historico, nova)
    vezes = jogo.vezes_achado(jogo.calcular_pontos(historico), captura.tema or "", captura.achado)
    id_captura = armazenamento.salvar_captura(captura.tema, captura.achado, captura.confianca,
                                              captura.foto_real, h, cidade, celula, **juizes)
    feita = {"id": id_foto, "captura": captura, "resultado": resultado, "vezes": vezes,
             "juizes": juizes, "id_captura": id_captura, "contestada": None}
    st.session_state["ultima_captura"] = feita

captura, resultado = feita["captura"], feita["resultado"]
tema = POR_ID.get(captura.tema or "")
linha_juizes = ui.linha_juizes(feita["juizes"], captura.tema)
if tema:
    ui.cartao_pontos(resultado, tema, captura.achado or tema.generico, feita["vezes"], linha_juizes)
else:
    ui.cartao_pontos(resultado, TEMAS[0], "", 0, linha_juizes)

# Contestar: o juiz errou o tema? A pessoa diz o que era. Não dá pontos (sem trapaça), mas fica gravado
# e aparece na página Avaliação para melhorar o identificador.
motivo = str(resultado.get("motivo") or "")
if not resultado.get("aceita") and ("nenhum tema" in motivo or "discordaram" in motivo):
    if feita["contestada"]:
        st.caption(f"✅ Obrigado! Você disse que era: {POR_ID[feita['contestada']].nome}. "
                   "Isso ajuda a melhorar o identificador.")
    else:
        c1, c2 = st.columns([2, 1])
        era = c1.selectbox("O juiz errou? Era…", [t.id for t in TEMAS], index=None, placeholder="Escolha o tema",
                           format_func=lambda i: f"{POR_ID[i].emoji} {POR_ID[i].nome}")
        if c2.button("Contestar", use_container_width=True, disabled=era is None):
            armazenamento.contestar(feita["id_captura"], era)
            feita["contestada"] = era
            st.rerun()

ranking = jogo.podio(jogo.calcular_pontos(armazenamento.capturas()), "hoje")
pos = jogo.posicao_de(ranking, eu)
if pos:
    total = int(ranking.loc[ranking["usuario"] == eu, "pontos"].iloc[0])
    st.markdown(f"**{pos}º lugar hoje** com {total} pontos.")

if st.button("🏆 Ver pódio", use_container_width=True):
    st.switch_page("pages/1_Pódio.py")
st.caption("Tire outra foto acima para continuar jogando.")
