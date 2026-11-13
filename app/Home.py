"""WishLens · Jogar: fotografe coisas reais dos temas, ganhe pontos e suba no pódio.

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

from src import armazenamento, jogo, localizacao, ui, visao
from src.categorias import nome_valido
from src.fotos import preparar_para_salvar
from src.temas import POR_ID, TEMAS, item_do_achado, tema_do_dia

ui.configurar("Jogar", "🎯")

MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
bairro_de = st.cache_data(ttl=86400, show_spinner=False)(localizacao.bairro_de)


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


# Pede a localização logo ao abrir: quando a foto chegar, ela já está pronta (o navegador demora a responder)
_gps = get_geolocation()
if _gps and "coords" in _gps:
    st.session_state["gps"] = (_gps["coords"]["latitude"], _gps["coords"]["longitude"])

hoje = tema_do_dia()
st.title("🎯 WishLens")
st.markdown("##### Fotografe coisas reais, ganhe pontos e suba no pódio.")
ui.faixa_tema_do_dia(hoje, TEMAS)

foto = st.camera_input("Fotografe algo de um dos temas",
                       help="Só vale foto tirada agora pela câmera, de algo real na sua frente.")

eu = armazenamento.usuario_atual()
if not foto:
    pontuadas = jogo.calcular_pontos(armazenamento.capturas())
    ranking = jogo.podio(pontuadas, "hoje")
    meus = ranking[ranking["usuario"] == eu]
    c1, c2, c3 = st.columns(3)
    c1.metric("Seus pontos hoje", int(meus["pontos"].iloc[0]) if not meus.empty else 0)
    c2.metric("Sua posição hoje", f'{int(meus["posicao"].iloc[0])}º' if not meus.empty else "—")
    c3.metric("Jogadores hoje", len(ranking))
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
        captura = visao.Captura(clip["tema"], POR_ID[clip["tema"]].generico if clip["tema"] else "",
                                clip["foto_real"], clip["confianca"])

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
              "clip_prob_tela": round(clip["probs"].get("tela", 0.0), 4) if clip else None}
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

pontuadas = jogo.calcular_pontos(armazenamento.capturas())
ranking = jogo.podio(pontuadas, "hoje")
pos = jogo.posicao_de(ranking, eu)
if pos:
    total = int(ranking.loc[ranking["usuario"] == eu, "pontos"].iloc[0])
    st.markdown(f"**{pos}º lugar hoje** com {total} pontos.")

c1, c2 = st.columns(2)
if c1.button("🏆 Ver pódio", use_container_width=True):
    st.switch_page("pages/2_Pódio.py")
item = item_do_achado(tema, captura.achado) if tema and resultado.get("aceita") else None
if item and c2.button("🔎 Onde encontrar", use_container_width=True):
    st.session_state["encontrar"] = item
    st.switch_page("pages/4_Onde_Encontrar.py")
elif tema and not item and resultado.get("aceita") and c2.button("🗺️ Onde ver mais", use_container_width=True):
    st.switch_page("pages/1_Explorar.py")
st.caption("Tire outra foto acima para continuar jogando.")
