"""Servidor do juiz do WishLens (FastAPI). O app de celular manda a foto, o CLIP julga e os pontos saem de
src/jogo.py: as mesmas regras do app web.

Rodar:  uvicorn servidor.app:app --port 7860
Ambiente: SUPABASE_URL e SUPABASE_KEY (a chave anon). Sem elas, o jogo fica em memória, para testar, e o
jogador é o apelido do cabeçalho X-Apelido. VISAO_URL / VISAO_CHAVE / VISAO_MODELO ligam a IA (opcional).

Privacidade: o GPS chega no corpo do pedido (nunca na URL, que vai para os logs). Dele saem só a célula de
~500 m, o bairro, o mirante, o clima e a distância da foto anterior. A coordenada não é gravada.
"""

from __future__ import annotations

import importlib.util
import io
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from src import banco, clima, jogo, localizacao, visao
from src.banco import COLUNAS_CAPTURA, para_brasilia
from src.cartao import linha_juizes, partes_e_destaque
from src.categorias import nome_valido
from src.fotos import preparar_para_salvar
from src.lugares import buscar_pontos_temas, distancia_km
from src.temas import POR_ID, TEMAS, tema_do_dia

MODOS = ("livre",)
FOTO_MAX = 10 * 1024 * 1024
SUPABASE = (os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
VISAO = (os.environ.get("VISAO_URL"), os.environ.get("VISAO_CHAVE"),
         os.environ.get("VISAO_MODELO") or visao.MODELO_PADRAO)
CLIP_INSTALADO = all(importlib.util.find_spec(m) for m in ("torch", "transformers"))

_fila = ThreadPoolExecutor(8)


@asynccontextmanager
async def _ciclo(_app):
    if CLIP_INSTALADO:
        from src.reconhecimento import aquecer

        aquecer()  # o CLIP carrega enquanto o servidor sobe: a 1ª foto não espera ~12 s
    yield


app = FastAPI(title="WishLens: juiz", lifespan=_ciclo)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _clip(imagem: Image.Image) -> dict:
    from src.reconhecimento import julgar_clip

    return julgar_clip(imagem)


# ---------------------------------------------------------------- quem está jogando
_memoria: list[dict] = []
_trava = threading.Lock()


class SessaoMemoria:
    """Os mesmos métodos de banco.Sessao, guardando em memória (sem Supabase: para testar)."""

    def __init__(self, apelido: str):
        self.apelido = apelido

    def salvar_captura(self, registro: dict) -> None:
        with _trava:
            _memoria.append({**registro, "usuario": self.apelido})

    def capturas_todas(self) -> list[dict]:
        return list(_memoria)

    def contestar(self, id_captura: str, tema: str) -> None:
        for c in _memoria:
            if c["id"] == id_captura and c["usuario"] == self.apelido:
                c["contestada"] = tema

    def objeto_visto(self, tema: str, celula: str | None, vetor: list[float]) -> str | None:
        anteriores = [(c["usuario"], c.get("celula"), c.get("clip_vetor")) for c in _memoria
                      if c["tema"] == tema and c["foto_real"]]
        return jogo.objeto_visto(vetor, self.apelido, celula, anteriores)

    def manchas(self) -> list[dict]:
        df = pd.DataFrame(_memoria, columns=COLUNAS_CAPTURA)
        df = df[df["celula"].notna() & df["foto_real"].astype(bool) & (df["tema"] != "nenhum")]
        return [{"celula": c, "tema": t, "n": len(g), "achados": list(g["achado"].value_counts(ascending=True).index[:3])}
                for (c, t), g in df.groupby(["celula", "tema"]) if len(g) >= 2]

    def guardioes(self) -> list[dict]:
        g = jogo.guardioes(pd.DataFrame(_memoria, columns=COLUNAS_CAPTURA))
        return [{"celula": r.celula, "apelido": r.usuario, "achados": int(r.achados)} for r in g.itertuples()]


_sessoes: dict[str, tuple[float, banco.Sessao]] = {}
SESSAO_SEGUNDOS = 300


def _sessao_supabase(token: str) -> banco.Sessao:
    agora = time.monotonic()
    guardada = _sessoes.get(token)
    if guardada and agora - guardada[0] < SESSAO_SEGUNDOS:
        return guardada[1]
    from supabase import create_client

    cliente = create_client(*SUPABASE)
    try:
        uid = cliente.auth.get_user(token).user.id
    except Exception:
        raise HTTPException(401, "Sessão expirada: entre de novo.")
    cliente.postgrest.auth(token)  # o banco vê a própria pessoa: o RLS continua valendo
    apelido = cliente.table("perfis").select("apelido").eq("id", uid).single().execute().data["apelido"]
    sessao = banco.Sessao(cliente, uid, apelido)
    with _trava:
        for velho in [t for t, (quando, _) in _sessoes.items() if agora - quando >= SESSAO_SEGUNDOS]:
            del _sessoes[velho]
        _sessoes[token] = (agora, sessao)
    return sessao


def sessao(authorization: str | None = Header(None), x_apelido: str | None = Header(None)):
    if all(SUPABASE):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Entre na sua conta para jogar.")
        return _sessao_supabase(authorization.removeprefix("Bearer ").strip())
    apelido = (x_apelido or "eu").strip()[:30]
    if not nome_valido(apelido):
        raise HTTPException(400, "Apelido inválido.")
    return SessaoMemoria(apelido)


# ---------------------------------------------------------------- capturas e pontos
_cache: dict = {"quando": 0.0, "linhas": None}
CACHE_SEGUNDOS = 15


def _capturas(s) -> pd.DataFrame:
    """Todas as capturas da turma. Com o Supabase, uma cópia vale 15 s para todo mundo: o RLS deixa toda conta
    ler as mesmas linhas (sem bairro nem célula), então não há o que separar por pessoa."""
    if isinstance(s, SessaoMemoria):
        linhas = s.capturas_todas()
    else:
        if _cache["linhas"] is None or time.monotonic() - _cache["quando"] > CACHE_SEGUNDOS:
            _cache.update(quando=time.monotonic(), linhas=s.capturas_todas())
        linhas = _cache["linhas"]
    df = pd.DataFrame(linhas, columns=COLUNAS_CAPTURA)
    if not df.empty:
        df["criado_em"] = pd.to_datetime([para_brasilia(x) for x in df["criado_em"]])
    return df


def _pontuadas(s) -> pd.DataFrame:
    return jogo.calcular_pontos(_capturas(s))


def _hoje(pontuadas: pd.DataFrame, eu: str) -> tuple[int, int | None]:
    ranking = jogo.podio(pontuadas, "hoje")
    meus = ranking[ranking["usuario"] == eu]
    return (int(meus["pontos"].iloc[0]), int(meus["posicao"].iloc[0])) if not meus.empty else (0, None)


def _tema(t) -> dict:
    return {"id": t.id, "nome": t.nome, "emoji": t.emoji, "cor": t.cor, "onde": t.onde}


# ---------------------------------------------------------------- serviços de fora, com cache
@lru_cache(maxsize=512)
def _lugares(lat2: float, lon2: float, hora: int) -> tuple:
    return tuple(buscar_pontos_temas(TEMAS, lat2, lon2))  # RuntimeError (Overpass fora) não fica em cache


def lugares_perto(lat: float, lon: float) -> list[dict]:
    try:
        return list(_lugares(round(lat, 2), round(lon, 2), int(time.time() // 3600)))
    except RuntimeError:
        return []


@lru_cache(maxsize=2048)
def _bairro(lat3: float, lon3: float) -> str | None:
    return localizacao.bairro_de(lat3, lon3)


@lru_cache(maxsize=512)
def _clima(lat2: float, lon2: float, meia_hora: int) -> str | None:
    return clima.agora(lat2, lon2)


def _bairro_seguro(lat: float, lon: float) -> str | None:
    try:
        return _bairro(round(lat, 3), round(lon, 3))
    except Exception:
        return None


# shortcut: a foto anterior de cada pessoa fica na memória do servidor (some quando ele reinicia).
# Para valer sempre, guardar no banco a última célula da pessoa (função security definer).
_ultima_foto: dict[str, tuple[float, float, object]] = {}


# ---------------------------------------------------------------- rotas
@app.get("/saude")
def saude():
    from src import reconhecimento

    pronto = CLIP_INSTALADO and reconhecimento._carregar_uma_vez.cache_info().currsize > 0
    return {"ok": True, "clip": "pronto" if pronto else ("carregando" if CLIP_INSTALADO else "ausente"),
            "banco": "supabase" if all(SUPABASE) else "memoria"}


@app.get("/temas")
def temas():
    return {"temas": [_tema(t) for t in TEMAS], "tema_do_dia": tema_do_dia().id, "modos": list(MODOS)}


@app.get("/estado")
def estado(s=Depends(sessao)):
    """O placar do topo e o painel do dia: pontos, posição, lupa, corrente, meta e desafios."""
    p = _pontuadas(s)
    pontos, posicao = _hoje(p, s.apelido)
    meta = jogo.meta_da_turma(p)
    return {"apelido": s.apelido, "pontos_hoje": pontos, "posicao": posicao, "tema_do_dia": _tema(tema_do_dia()),
            "dia": jogo.estado_do_dia(p, s.apelido), "corrente": jogo.corrente_atual(p, s.apelido),
            "meta": {**meta, "tema": meta["tema"].id}}


@app.get("/podio")
def podio(periodo: str = "hoje", tema: str | None = None, s=Depends(sessao)):
    if periodo not in ("hoje", "semana", "geral") or (tema and tema not in POR_ID):
        raise HTTPException(400, "Período ou tema inválido.")
    ranking = jogo.podio(_pontuadas(s), periodo, tema=tema)
    linhas = [{"posicao": int(r.posicao), "apelido": str(r.usuario), "pontos": int(r.pontos),
               "achados": int(r.achados), "voce": r.usuario == s.apelido} for r in ranking.itertuples()]
    return {"ranking": linhas, "guardioes": [{"apelido": str(u), "quadrados": int(n)} for u, n in
                                            pd.Series([g["apelido"] for g in _guardioes(s)]).value_counts().items()]}


@app.get("/colecao")
def colecao(s=Depends(sessao)):
    p = _pontuadas(s)
    minhas = p[p["usuario"] == s.apelido] if not p.empty else p
    aceitas = minhas[minhas["aceita"]] if not minhas.empty else minhas
    medalhas = jogo.medalhas(p, s.apelido)
    medalha_de = {m["id"]: m for m in medalhas}
    turma = (p[p["aceita"]].assign(chave=lambda d: d["achado"].map(jogo.normalizar)).groupby(["tema", "chave"]).size()
             if not p.empty else pd.Series(dtype=int))
    album = []
    for t in TEMAS:
        meus = aceitas[aceitas["tema"] == t.id] if not aceitas.empty else aceitas
        unicos = meus.assign(chave=meus["achado"].map(jogo.normalizar)).drop_duplicates("chave") if not meus.empty else meus
        colados = [{"achado": str(r.achado), "turma": int(turma.get((t.id, r.chave), 1))} for r in unicos.itertuples()]
        total = int((turma.index.get_level_values("tema") == t.id).sum()) if not turma.empty else 0
        album.append({"tema": _tema(t), "colados": colados, "total": max(total, len(colados)),
                      "faltam": [{"dica": d, "turma": int(n)} for d, n in jogo.lacunas(p, s.apelido, t.id)],
                      "medalha": medalha_de.get(t.id)})
    resumo = {"pontos": int(aceitas["pontos"].sum()) if not aceitas.empty else 0,
              "achados": int(aceitas["achado"].map(jogo.normalizar).nunique()) if not aceitas.empty else 0,
              "corrente": jogo.corrente_atual(p, s.apelido), "fotos": len(minhas),
              "recusadas": round(float((~minhas["aceita"]).mean()), 2) if not minhas.empty else 0.0}
    try:
        estilo = jogo.estilo_jogador(p, s.apelido) if not aceitas.empty else None
    except Exception:  # K-Means precisa de jogadores suficientes: sem estilo, a coleção continua
        estilo = None
    return {"resumo": resumo, "estilo": estilo, "album": album, "medalhas": medalhas}


class Posicao(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


def _guardioes(s) -> list[dict]:
    try:
        return s.guardioes()
    except Exception:  # banco criado antes da função guardioes_quadrados
        return []


@app.post("/mapa")
def mapa(pos: Posicao, s=Depends(sessao)):
    """Lugares de cada tema (OpenStreetMap) perto de você e as manchas da turma, com o guardião de cada uma."""
    lugares = [{**l, "distancia_km": round(distancia_km(pos.lat, pos.lon, l["lat"], l["lon"]), 2)}
               for l in lugares_perto(pos.lat, pos.lon)]
    try:
        manchas = s.manchas()
    except Exception:  # banco criado antes da função manchas_capturas
        manchas = []
    guardiao = {g["celula"]: g["apelido"] for g in _guardioes(s)}
    for m in manchas:
        m["lat"], m["lon"] = jogo.centro_celula(m["celula"])
        m["guardiao"] = guardiao.get(m["celula"])
        m["n"] = int(m["n"])
    return {"lugares": lugares, "manchas": manchas}


class Contestacao(BaseModel):
    id: str = Field(max_length=40)
    tema: str


@app.post("/contestar")
def contestar(c: Contestacao, s=Depends(sessao)):
    if c.tema not in POR_ID:
        raise HTTPException(400, "Tema inválido.")
    s.contestar(c.id, c.tema)
    _cache["linhas"] = None
    return {"ok": True}


def _cartao(resultado: dict, captura: visao.Captura, vezes: int, juizes: dict) -> dict:
    t = POR_ID.get(captura.tema or "")
    cartao = {"aceita": bool(resultado.get("aceita")), "pontos": int(resultado.get("pontos") or 0),
              "tema": _tema(t) if t else None, "achado": captura.achado or (t.generico if t else ""),
              "juizes": linha_juizes(juizes, captura.tema)}
    if not cartao["aceita"]:
        motivo = str(resultado.get("motivo") or "foto recusada")
        return {**cartao, "pontos": 0, "motivo": motivo,
                "pode_contestar": any(m in motivo for m in ("nenhum tema", "discordaram", "CLIP viu"))}
    partes, bonus, destaque = partes_e_destaque(resultado, vezes)
    return {**cartao, "partes": partes, "bonus": bonus, "destaque": destaque, "pode_contestar": False}


@app.post("/julgar")
def julgar(foto: UploadFile = File(...), lat: float | None = Form(None, ge=-90, le=90),
           lon: float | None = Form(None, ge=-180, le=180), modo: str = Form("livre"), s=Depends(sessao)):
    """Julga a foto, grava a captura e devolve o cartão de pontos (ou pede outra foto, se ficou borrada)."""
    if modo not in MODOS:
        raise HTTPException(400, "Modo inválido.")
    if not CLIP_INSTALADO:
        raise HTTPException(503, "O juiz (CLIP) não está instalado neste servidor.")
    dados = foto.file.read(FOTO_MAX + 1)
    if len(dados) > FOTO_MAX:
        raise HTTPException(413, "Foto grande demais (máximo 10 MB).")
    try:
        imagem = ImageOps.exif_transpose(Image.open(io.BytesIO(dados))).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "Não consegui abrir a foto.")

    gps = (lat, lon) if lat is not None and lon is not None else None
    jpeg = preparar_para_salvar(imagem) if VISAO[0] else None  # sem EXIF/GPS: é o que vai para a IA
    f_ia = _fila.submit(visao.identificar_captura, jpeg, VISAO[0], VISAO[2], VISAO[1]) if VISAO[0] else None
    f_bairro = _fila.submit(_bairro_seguro, *gps) if gps else None
    f_clima = _fila.submit(_clima, round(gps[0], 2), round(gps[1], 2), int(time.time() // 1800)) if gps else None
    f_lugares = _fila.submit(lugares_perto, *gps) if gps else None
    clip = _clip(imagem)  # o CLIP usa o processador enquanto o resto espera a rede

    if clip["nao_identificou"]:  # não julga nem salva: a pessoa tira outra
        return {"status": "borrada", "mensagem": "Não foi possível identificar: a foto ficou borrada. "
                                                 "Tire outra, com o celular parado e o objeto em foco."}
    captura, aviso = None, None
    if f_ia:
        try:
            captura = f_ia.result()
        except visao.ErroVisao as erro:
            aviso = f"Juiz com IA indisponível agora ({erro}). Usando só o CLIP."
    juiz = "ia+clip" if captura else "clip"
    if captura is None:
        captura = visao.Captura(clip["tema"], clip["achado"], clip["foto_real"], clip["confianca"])

    celula, cidade = None, None
    contexto = {"mirante": None, "tipo_lugar": None, "clima": None, "km_anterior": None, "min_anterior": None}
    if gps:
        lat, lon = gps
        celula = jogo.celula(lat, lon)
        cidade = f_bairro.result()
        lugares = f_lugares.result()
        perto = min(lugares, key=lambda l: distancia_km(lat, lon, l["lat"], l["lon"]), default=None)
        contexto["mirante"] = bool(perto) and distancia_km(lat, lon, perto["lat"], perto["lon"]) * 1000 <= jogo.MIRANTE_M
        contexto["tipo_lugar"] = perto.get("tipo") if contexto["mirante"] else None
        contexto["clima"] = f_clima.result()
        agora = jogo.agora_naive()
        if anterior := _ultima_foto.get(s.apelido):
            la0, lo0, t0 = anterior
            contexto["km_anterior"] = round(distancia_km(la0, lo0, lat, lon), 2)
            contexto["min_anterior"] = round((agora - t0).total_seconds() / 60, 1)
        _ultima_foto[s.apelido] = (round(lat, 3), round(lon, 3), agora)

    mesmo = None
    if captura.tema:
        try:  # o banco compara o vetor sem devolver quem, quando nem onde
            mesmo = s.objeto_visto(captura.tema, celula, clip["vetor"])
        except Exception:  # banco sem a função objeto_visto (schema.sql antigo)
            pass
    juizes = {"juiz": juiz, "clip_tema": clip["tema"], "clip_foto_real": clip["foto_real"],
              "clip_prob_tema": round(clip["probs"].get(captura.tema, 0.0), 4) if captura.tema else None,
              "clip_prob_tela": round(clip["probs"].get("tela", 0.0), 4),
              "clip_rank_tema": jogo.posicao(clip["probs"], captura.tema) if captura.tema else None,
              "mesmo_objeto": mesmo, **contexto}
    h = jogo.hash_foto(imagem)
    historico = _capturas(s)
    antes = jogo.calcular_pontos(historico)
    nova = {"usuario": s.apelido, "criado_em": jogo.agora_naive(), "tema": captura.tema or "nenhum",
            "achado": captura.achado, "foto_real": captura.foto_real, "foto_hash": h, **juizes}
    resultado = jogo.pontuar_nova(historico, nova)
    medalhas_antes = {m["id"]: m["nivel"] for m in jogo.medalhas(antes, s.apelido)}
    vezes = jogo.vezes_achado(antes, captura.tema or "", captura.achado)

    registro = {"id": str(uuid.uuid4()), "criado_em": nova["criado_em"], "tema": captura.tema or "nenhum",
                "achado": captura.achado or "", "confianca": captura.confianca, "foto_real": bool(captura.foto_real),
                "foto_hash": h, "cidade": cidade, "celula": celula, "clip_vetor": clip["vetor"], **juizes}
    s.salvar_captura(registro)
    _cache["linhas"] = None

    depois = _pontuadas(s)
    avisos = [d[0].upper() + d[1:] for d in filter(None, str(resultado.get("detalhes") or "").split("; "))]
    avisos += [f"Medalha nova: {m['nome']} ({m['nivel']})" for m in jogo.medalhas(depois, s.apelido)
               if m["nivel"] and m["nivel"] != medalhas_antes.get(m["id"])]
    pontos, posicao = _hoje(depois, s.apelido)
    return {"status": "ok", "id": registro["id"], "cartao": _cartao(resultado, captura, vezes, juizes),
            "avisos": avisos, "aviso_juiz": aviso, "pontos_hoje": pontos, "posicao": posicao}
