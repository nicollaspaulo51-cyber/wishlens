"""Regras do jogo: foto repetida, pontos e pódio. Só funções (sem Streamlit), para testar.

Pontos de cada captura (recalculados sempre a partir das capturas, em ordem de data):
- base: 10;
- novidade: +10 se a pessoa nunca tinha achado isso;
- raridade: +20 / (1 + vezes que alguém já achou isso antes): o 1º ganha 20, o 2º 10, o 3º 7...;
- tema do dia: tudo vezes 2;
- achado genérico (ex.: só "carro", quando a IA não disse o modelo): só a base.
Vale 0, com o motivo, se não for foto real, se for foto repetida (do mesmo achado), se não for de nenhum tema
ou se a pessoa já achou a mesma coisa no mesmo dia.

Como os pontos saem das capturas, um número falso gravado no banco não vale nada, e a
raridade de cada captura só olha as que vieram antes (não muda depois).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd
from PIL import Image, ImageOps

from src.temas import POR_ID, dia_de, tema_do_dia

BASE, NOVIDADE, RARIDADE, MULTIPLICADOR_DO_DIA = 10, 10, 20, 2
LIMITE_HASH = 6  # bits diferentes no dHash de 64 bits: até isso é a mesma foto

# Apelidos de marca: "VW Gol" e "Volkswagen Gol" contam como o mesmo achado
APELIDOS = {"vw": "volkswagen", "volks": "volkswagen", "chevy": "chevrolet", "gm": "chevrolet",
            "mercedes": "mercedes-benz", "mb": "mercedes-benz", "benz": "mercedes-benz",
            "vira lata": "vira-lata", "srd": "vira-lata"}

COLUNAS_PONTOS = ["pontos", "base", "novidade", "raridade", "do_dia", "aceita", "motivo"]

# Achado genérico (só "carro", "pássaro"...): vale só a base, e até LIMITE_GENERICO_DIA vezes por tema
# por dia (sem o limite de "já achou hoje", que recusava o 2º carro de verdade sem modelo).
LIMITE_GENERICO_DIA = 3
GENERICOS = {"carro", "passaro", "planta", "cachorro", "gato", "cachorro ou gato", "peca de computador",
             "ave", "flor", "arvore"}


def eh_generico(tema_id: str, chave: str) -> bool:
    """O achado é só o nome do tema/categoria, sem modelo, espécie ou raça (chave já normalizada)."""
    return chave == normalizar(POR_ID[tema_id].generico) or chave in GENERICOS

# Segundo juiz (CLIP) ao lado do Gemma: só barra quando discorda com clareza, porque sozinho ele erra
# bastante (pássaro pequeno na foto, carro de longe). Ajustar depois de ver os dados da turma.
# O CLIP é muito "confiante" (escala ~100 nas similaridades): uma diferença pequena de parecença vira
# 95% x 5%. Por isso a discordância de tema usa a POSIÇÃO do tema do Gemma entre os palpites do CLIP
# (1 = o preferido dele), não a chance. Com 7 grupos (5 temas, tela, nenhum), ficar fora dos 2 primeiros
# é discordar com clareza.
VETO_RANK = 2     # o CLIP barra se o tema do Gemma ficar além desta posição
VETO_TELA = 0.5   # só para capturas antigas, sem clip_foto_real: chance mínima de "tela" para barrar
VETO_TEMA = 0.10  # só para capturas antigas, sem a posição gravada


def _valor(x):
    """None para vazio/NaN (colunas opcionais do banco)."""
    if x is None or (isinstance(x, float) and pd.isna(x)) or x is pd.NA:
        return None
    return x


def posicao(probs: dict[str, float], grupo: str) -> int:
    """Posição do grupo entre os palpites do CLIP (1 = o mais provável)."""
    ordem = sorted(probs, key=probs.get, reverse=True)
    return ordem.index(grupo) + 1 if grupo in ordem else len(ordem) + 1


def veto_clip(tema: str | None, juiz: str | None, clip_tema: str | None,
              clip_prob_tema: float | None, clip_prob_tela: float | None,
              clip_rank_tema: int | None = None, clip_foto_real: bool | None = None) -> str | None:
    """Motivo para o CLIP barrar a foto que o Gemma aceitou, ou None. Só vale com os dois juízes.

    Tela: barra se "tela/impressão" foi o 1º palpite do CLIP (clip_foto_real falso), mesmo que o
    Gemma tenha dito que é real. Não vale para peças de computador (monitor ligado é peça).
    """
    if _valor(juiz) != "gemma+clip" or not tema:
        return None
    tela, prob_tema, rank = _valor(clip_prob_tela), _valor(clip_prob_tema), _valor(clip_rank_tema)
    clip_real = _valor(clip_foto_real)
    viu_tela = (not bool(clip_real)) if clip_real is not None else (tela is not None and tela >= VETO_TELA)
    if viu_tela and tema != "pecas":
        return "o CLIP viu uma tela ou impressão"
    discorda = int(rank) > VETO_RANK if rank is not None else (prob_tema is not None and prob_tema < VETO_TEMA)
    if discorda:
        nome = POR_ID[tema].nome.lower()
        outro = POR_ID[clip_tema].nome.lower() if _valor(clip_tema) in POR_ID else "nenhum tema"
        return f"os juízes discordaram do tema (Gemma: {nome}; CLIP: {outro})"
    return None


# ---------------------------------------------------------------- achados
def normalizar(achado: str | None) -> str:
    """Minúsculas, sem acento, sem pontuação e com apelidos trocados: chave de comparação."""
    texto = unicodedata.normalize("NFKD", str(achado or "")).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9 -]+", " ", texto.lower())
    texto = re.sub(r"\s+", " ", texto).strip()
    for apelido, nome in APELIDOS.items():
        texto = re.sub(rf"(?<![\w-]){re.escape(apelido)}(?![\w-])", nome, texto)
    return texto


# ---------------------------------------------------------------- foto repetida
def hash_foto(imagem: Image.Image) -> str:
    """dHash de 64 bits (16 caracteres hex): igual para a mesma foto reduzida ou recomprimida."""
    cinza = ImageOps.exif_transpose(imagem).convert("L").resize((9, 8), Image.LANCZOS)
    px = list(cinza.tobytes())
    bits = 0
    for linha in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[linha * 9 + col] > px[linha * 9 + col + 1])
    return f"{bits:016x}"


def distancia(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def repetida(h: str | None, anteriores) -> bool:
    return bool(h) and any(distancia(h, x) <= LIMITE_HASH for x in anteriores if x)


# ---------------------------------------------------------------- pontos
def calcular_pontos(capturas: pd.DataFrame) -> pd.DataFrame:
    """Recebe as capturas (usuario, criado_em, tema, achado, foto_real, foto_hash) e devolve
    as mesmas linhas, em ordem de data, com as colunas de COLUNAS_PONTOS."""
    df = capturas.sort_values("criado_em", kind="stable").reset_index(drop=True).copy()
    vistos_usuario: set[tuple[str, str, str]] = set()
    vistos_no_dia: set[tuple[str, str, str, date]] = set()
    genericos_dia: dict[tuple[str, str, date], int] = {}
    contagem: dict[tuple[str, str], int] = {}
    # Foto repetida: compara só com fotos do mesmo achado (rápido e não pega fotos parecidas de
    # coisas diferentes, como dois pássaros contra o céu); foto reaproveitada recebe o mesmo achado do juiz.
    hashes: dict[tuple[str, str], list[str]] = {}
    linhas = []
    for c in df.itertuples(index=False):
        tema = POR_ID.get(getattr(c, "tema", None) or "")
        dia = dia_de(pd.Timestamp(c.criado_em).to_pydatetime())
        do_dia = bool(tema) and tema_do_dia(dia).id == tema.id
        chave = normalizar(getattr(c, "achado", ""))
        h = getattr(c, "foto_hash", None)
        h = h if isinstance(h, str) else None

        generico_ = bool(tema) and eh_generico(tema.id, chave)
        real = getattr(c, "foto_real", True)
        motivo = None
        if real is not None and not pd.isna(real) and not bool(real):
            motivo = "não é foto real (tela, impressão ou desenho)"
        elif tema is None:
            motivo = "não é de nenhum tema do jogo"
        elif veto := veto_clip(tema.id, getattr(c, "juiz", None), getattr(c, "clip_tema", None),
                               getattr(c, "clip_prob_tema", None), getattr(c, "clip_prob_tela", None),
                               getattr(c, "clip_rank_tema", None), getattr(c, "clip_foto_real", None)):
            motivo = veto
        elif not chave:
            motivo = "não deu para saber o que é"
        elif repetida(h, hashes.get((tema.id, chave), [])):
            motivo = "foto repetida"
        elif not generico_ and (c.usuario, tema.id, chave, dia) in vistos_no_dia:
            motivo = "você já achou isso hoje"
        elif generico_ and genericos_dia.get((c.usuario, tema.id, dia), 0) >= LIMITE_GENERICO_DIA:
            motivo = (f"limite de {LIMITE_GENERICO_DIA} fotos genéricas de {tema.nome.lower()} hoje: "
                      "diga o modelo, a espécie ou a raça para ganhar mais")
        if motivo:
            linhas.append({"pontos": 0, "base": 0, "novidade": 0, "raridade": 0, "do_dia": do_dia,
                           "aceita": False, "motivo": motivo})
            continue

        generico = generico_
        if generico:
            genericos_dia[(c.usuario, tema.id, dia)] = genericos_dia.get((c.usuario, tema.id, dia), 0) + 1
        novo = not generico and (c.usuario, tema.id, chave) not in vistos_usuario
        anteriores = contagem.get((tema.id, chave), 0)
        rar = 0 if generico else round(RARIDADE / (1 + anteriores))
        subtotal = BASE + (NOVIDADE if novo else 0) + rar
        linhas.append({"pontos": subtotal * (MULTIPLICADOR_DO_DIA if do_dia else 1), "base": BASE,
                       "novidade": NOVIDADE if novo else 0, "raridade": rar, "do_dia": do_dia,
                       "aceita": True, "motivo": None})
        vistos_usuario.add((c.usuario, tema.id, chave))
        vistos_no_dia.add((c.usuario, tema.id, chave, dia))
        contagem[(tema.id, chave)] = anteriores + 1
        if h:
            hashes.setdefault((tema.id, chave), []).append(h)
    pontos = pd.DataFrame(linhas, columns=COLUNAS_PONTOS)
    return pd.concat([df.drop(columns=[c for c in COLUNAS_PONTOS if c in df.columns]), pontos], axis=1)


def pontuar_nova(historico: pd.DataFrame, nova: dict) -> dict:
    """Pontos que uma captura nova receberia, dado o histórico (mostrado antes/depois de salvar)."""
    tudo = pd.concat([historico, pd.DataFrame([{**nova, "_nova": True}])], ignore_index=True)
    resultado = calcular_pontos(tudo)
    return resultado[resultado["_nova"].eq(True)].iloc[0].drop(labels="_nova").to_dict()


def vezes_achado(pontuadas: pd.DataFrame, tema: str, achado: str) -> int:
    """Quantas vezes a turma já achou isso (capturas aceitas)."""
    if pontuadas.empty:
        return 0
    ok = pontuadas[pontuadas["aceita"] & pontuadas["tema"].eq(tema)]
    return int((ok["achado"].map(normalizar) == normalizar(achado)).sum())


# ---------------------------------------------------------------- pódio
def no_periodo(pontuadas: pd.DataFrame, periodo: str, hoje: date | None = None) -> pd.DataFrame:
    """periodo: "hoje", "semana" (de segunda até hoje) ou "geral"."""
    if periodo == "geral" or pontuadas.empty:
        return pontuadas
    hoje = hoje or dia_de(None)
    dias = pontuadas["criado_em"].map(lambda x: dia_de(pd.Timestamp(x).to_pydatetime()))
    inicio = hoje if periodo == "hoje" else hoje - timedelta(days=hoje.weekday())
    return pontuadas[(dias >= inicio) & (dias <= hoje)]


def podio(pontuadas: pd.DataFrame, periodo: str = "hoje", tema: str | None = None,
          hoje: date | None = None) -> pd.DataFrame:
    """Ranking: usuario, pontos, achados, ultimo, posicao. Empate: quem chegou antes no total."""
    colunas = ["posicao", "usuario", "pontos", "achados", "ultimo"]
    df = no_periodo(pontuadas, periodo, hoje)
    if tema:
        df = df[df["tema"] == tema]
    df = df[df["aceita"]] if not df.empty else df
    if df.empty:
        return pd.DataFrame(columns=colunas)
    r = (df.groupby("usuario").agg(pontos=("pontos", "sum"), achados=("pontos", "size"),
                                    ultimo=("criado_em", "max"))
         .reset_index().sort_values(["pontos", "ultimo"], ascending=[False, True]))
    r["posicao"] = range(1, len(r) + 1)
    return r[colunas].reset_index(drop=True)


def posicao_de(ranking: pd.DataFrame, usuario: str) -> int | None:
    linha = ranking[ranking["usuario"] == usuario]
    return int(linha["posicao"].iloc[0]) if not linha.empty else None


def celula(lat: float | None, lon: float | None, passo: float = 0.005) -> str | None:
    """Quadrado de ~500 m (0,005°) onde a foto foi tirada: nunca a coordenada exata."""
    if lat is None or lon is None:
        return None
    return f"{round(round(lat / passo) * passo, 3):.3f},{round(round(lon / passo) * passo, 3):.3f}"


def centro_celula(c: str) -> tuple[float, float]:
    lat, lon = c.split(",")
    return float(lat), float(lon)


def agora_naive() -> datetime:
    """Agora no horário de Brasília, sem fuso (é assim que as capturas ficam no DataFrame)."""
    from src.temas import agora
    return agora().replace(tzinfo=None)


# Estilo de jogador (K-Means sobre a proporção de capturas por tema)
NOMES_ESTILO = {"carros": "Caçador de carros", "plantas": "Naturalista", "passaros": "Observador de aves",
                "pets": "Amigo dos bichos", "pecas": "Garimpeiro tech"}


def estilo_jogador(pontuadas: pd.DataFrame, usuario: str) -> str | None:
    from src.clustering import perfil_do_usuario
    from src.temas import TEMAS

    aceitas = pontuadas[pontuadas["aceita"]] if not pontuadas.empty else pontuadas
    if aceitas.empty:
        return None
    return perfil_do_usuario(aceitas, usuario, coluna="tema", valores=[t.id for t in TEMAS], nomes=NOMES_ESTILO)


# ---------------------------------------------------------------- avaliação dos juízes (CRISP-DM, fase 5)
def avaliar_juizes(pontuadas: pd.DataFrame) -> dict:
    """Compara CLIP e Gemma nas fotos em que os dois julgaram.

    Devolve: comparadas, concordancia (0-1), matriz (Gemma x CLIP, contagens), por_tema (concordância
    por tema do Gemma), vetos (por motivo), recusas (por motivo), especificos (fração de achados com
    modelo/espécie/raça entre as aceitas pelo Gemma) e contestadas (o que as pessoas disseram que era).
    """
    vazio = {"comparadas": 0, "concordancia": None, "matriz": pd.DataFrame(), "por_tema": pd.Series(dtype=float),
             "vetos": pd.Series(dtype=int), "recusas": pd.Series(dtype=int), "especificos": None,
             "contestadas": pd.DataFrame(columns=["tema_dito", "contestada", "vezes"])}
    if pontuadas.empty:
        return vazio
    df = pontuadas.copy()
    for col in ("juiz", "clip_tema", "contestada"):
        if col not in df:
            df[col] = None
    nome = lambda t: POR_ID[t].nome if t in POR_ID else "nenhum"  # noqa: E731
    saida = dict(vazio)
    saida["recusas"] = df.loc[~df["aceita"], "motivo"].value_counts()

    ambos = df[df["juiz"] == "gemma+clip"].copy()
    if not ambos.empty:
        ambos["gemma"] = ambos["tema"].map(nome)
        ambos["clip"] = ambos["clip_tema"].map(lambda t: nome(_valor(t)))
        ambos["concorda"] = ambos["gemma"] == ambos["clip"]
        saida["comparadas"] = len(ambos)
        saida["concordancia"] = float(ambos["concorda"].mean())
        saida["matriz"] = pd.crosstab(ambos["gemma"], ambos["clip"]).rename_axis(index="Gemma", columns="CLIP")
        saida["por_tema"] = ambos.groupby("gemma")["concorda"].mean().drop("nenhum", errors="ignore").sort_values()
        vetadas = ambos[ambos["motivo"].fillna("").str.contains("CLIP|juízes")]
        saida["vetos"] = vetadas["motivo"].str.replace(r" \(.*\)$", "", regex=True).value_counts()

        aceitas = ambos[ambos["aceita"]]
        if not aceitas.empty:
            genericos = aceitas.apply(lambda r: eh_generico(r["tema"], normalizar(r["achado"])), axis=1)
            saida["especificos"] = float(1 - genericos.mean())

    contest = df[df["contestada"].map(_valor).notna()]
    if not contest.empty:
        saida["contestadas"] = (contest.assign(tema_dito=contest["tema"].map(nome),
                                               contestada=contest["contestada"].map(nome))
                                .groupby(["tema_dito", "contestada"]).size().rename("vezes").reset_index()
                                .sort_values("vezes", ascending=False))
    return saida
