"""WishLens · Jogar: o personagem no mapa, os lugares dos temas piscando, e a câmera para pontuar.

Rodar localmente:  streamlit run app/Home.py
"""

import hashlib
import importlib.util
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from PIL import Image
from streamlit_js_eval import get_geolocation

import streamlit.components.v1 as components
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from src import armazenamento, clima, jogo, localizacao, mapa_jogo, ui, visao
from src.categorias import nome_valido
from src.fotos import preparar_para_salvar
from src.lugares import buscar_pontos_temas, distancia_km, horario_legivel
from src.temas import POR_ID, TEMAS, tema_do_dia

ui.configurar("Jogar", "🎯")

MODELO_DISPONIVEL = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))
bairro_de = st.cache_data(ttl=86400, show_spinner=False)(localizacao.bairro_de)
geocodificar = st.cache_data(ttl=86400, show_spinner=False)(localizacao.geocodificar)
pontos_temas = st.cache_data(ttl=3600, show_spinner=False)(buscar_pontos_temas)
clima_agora = st.cache_data(ttl=1800, show_spinner=False)(clima.agora)
if MODELO_DISPONIVEL:
    from src.reconhecimento import aquecer, julgar_clip

    aquecer()  # o CLIP carrega em segundo plano enquanto a pessoa anda: a 1ª foto não espera ~12 s


def _em_paralelo(fila: ThreadPoolExecutor, funcao, *args):
    """Roda numa thread com o contexto do Streamlit (o st.cache_data precisa dele)."""
    ctx = get_script_run_ctx()

    def rodar():
        add_script_run_ctx(threading.current_thread(), ctx)
        return funcao(*args)
    return fila.submit(rodar)


def _segredo(nome: str) -> str | None:
    try:
        return st.secrets[nome] or None
    except Exception:  # sem secrets.toml o Streamlit lança erros próprios
        return None


VISAO_URL = _segredo("VISAO_URL")
VISAO_CHAVE = _segredo("VISAO_CHAVE")
VISAO_MODELO = _segredo("VISAO_MODELO") or visao.MODELO_PADRAO


@st.cache_data(ttl=86400, show_spinner=False, max_entries=300)
def julgar_ia(jpeg: bytes, modelo: str) -> visao.Captura:
    """Mesma foto = mesma resposta (economiza cota e tempo). Erros não ficam em cache."""
    return visao.identificar_captura(jpeg, VISAO_URL, modelo, VISAO_CHAVE)


# Posição: GPS do navegador (pedido logo ao abrir); sem ele, um endereço digitado
_gps = get_geolocation()
if _gps and "coords" in _gps:
    st.session_state["gps"] = (_gps["coords"]["latitude"], _gps["coords"]["longitude"])

hoje = tema_do_dia()
eu = armazenamento.usuario_atual()


# ---------- Placar ao vivo: se atualiza sozinho a cada 30 s (pontos da turma, meta, desafios) ----------
@st.fragment(run_every="30s")
def placar_ao_vivo():
    pontuadas = jogo.calcular_pontos(armazenamento.capturas())
    ranking = jogo.podio(pontuadas, "hoje")
    meus = ranking[ranking["usuario"] == eu]
    pontos_hoje = int(meus["pontos"].iloc[0]) if not meus.empty else 0
    posicao = int(meus["posicao"].iloc[0]) if not meus.empty else None
    st.markdown(
        f'<div class="wl-barra"><div class="wl-brand">WishLens</div>'
        f'<div class="wl-placar"><span><b>{pontos_hoje}</b> pontos hoje</span>'
        f'<span aria-label="sua posição hoje"><b>{f"{posicao}º" if posicao else "—"}</b> lugar</span></div></div>'
        + ui.selo_tema_do_dia(hoje)
        + ui.painel_do_dia(jogo.estado_do_dia(pontuadas, eu), jogo.corrente_atual(pontuadas, eu),
                           jogo.meta_da_turma(pontuadas)), unsafe_allow_html=True)
    antes = st.session_state.get("_posicao_antes")
    if antes and posicao and posicao < antes:
        st.toast(f"Você subiu para {posicao}º lugar hoje", icon=":material/trending_up:")
    elif antes and posicao and posicao > antes:
        st.toast(f"Alguém passou você: agora {posicao}º lugar", icon=":material/trending_down:")
    st.session_state["_posicao_antes"] = posicao


placar_ao_vivo()
# A câmera aparece aqui, acima do mapa. O código dela fica depois: precisa dos lugares do mapa (mirante).
area_foto = st.container()
pontuadas = jogo.calcular_pontos(armazenamento.capturas())

# ---------- Mapa com o personagem ----------
posicao = st.session_state.get("gps")
if posicao is None:
    st.caption("Permita a localização no navegador para ver o mapa com o seu personagem.")
    with st.popover("Sem GPS? Diga onde você está", icon=":material/location_on:", use_container_width=True):
        endereco = st.text_input("Bairro e cidade", placeholder="Ex.: Jardim da Penha, Vitória")
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

if posicao is not None:
    escolhidos = st.pills("Mostrar no mapa", [t.id for t in TEMAS], selection_mode="multi",
                          default=[t.id for t in TEMAS],
                          format_func=lambda i: f"{POR_ID[i].emoji} {POR_ID[i].nome}") or []
    lat, lon = posicao
    centro = (round(lat, 3), round(lon, 3))  # ~100 m: a busca no OSM fica em cache enquanto você anda perto
    if st.session_state.get("_centro_mapa") is None or st.button("Atualizar lugares", icon=":material/refresh:", help="Busca de novo a partir de onde você está"):
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
    st.session_state["_lugares"] = pontos  # para saber, na hora da foto, se você está num mirante
    g = armazenamento.guardioes()
    guardiao = dict(zip(g["celula"], g["usuario"]))
    manchas = []
    for r in armazenamento.manchas().itertuples():
        if r.tema in escolhidos:
            la, lo = jogo.centro_celula(r.celula)
            if distancia_km(lat, lon, la, lo) <= 2:
                manchas.append({"tema": r.tema, "lat": la, "lon": lo, "n": int(r.n), "raros": list(r.achados or []),
                                "guardiao": ui.nome_publico(str(guardiao.get(r.celula) or ""))})
    html = mapa_jogo.montar(lat, lon, pontos, manchas, hoje, TEMAS, escuro=ui.tema() == "escuro",
                            cor=ui.cores()["accent"], semente=hash(centro) % 10_000,
                            pistas=jogo.pistas_por_tipo(pontuadas))
    components.html(html, height=480)

# ---------- Câmera (desenhada em area_foto, acima do mapa) ----------
with area_foto:
    if ui.precisa_entrar():
        ui.entrar_na_pagina()
        st.stop()
    if st.button("Fotografar", icon=":material/photo_camera:", type="primary", use_container_width=True):
        st.session_state["camera_aberta"] = True
    foto = None
    if st.session_state.get("camera_aberta"):
        # GPS de novo a cada foto: o do início da página fica velho enquanto você anda
        _gps_foto = get_geolocation(component_key=f"gps_foto_{st.session_state.get('n_foto', 0)}")
        if _gps_foto and "coords" in _gps_foto:
            st.session_state["gps"] = (_gps_foto["coords"]["latitude"], _gps_foto["coords"]["longitude"])
        foto = st.camera_input("Fotografe algo de um dos temas",
                               help="Só vale foto tirada agora pela câmera, de algo real na sua frente.")
    if not foto:
        with st.expander("Como pontuar"):
            st.markdown("""
- Toda foto aceita vale **10 pontos**.
- **+10** se é a primeira vez que você acha aquilo.
- **Até +20** pela raridade: quem acha primeiro ganha mais.
- No tema de hoje, tudo vale **o dobro**.
- **Mirante** (a até 40 m de um lugar do mapa): +5, até 3 por dia.
- **Lupa**: 3 temas diferentes no dia a enchem, e o achado seguinte ganha +50%.
- **Desafios do dia**: +15 cada. **7 dias seguidos**: +20. **Com chuva**, plantas e pássaros: +5.
- **Meta da turma** (12h às 14h): se a turma fizer 20 fotos do tema do dia, cada uma ganha +10.
- Vale 0: foto repetida, de tela, fora dos temas ou tirada longe demais da anterior (mais de 3 km a mais de 120 km/h).""")
        st.stop()

    # Cada foto é julgada e salva uma vez só (o Streamlit roda a página de novo a cada clique)
    dados = foto.getvalue()
    id_foto = hashlib.sha256(dados).hexdigest()
    feita = st.session_state.get("ultima_captura")

    if not feita or feita["id"] != id_foto:
        imagem = Image.open(foto)
        jpeg = preparar_para_salvar(imagem)  # sem EXIF/GPS: é o que vai para a IA
        # Dois juízes em toda foto: a IA open source (se houver VISAO_URL) e o CLIP (se instalado).
        # O que cada um disse fica gravado. Tudo ao mesmo tempo: a IA, o bairro e o clima esperam a rede
        # enquanto o CLIP usa o processador.
        gps = st.session_state.get("gps")
        captura, aviso, clip, cidade, clima_foto = None, None, None, None, None
        with st.spinner("Os juízes estão olhando sua foto..."), ThreadPoolExecutor(3) as fila:
            f_ia = _em_paralelo(fila, julgar_ia, jpeg, VISAO_MODELO) if VISAO_URL else None
            f_bairro = _em_paralelo(fila, bairro_de, round(gps[0], 3), round(gps[1], 3)) if gps else None
            f_clima = _em_paralelo(fila, clima_agora, round(gps[0], 2), round(gps[1], 2)) if gps else None
            if MODELO_DISPONIVEL:
                clip = julgar_clip(imagem)
            if f_ia:
                try:
                    captura = f_ia.result()
                except visao.ErroVisao as erro:
                    aviso = str(erro)
            try:
                cidade = f_bairro.result() if f_bairro else None
            except Exception:
                pass
            clima_foto = f_clima.result() if f_clima else None
        if aviso:
            st.caption(f"⚠️ Juiz com IA indisponível agora ({aviso}). Usando só o CLIP.")
        juiz = ("ia+clip" if clip else "ia") if captura else ("clip" if clip else "manual")
        if captura is None and clip:  # sem a IA: o CLIP decide sozinho (achado genérico)
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

        # Localização aproximada (opcional): bairro + quadrado de ~500 m para o mapa da turma, e o contexto das
        # mecânicas. A coordenada exata não é gravada: só o que sai dela (mirante, tipo de lugar, clima, km).
        celula = None
        contexto = {"mirante": None, "tipo_lugar": None, "clima": None, "km_anterior": None, "min_anterior": None}
        if gps:
            lat, lon = gps
            celula = jogo.celula(lat, lon)
            lugares = st.session_state.get("_lugares") or []
            perto = min(lugares, key=lambda l: distancia_km(lat, lon, l["lat"], l["lon"]), default=None)
            contexto["mirante"] = bool(perto) and distancia_km(lat, lon, perto["lat"], perto["lon"]) * 1000 <= jogo.MIRANTE_M
            contexto["tipo_lugar"] = perto.get("tipo") if contexto["mirante"] else None
            contexto["clima"] = clima_foto
            # shortcut: a foto anterior fica só nesta sessão do navegador; ao recarregar, a conta recomeça.
            # Para valer entre aparelhos, guardar no banco a última célula da pessoa (função security definer).
            if anterior := st.session_state.get("_ultima_foto"):
                la0, lo0, t0 = anterior
                contexto["km_anterior"] = round(distancia_km(la0, lo0, lat, lon), 2)
                contexto["min_anterior"] = round((jogo.agora_naive() - t0).total_seconds() / 60, 1)
            st.session_state["_ultima_foto"] = (lat, lon, jogo.agora_naive())
        st.session_state["n_foto"] = st.session_state.get("n_foto", 0) + 1

        # Este mesmo objeto já foi fotografado? Compara o vetor do CLIP com as suas fotos e as da turma ali
        mesmo = armazenamento.objeto_visto(captura.tema, celula, clip["vetor"]) if clip else None
        juizes = {"juiz": juiz, "clip_tema": clip["tema"] if clip else None,
                  "clip_foto_real": clip["foto_real"] if clip else None,
                  "clip_prob_tema": round(clip["probs"].get(captura.tema, 0.0), 4) if clip and captura.tema else None,
                  "clip_prob_tela": round(clip["probs"].get("tela", 0.0), 4) if clip else None,
                  "clip_rank_tema": jogo.posicao(clip["probs"], captura.tema) if clip and captura.tema else None,
                  "mesmo_objeto": mesmo, **contexto}
        h = jogo.hash_foto(imagem)
        historico = armazenamento.capturas()
        nova = {"usuario": eu, "criado_em": jogo.agora_naive(), "tema": captura.tema or "nenhum",
                "achado": captura.achado, "foto_real": captura.foto_real, "foto_hash": h, **juizes}
        resultado = jogo.pontuar_nova(historico, nova)
        medalhas_antes = {m["id"]: m["nivel"] for m in jogo.medalhas(jogo.calcular_pontos(historico), eu)}
        vezes = jogo.vezes_achado(jogo.calcular_pontos(historico), captura.tema or "", captura.achado)
        id_captura = armazenamento.salvar_captura(captura.tema, captura.achado, captura.confianca,
                                                  captura.foto_real, h, cidade, celula,
                                                      clip_vetor=clip["vetor"] if clip else None, **juizes)
        feita = {"id": id_foto, "captura": captura, "resultado": resultado, "vezes": vezes,
                 "juizes": juizes, "id_captura": id_captura, "contestada": None}
        st.session_state["ultima_captura"] = feita
        # Um aviso por bônus e por medalha nova, mostrados depois do rerun (o placar do topo já com a foto nova)
        avisos = [(d[0].upper() + d[1:], ":material/bolt:")
                  for d in filter(None, str(resultado.get("detalhes") or "").split("; "))]
        for m in jogo.medalhas(jogo.calcular_pontos(armazenamento.capturas()), eu):
            if m["nivel"] and m["nivel"] != medalhas_antes.get(m["id"]):
                avisos.append((f"Medalha nova: {m['nome']} ({m['nivel']})", ":material/military_tech:"))
        feita["avisos"] = avisos
        st.rerun()

    for texto, icone in feita.pop("avisos", []):
        st.toast(texto, icon=icone)

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
    if not resultado.get("aceita") and ("nenhum tema" in motivo or "discordaram" in motivo or "CLIP viu" in motivo):
        if feita["contestada"]:
            st.caption(f"Contestação registrada: você disse que era {POR_ID[feita['contestada']].nome.lower()}. "
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

    if st.button("Ver pódio", icon=":material/trophy:", use_container_width=True):
        st.switch_page("pages/1_Pódio.py")
    st.caption("Tire outra foto acima para continuar jogando.")
