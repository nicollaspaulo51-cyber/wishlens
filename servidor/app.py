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
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

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
from src.temas import MODOS as ABAS, POR_ID, TEMAS, TEMAS_ANTIGOS, TODOS, agora, tema_do_dia

MODOS = ("livre", *ABAS)
# Até onde a foto conta como "no lugar" da aba, pelo tipo do lugar do OpenStreetMap. GPS dentro de prédio erra mais;
# parque e quadra são áreas grandes e o OSM só dá o centro delas.
LUGAR_M = {"fitness_station": 40, "fitness_centre": 60, "park": 150, "pitch": 150}
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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Agora"])


@app.middleware("http")
async def _relogio(request, chamar_rota):
    """A hora do juiz em cada resposta: o app mede "há 3 min" por ela, não pelo relógio do celular ou do PC."""
    resposta = await chamar_rota(request)
    resposta.headers["X-Agora"] = str(int(time.time() * 1000))
    return resposta


def _clip(imagem: Image.Image, modo: str = "livre") -> dict:
    from src.reconhecimento import julgar_clip

    return julgar_clip(imagem, modo)


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


def _pontuadas(s, capturas: pd.DataFrame | None = None) -> pd.DataFrame:
    """Pontos do Mapa livre: as fotos das outras abas não entram (nem no tema do dia, lupa, desafios ou meta)."""
    df = _capturas(s) if capturas is None else capturas
    return jogo.calcular_pontos(df[~df["tema"].isin(ABAS)])


def _pontuadas_aba(s, modo: str, capturas: pd.DataFrame | None = None) -> pd.DataFrame:
    return jogo.pontos_modo(_capturas(s) if capturas is None else capturas, modo)


def _hoje(pontuadas: pd.DataFrame, eu: str) -> tuple[int, int | None]:
    ranking = jogo.podio(pontuadas, "hoje")
    meus = ranking[ranking["usuario"] == eu]
    return (int(meus["pontos"].iloc[0]), int(meus["posicao"].iloc[0])) if not meus.empty else (0, None)


def _tema(t) -> dict:
    return {"id": t.id, "nome": t.nome, "emoji": t.emoji, "cor": t.cor, "onde": t.onde}


# ---------------------------------------------------------------- serviços de fora, com cache
RAIOS_ABA_M = (2000, 5000, 10000)  # medido em pontos de teste: em 2 km muitas vezes não havia academia nem mirante
LUGARES_MINIMOS = 3
@lru_cache(maxsize=512)
def _lugares(modo: str, lat2: float, lon2: float, hora: int) -> tuple:
    if modo == "livre":
        return tuple(buscar_pontos_temas(TEMAS, lat2, lon2))  # RuntimeError (Overpass fora) não fica em cache
    # Academias, mirantes e lan houses são raros: com menos de LUGARES_MINIMOS em 2 km, procura mais longe
    for raio in RAIOS_ABA_M:
        achados = buscar_pontos_temas([ABAS[modo]], lat2, lon2, raio_m=raio)
        if len(achados) >= LUGARES_MINIMOS:
            break
    return tuple(achados)


# Últimos lugares bons de cada quadrado de ~1 km, em disco (volume "dados"): o Overpass vive fora do ar ou
# devolvendo lista vazia, e os ícones sumiam do mapa. Lojas e parques mudam devagar, então guardar é seguro.
RESERVA_LUGARES = Path(os.environ.get("DADOS_DIR", "/home/user/dados")) / "lugares.json"
_reserva: dict[str, list] | None = None
_trava_reserva = threading.Lock()


def _ler_reserva() -> dict[str, list]:
    global _reserva
    if _reserva is None:
        try:
            _reserva = json.loads(RESERVA_LUGARES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _reserva = {}
    return _reserva


def _guardar_reserva(chave: str, lugares: list[dict]) -> None:
    with _trava_reserva:
        reserva = _ler_reserva()
        if reserva.get(chave) == lugares:
            return
        reserva[chave] = lugares
        try:
            RESERVA_LUGARES.parent.mkdir(parents=True, exist_ok=True)
            temporario = RESERVA_LUGARES.with_suffix(".tmp")
            temporario.write_text(json.dumps(reserva, ensure_ascii=False), encoding="utf-8")
            temporario.replace(RESERVA_LUGARES)
        except OSError:  # sem disco: fica só na memória
            pass


def _da_reserva(modo: str, lat2: float, lon2: float) -> list[dict] | None:
    """Os últimos lugares bons deste quadrado ou de um vizinho (andou um pouco desde a última vez)."""
    reserva = _ler_reserva()
    for dl in (0.0, -0.01, 0.01):
        for dn in (0.0, -0.01, 0.01):
            achados = reserva.get(f"{modo}:{round(lat2 + dl, 2)}:{round(lon2 + dn, 2)}")
            if achados:
                return achados
    return None


def lugares_perto(lat: float, lon: float, modo: str = "livre") -> list[dict] | None:
    """Lugares da aba perto de você. Se o OpenStreetMap (Overpass) não respondeu ou veio vazio, usa os últimos
    lugares bons guardados. None só quando não respondeu e não há nada guardado."""
    lat2, lon2 = round(lat, 2), round(lon, 2)
    try:
        achados = list(_lugares(modo, lat2, lon2, int(time.time() // 3600)))
    except RuntimeError:
        achados = None
    if achados:
        _guardar_reserva(f"{modo}:{lat2}:{lon2}", achados)
        return achados
    guardados = _da_reserva(modo, lat2, lon2)
    return guardados if guardados else achados


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
    return {"temas": [_tema(t) for t in TEMAS], "tema_do_dia": tema_do_dia().id, "modos": list(MODOS),
            "abas": [{**_tema(t), "conta": t.conta} for t in ABAS.values()]}


@app.get("/estado")
def estado(s=Depends(sessao)):
    """O placar do topo e o painel do dia: pontos, posição, lupa, corrente, meta e desafios."""
    todas = _capturas(s)
    p = _pontuadas(s, todas)
    pontos, posicao = _hoje(p, s.apelido)
    meta = jogo.meta_da_turma(p)
    # pontos de hoje em cada aba, para o seletor de abas do app
    abas = {"livre": pontos, **{m: _hoje(_pontuadas_aba(s, m, todas), s.apelido)[0] for m in ABAS}}
    return {"apelido": s.apelido, "pontos_hoje": pontos, "posicao": posicao, "pontos_abas": abas,
            "espera_competicao": jogo.espera_competicao(todas, s.apelido),
            "tema_do_dia": _tema(tema_do_dia()),
            "dia": jogo.estado_do_dia(p, s.apelido), "corrente": jogo.corrente_atual(p, s.apelido),
            "meta": {**meta, "tema": meta["tema"].id}}


@app.get("/podio")
def podio(periodo: str = "hoje", tema: str | None = None, modo: str = "livre", s=Depends(sessao)):
    if periodo not in ("hoje", "semana", "geral") or (tema and tema not in POR_ID) or modo not in MODOS:
        raise HTTPException(400, "Período, tema ou aba inválido.")
    contar = lambda nomes: [{"apelido": str(u), "quadrados": int(n)} for u, n in pd.Series(nomes, dtype=object).value_counts().items()]
    if modo == "livre":
        ranking, guardioes, donos = jogo.podio(_pontuadas(s), periodo, tema=tema), [g["apelido"] for g in _guardioes(s)], []
    else:
        p = _pontuadas_aba(s, modo)
        # shortcut: os donos saem da célula, que no Supabase não é legível pela API: lá a lista fica vazia
        # até existir uma função security definer como guardioes_quadrados
        ranking, guardioes = jogo.podio(p, periodo), []
        donos = list(jogo.donos_academia(p)["usuario"]) if modo == "academia" else []
    linhas = [{"posicao": int(r.posicao), "apelido": str(r.usuario), "pontos": int(r.pontos),
               "achados": int(r.achados), "voce": r.usuario == s.apelido} for r in ranking.itertuples()]
    return {"ranking": linhas, "guardioes": contar(guardioes), "donos": contar(donos)}


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
    # temas que saíram do jogo (Pássaros) só aparecem para quem tem achados neles
    antigos = [t for t in TEMAS_ANTIGOS.values() if not aceitas.empty and (aceitas["tema"] == t.id).any()]
    for t in [*TEMAS, *antigos]:
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


class PedidoMapa(Posicao):
    modo: str = "livre"


def _guardioes(s) -> list[dict]:
    try:
        return s.guardioes()
    except Exception:  # banco criado antes da função guardioes_quadrados
        return []


@app.post("/mapa")
def mapa(pos: PedidoMapa, s=Depends(sessao)):
    """Lugares da aba (OpenStreetMap) perto de você e as manchas da turma, com o guardião de cada uma (Mapa livre)."""
    if pos.modo not in MODOS:
        raise HTTPException(400, "Aba inválida.")
    perto = lugares_perto(pos.lat, pos.lon) if pos.modo == "livre" else lugares_perto(pos.lat, pos.lon, pos.modo)
    lugares = [{**l, "distancia_km": round(distancia_km(pos.lat, pos.lon, l["lat"], l["lon"]), 2)} for l in perto or []]
    try:
        manchas = s.manchas()
    except Exception:  # banco criado antes da função manchas_capturas
        manchas = []
    da_aba = POR_ID if pos.modo == "livre" else (pos.modo,)
    manchas = [m for m in manchas if m["tema"] in da_aba]
    guardiao = {g["celula"]: g["apelido"] for g in _guardioes(s)} if pos.modo == "livre" else {}
    for m in manchas:
        m["lat"], m["lon"] = jogo.centro_celula(m["celula"])
        m["guardiao"] = guardiao.get(m["celula"])
        m["n"] = int(m["n"])
    # lugares_ok=False: o OpenStreetMap não respondeu agora e o app tenta de novo daqui a pouco
    return {"lugares": lugares, "manchas": manchas, "lugares_ok": perto is not None}


class Contestacao(BaseModel):
    id: str = Field(max_length=40)
    tema: str


# ---------------------------------------------------------------- avisos (suporte)
# Cada aviso vira uma linha de avisos.jsonl, no volume do Docker: sobrevive a reinícios e não vai para o Git.
# Para ler: docker exec servidor-juiz-1 cat /home/user/avisos/avisos.jsonl
AVISOS = Path(os.environ.get("AVISOS_DIR", "/home/user/avisos")) / "avisos.jsonl"
TIPOS_AVISO = ("juiz", "app", "outro")
AVISOS_POR_HORA = 5
_avisos_recentes: dict[str, list[float]] = {}
_trava_avisos = threading.Lock()
# Do que o juiz disse sobre a foto, só isto vai junto (nunca célula, bairro, hash ou vetor)
CAMPOS_DO_JUIZ = ("tema", "achado", "confianca", "foto_real", "juiz", "clip_tema", "clip_prob_tema",
                  "clip_prob_tela", "clip_rank_tema")


class Aviso(BaseModel):
    tipo: str
    texto: str = Field(min_length=3, max_length=500)
    captura: str | None = Field(None, max_length=40)
    aparelho: str | None = Field(None, max_length=40)


def _do_juiz(s, id_captura: str | None) -> dict | None:
    if not id_captura:
        return None
    df = _capturas(s)
    linha = df[df["id"] == id_captura]
    if linha.empty:
        return None
    r = linha.iloc[0]
    return {c: (None if pd.isna(r[c]) else r[c].item() if hasattr(r[c], "item") else r[c]) for c in CAMPOS_DO_JUIZ}


@app.post("/aviso")
def avisar(a: Aviso, s=Depends(sessao)):
    if a.tipo not in TIPOS_AVISO:
        raise HTTPException(400, "Tipo de aviso inválido.")
    instante = time.time()
    with _trava_avisos:
        recentes = [t for t in _avisos_recentes.get(s.apelido, []) if instante - t < 3600]
        if len(recentes) >= AVISOS_POR_HORA:
            raise HTTPException(429, "Você já mandou 5 avisos nesta hora. Tente de novo mais tarde.")
        _avisos_recentes[s.apelido] = [*recentes, instante]
    registro = {"quando": agora().isoformat(timespec="seconds"), "apelido": s.apelido, "tipo": a.tipo,
                "texto": a.texto.strip(), "aparelho": a.aparelho, "captura": a.captura,
                "juiz_disse": _do_juiz(s, a.captura)}
    gravar_aviso(registro)
    return {"ok": True}


def gravar_aviso(registro: dict) -> None:
    """Uma linha no arquivo de avisos (suporte e denúncias do chat)."""
    with _trava_avisos:
        AVISOS.parent.mkdir(parents=True, exist_ok=True)
        with AVISOS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


@app.post("/contestar")
def contestar(c: Contestacao, s=Depends(sessao)):
    if c.tema not in POR_ID:
        raise HTTPException(400, "Tema inválido.")
    s.contestar(c.id, c.tema)
    _cache["linhas"] = None
    return {"ok": True}


def _cartao(resultado: dict, captura: visao.Captura, vezes: int, juizes: dict) -> dict:
    t = TODOS.get(captura.tema or "")
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
    livre = modo == "livre"
    if modo == "competicao" and (falta := jogo.espera_competicao(_capturas(s), s.apelido)):
        minutos = -(-falta // 60)
        return {"status": "borrada", "titulo": "Espere a próxima partida",
                "mensagem": f"Na Competição vale uma foto de partida a cada {jogo.ESPERA_COMPETICAO_MIN} minutos. "
                            f"Faltam {minutos} min.", "espera": falta}
    if not gps and modo in jogo.NO_LUGAR_EXIGIDO:  # não julga nem salva: nesta aba a foto só vale no lugar
        return {"status": "borrada", "titulo": "Ligue a localização",
                "mensagem": f"Na aba {ABAS[modo].nome} a foto só vale {jogo.NO_LUGAR_EXIGIDO[modo].replace('fora de', 'dentro de')}. "
                            "Ligue a localização e tire de novo."}
    # A IA confere se a foto é real em todas as abas; o tema dela só vale no Mapa livre (conhece só os 5 temas).
    # Na Competição a foto É de uma tela, então ela fica de fora.
    usar_ia = VISAO[0] and modo != "competicao"
    jpeg = preparar_para_salvar(imagem) if usar_ia else None  # sem EXIF/GPS: é o que vai para a IA
    f_ia = _fila.submit(visao.identificar_captura, jpeg, VISAO[0], VISAO[2], VISAO[1]) if usar_ia else None
    f_bairro = _fila.submit(_bairro_seguro, *gps) if gps else None
    f_clima = _fila.submit(_clima, round(gps[0], 2), round(gps[1], 2), int(time.time() // 1800)) if gps else None
    f_lugares = (_fila.submit(lugares_perto, *gps) if livre else _fila.submit(lugares_perto, *gps, modo)) if gps else None
    clip = _clip(imagem, modo)  # o CLIP usa o processador enquanto o resto espera a rede

    if clip["nao_identificou"]:  # não julga nem salva: a pessoa tira outra
        return {"status": "borrada", "titulo": "Foto borrada",
                "mensagem": "Não foi possível identificar: a foto ficou borrada. "
                            "Tire outra, com o celular parado e o objeto em foco."}
    if f_lugares and modo in jogo.NO_LUGAR_EXIGIDO and f_lugares.result() is None:
        return {"status": "borrada", "titulo": "Lugar não confirmado",
                "mensagem": "O mapa (OpenStreetMap) não respondeu agora, então não deu para confirmar o lugar. "
                            "Tente de novo daqui a pouco."}
    captura, aviso = None, None
    if f_ia:
        try:
            captura = f_ia.result()
        except visao.ErroVisao as erro:
            aviso = f"Juiz com IA indisponível agora ({erro}). Usando só o CLIP."
    juiz = "ia+clip" if captura else "clip"
    if captura is None:
        captura = visao.Captura(clip["tema"], clip["achado"], clip["foto_real"], clip["confianca"])
    elif not livre:  # nas outras abas o CLIP diz o que é; a IA só pode marcar a foto como falsa
        captura = visao.Captura(clip["tema"], clip["achado"], clip["foto_real"] and captura.foto_real, clip["confianca"])

    celula, cidade = None, None
    contexto = {"mirante": None, "tipo_lugar": None, "clima": None, "km_anterior": None, "min_anterior": None}
    if gps:
        lat, lon = gps
        celula = jogo.celula(lat, lon)
        cidade = f_bairro.result()
        lugares = f_lugares.result() or []
        perto = min(lugares, key=lambda l: distancia_km(lat, lon, l["lat"], l["lon"]), default=None)
        limite = jogo.MIRANTE_M if livre or not perto else LUGAR_M.get(perto.get("tipo"), jogo.MIRANTE_M)
        # nas outras abas, "mirante" quer dizer "no lugar da aba" (mirante, praça com aparelhos ou academia)
        contexto["mirante"] = bool(perto) and distancia_km(lat, lon, perto["lat"], perto["lon"]) * 1000 <= limite
        contexto["tipo_lugar"] = perto.get("tipo") if contexto["mirante"] else None
        contexto["clima"] = f_clima.result()
        agora = jogo.agora_naive()
        if anterior := _ultima_foto.get(s.apelido):
            la0, lo0, t0 = anterior
            contexto["km_anterior"] = round(distancia_km(la0, lo0, lat, lon), 2)
            contexto["min_anterior"] = round((agora - t0).total_seconds() / 60, 1)
        _ultima_foto[s.apelido] = (round(lat, 3), round(lon, 3), agora)

    mesmo = None
    if captura.tema and modo != "competicao":  # telas de vitória do mesmo jogo são quase iguais
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
    nova = {"usuario": s.apelido, "criado_em": jogo.agora_naive(), "tema": captura.tema or "nenhum",
            "achado": captura.achado, "foto_real": captura.foto_real, "foto_hash": h, "celula": celula, **juizes}
    dica = _dica_outra_aba(modo, clip.get("outra_aba")) if not captura.tema else None
    if livre:
        antes = _pontuadas(s, historico)
        resultado = jogo.pontuar_nova(historico[~historico["tema"].isin(ABAS)], nova)
        medalhas_antes = {m["id"]: m["nivel"] for m in jogo.medalhas(antes, s.apelido)}
    else:
        antes = _pontuadas_aba(s, modo, historico)
        if captura.tema:
            tudo = pd.concat([historico, pd.DataFrame([{**nova, "_nova": True}])], ignore_index=True)
            pontuadas = jogo.pontos_modo(tudo, modo)
            resultado = pontuadas[pontuadas["_nova"].eq(True)].iloc[0].to_dict()
        else:
            resultado = {"aceita": False, "motivo": dica or f"não é {ABAS[modo].conta.split('.')[0].lower()}"}
    vezes = jogo.vezes_achado(antes, captura.tema or "", captura.achado)

    registro = {"id": str(uuid.uuid4()), "criado_em": nova["criado_em"], "tema": captura.tema or "nenhum",
                "achado": captura.achado or "", "confianca": captura.confianca, "foto_real": bool(captura.foto_real),
                "foto_hash": h, "cidade": cidade, "celula": celula, "clip_vetor": clip["vetor"], **juizes}
    s.salvar_captura(registro)
    _cache["linhas"] = None

    depois = _pontuadas(s) if livre else _pontuadas_aba(s, modo)
    avisos = [d[0].upper() + d[1:] for d in filter(None, str(resultado.get("detalhes") or "").split("; "))]
    if livre:
        avisos += [f"Medalha nova: {m['nome']} ({m['nivel']})" for m in jogo.medalhas(depois, s.apelido)
                   if m["nivel"] and m["nivel"] != medalhas_antes.get(m["id"])]
        if dica:
            avisos.insert(0, dica)
    pontos, posicao = _hoje(depois, s.apelido)
    cartao = _cartao(resultado, captura, vezes, juizes)
    if not livre:
        cartao["pode_contestar"] = False  # contestar é escolher outro tema do Mapa livre
    return {"status": "ok", "id": registro["id"], "cartao": cartao, "modo": modo,
            "avisos": avisos, "aviso_juiz": aviso, "pontos_hoje": pontos, "posicao": posicao}


def _dica_outra_aba(modo: str, outra: str | None) -> str | None:
    """Em vez de só recusar, diz em qual aba a foto pontuaria."""
    if not outra:
        return None
    if modo == "paisagens" and outra == "livre":
        return ("Isso parece uma planta ou objeto de perto. Afaste-se para mostrar a vista, "
                "ou fotografe na aba Mapa livre.")
    nome = "Mapa livre" if outra == "livre" else ABAS[outra].nome
    return f"Isso parece ser da aba {nome}: lá esta foto vale pontos."


# Chat com amigos (servidor/chat.py): importado no fim porque usa a sessão e as capturas daqui
from servidor import chat  # noqa: E402

app.include_router(chat.router)
