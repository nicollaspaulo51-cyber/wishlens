"""Regras do jogo: foto repetida, pontos e pódio. Só funções (sem Streamlit), para testar.

Pontos de cada captura (recalculados sempre a partir das capturas, em ordem de data):
- base: 10;
- novidade: +10 se a pessoa nunca tinha achado isso;
- raridade: +20 / (1 + vezes que alguém já achou isso antes): o 1º ganha 20, o 2º 10, o 3º 7...;
- tema do dia: tudo vezes 2;
- achado genérico (ex.: só "carro", quando a IA não disse o modelo): só a base.
Extras (coluna "extra", fora do ×2): mirante, chuva, lupa, desafios do dia, corrente de 7 dias e meta da turma
(ver "mecânicas de caminhada" abaixo).
Vale 0, com o motivo, se não for foto real, se for foto repetida (do mesmo achado) ou do mesmo objeto que a
pessoa já fotografou (vetor do CLIP), se não for de nenhum tema
se a pessoa já achou a mesma coisa no mesmo dia ou se "andou" rápido demais desde a foto anterior.

Como os pontos saem das capturas, um número falso gravado no banco não vale nada, e a
raridade de cada captura só olha as que vieram antes (não muda depois).
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
from PIL import Image, ImageOps

from src.temas import POR_ID, TEMAS, dia_de, tema_do_dia

BASE, NOVIDADE, RARIDADE, MULTIPLICADOR_DO_DIA = 10, 10, 20, 2
LIMITE_HASH = 6  # bits diferentes no dHash de 64 bits: até isso é a mesma foto

# Apelidos de marca: "VW Gol" e "Volkswagen Gol" contam como o mesmo achado
APELIDOS = {"vw": "volkswagen", "volks": "volkswagen", "chevy": "chevrolet", "gm": "chevrolet",
            "mercedes": "mercedes-benz", "mb": "mercedes-benz", "benz": "mercedes-benz",
            "vira lata": "vira-lata", "srd": "vira-lata"}

COLUNAS_PONTOS = ["pontos", "base", "novidade", "raridade", "do_dia", "extra", "lupa", "meta", "detalhes",
                  "aceita", "motivo"]

# Achado genérico (só "carro", "pássaro"...): vale só a base, e até LIMITE_GENERICO_DIA vezes por tema
# por dia (sem o limite de "já achou hoje", que recusava o 2º carro de verdade sem modelo).
LIMITE_GENERICO_DIA = 3
GENERICOS = {"carro", "passaro", "planta", "cachorro", "gato", "cachorro ou gato", "peca de computador",
             "ave", "flor", "arvore"}


def eh_generico(tema_id: str, chave: str) -> bool:
    """O achado é só o nome do tema/categoria, sem modelo, espécie ou raça (chave já normalizada)."""
    return chave == normalizar(POR_ID[tema_id].generico) or chave in GENERICOS

# Segundo juiz (CLIP) ao lado da IA (juiz principal, src/visao.py): só barra quando discorda com clareza, porque sozinho ele erra
# bastante (pássaro pequeno na foto, carro de longe). Ajustar depois de ver os dados da turma.
# O CLIP é muito "confiante" (escala ~100 nas similaridades): uma diferença pequena de parecença vira
# 95% x 5%. Por isso a discordância de tema usa a POSIÇÃO do tema da IA entre os palpites do CLIP
# (1 = o preferido dele), não a chance. Com 7 grupos (5 temas, tela, nenhum), ficar fora dos 2 primeiros
# é discordar com clareza.
VETO_RANK = 2     # o CLIP barra se o tema da IA ficar além desta posição
VETO_TELA = 0.5   # só para capturas antigas, sem clip_foto_real: chance mínima de "tela" para barrar
# Com os dois juízes, o CLIP só derruba o "é real" da IA se "tela" for bem mais provável que o tema
# (o grupo "tela" tem ~90 frases e sempre leva alguma vantagem pequena). Sozinho, vale o 1º palpite.
RAZAO_TELA = 3
VETO_TEMA = 0.10  # só para capturas antigas, sem a posição gravada


def _valor(x):
    """None para vazio/NaN (colunas opcionais do banco)."""
    if x is None or (isinstance(x, float) and pd.isna(x)) or x is pd.NA:
        return None
    return x


# O juiz principal era o Gemma (licença não OSI) e foi trocado por um modelo open source: capturas
# antigas gravaram "gemma"/"gemma+clip" e são lidas como "ia"/"ia+clip".
JUIZ_ANTIGO = {"gemma+clip": "ia+clip", "gemma": "ia"}


def normalizar_juiz(juiz) -> str | None:
    v = _valor(juiz)
    return JUIZ_ANTIGO.get(v, v)


def posicao(probs: dict[str, float], grupo: str) -> int:
    """Posição do grupo entre os palpites do CLIP (1 = o mais provável)."""
    ordem = sorted(probs, key=probs.get, reverse=True)
    return ordem.index(grupo) + 1 if grupo in ordem else len(ordem) + 1


def veto_clip(tema: str | None, juiz: str | None, clip_tema: str | None,
              clip_prob_tema: float | None, clip_prob_tela: float | None,
              clip_rank_tema: int | None = None, clip_foto_real: bool | None = None) -> str | None:
    """Motivo para o CLIP barrar a foto que a IA aceitou, ou None. Só vale com os dois juízes.

    Tela: barra se "tela/impressão" foi o 1º palpite do CLIP (clip_foto_real falso), mesmo que a
    IA tenha dito que é real. Não vale para peças de computador (monitor ligado é peça).
    """
    if normalizar_juiz(juiz) != "ia+clip" or not tema:
        return None
    tela, prob_tema, rank = _valor(clip_prob_tela), _valor(clip_prob_tema), _valor(clip_rank_tema)
    clip_real = _valor(clip_foto_real)
    if tela is not None and prob_tema is not None:
        viu_tela = tela >= RAZAO_TELA * prob_tema and (clip_real is None or not bool(clip_real))
    elif clip_real is not None:
        viu_tela = not bool(clip_real)
    else:
        viu_tela = tela is not None and tela >= VETO_TELA
    if viu_tela and tema != "pecas":
        return "o CLIP viu uma tela ou impressão"
    discorda = int(rank) > VETO_RANK if rank is not None else (prob_tema is not None and prob_tema < VETO_TEMA)
    if discorda:
        nome = POR_ID[tema].nome.lower()
        outro = POR_ID[clip_tema].nome.lower() if _valor(clip_tema) in POR_ID else "nenhum tema"
        return f"os juízes discordaram do tema (IA: {nome}; CLIP: {outro})"
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


# ---------------------------------------------------------------- mecânicas de caminhada
# Os campos de contexto (mirante, clima, km_anterior, min_anterior) são gravados pelo app na hora da foto,
# sem a localização exata; os bônus saem daqui, recalculados como os pontos.
MIRANTE, MIRANTES_DIA, MIRANTE_M = 5, 3, 40          # foto a até 40 m de um lugar do mapa: +5, até 3 por dia
CHUVA, TEMAS_CHUVA = 5, ("plantas", "passaros")      # com chuva, plantas e pássaros dão +5 (fora do tema do dia)
LUPA_TEMAS, LUPA_BONUS = 3, 0.5                      # 3 temas diferentes no dia enchem a lupa: o próximo achado +50%
DESAFIO = 15                                         # cada desafio do dia cumprido
CORRENTE, CORRENTE_DIAS = 20, 7                      # 7 dias seguidos com foto aceita
META, META_FOTOS, META_HORAS = 10, 20, (12, 14)      # meta da turma: 20 fotos do tema do dia das 12h às 14h
LONGE_KM, VELOCIDADE_MAX = 3, 120                    # >3 km a >120 km/h desde a foto anterior: não vale


def deslocamento_impossivel(km, minutos) -> bool:
    """Andou mais de 3 km a mais de 120 km/h desde a foto anterior (GPS falso ou foto de outro lugar)."""
    km, minutos = _valor(km), _valor(minutos)
    if km is None or minutos is None or float(km) <= LONGE_KM:
        return False
    return float(km) / max(float(minutos), 1.0) * 60 > VELOCIDADE_MAX


@dataclass(frozen=True)
class Desafio:
    id: str
    texto: str
    medida: str   # "temas", "fotos", "raros", "especificos", "mirantes" ou "tema:<id>"
    alvo: int


def desafios_do_dia(dia: date | None = None) -> list[Desafio]:
    """3 desafios sorteados pela data: todo mundo tem os mesmos no mesmo dia."""
    dia = dia or dia_de(None)
    rng = random.Random(dia.toordinal() * 31 + 7)
    outro = rng.choice([t for t in TEMAS if t.id != tema_do_dia(dia).id])
    n = rng.choice([2, 3])
    opcoes = [
        Desafio("temas", f"Fotografe {n + 1} temas diferentes", "temas", n + 1),
        Desafio("tema", f"Ache {n} {outro.nome.lower()} diferentes", f"tema:{outro.id}", n),
        Desafio("raro", "Ache algo que a turma ainda não achou", "raros", 1),
        Desafio("especificos", f"{n + 1} achados com modelo, espécie ou raça", "especificos", n + 1),
        Desafio("mirante", "Fotografe num mirante (a até 40 m de um lugar do mapa)", "mirantes", 1),
        Desafio("fotos", f"Tenha {n + 3} fotos aceitas hoje", "fotos", n + 3),
    ]
    return rng.sample(opcoes, 3)


def _novo_dia() -> dict:
    return {"temas": set(), "por_tema": Counter(), "raros": 0, "especificos": 0, "mirantes": 0, "fotos": 0}


def _somar(est: dict, tema: str, generico: bool, raro: bool, mirante: bool) -> None:
    est["temas"].add(tema)
    est["por_tema"][tema] += 1
    est["raros"] += raro
    est["especificos"] += not generico
    est["mirantes"] += mirante
    est["fotos"] += 1


def progresso(est: dict, d: Desafio) -> int:
    if d.medida.startswith("tema:"):
        return est["por_tema"][d.medida[5:]]
    v = est[d.medida]
    return len(v) if isinstance(v, set) else int(v)


# ---------------------------------------------------------------- mesmo objeto
# Semelhança mínima entre os vetores do CLIP de duas fotos para dizer que são o mesmo objeto.
# shortcut: 0,92 foi escolhido sem fotos reais da turma; calibrar com as capturas (pares iguais x diferentes)
# e, se o CLIP confundir objetos parecidos da mesma espécie/modelo, trocar o vetor pelo DINOv2 (Apache 2.0).
MESMO_OBJETO = 0.92


def objeto_visto(vetor: list[float] | None, eu: str, celula: str | None,
                 anteriores: list[tuple[str, str | None, list[float] | None]],
                 limiar: float = MESMO_OBJETO) -> str | None:
    """'seu' (você já fotografou este mesmo objeto), 'turma' (alguém fotografou no mesmo quadrado) ou None.

    anteriores: (usuario, celula, vetor) das fotos do mesmo tema. As suas valem em qualquer lugar; as da turma,
    só no mesmo quadrado de ~500 m (dois carros iguais em bairros diferentes não são o mesmo carro).
    Mesma regra da função objeto_visto do banco (supabase/schema.sql).
    """
    if not vetor:
        return None
    turma = False
    for usuario, cel, outro in anteriores:
        if not outro or (usuario != eu and (celula is None or cel != celula)):
            continue
        if sum(a * b for a, b in zip(vetor, outro)) >= limiar:
            if usuario == eu:
                return "seu"
            turma = True
    return "turma" if turma else None


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
    dias_usuario: dict[tuple[str, date], dict] = {}        # estatísticas do dia (desafios)
    feitos: dict[tuple[str, date], set[str]] = {}          # desafios já cumpridos
    lupa: dict[tuple[str, date], set[str]] = {}            # temas que carregaram a lupa
    mirantes_dia: Counter = Counter()
    corrente: dict[str, tuple[date, int]] = {}             # último dia com foto aceita e dias seguidos
    desafios: dict[date, list[Desafio]] = {}
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
        km, minutos = getattr(c, "km_anterior", None), getattr(c, "min_anterior", None)
        if real is not None and not pd.isna(real) and not bool(real):
            motivo = "não é foto real (tela, impressão ou desenho)"
        elif deslocamento_impossivel(km, minutos):
            motivo = (f"deslocamento impossível ({float(km):.0f} km em {max(float(minutos), 1):.0f} min "
                      "desde a foto anterior)")
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
        elif _valor(getattr(c, "mesmo_objeto", None)) == "seu":
            motivo = "você já fotografou este mesmo objeto"
        elif not generico_ and (c.usuario, tema.id, chave, dia) in vistos_no_dia:
            motivo = "você já achou isso hoje"
        elif generico_ and genericos_dia.get((c.usuario, tema.id, dia), 0) >= LIMITE_GENERICO_DIA:
            motivo = (f"limite de {LIMITE_GENERICO_DIA} fotos genéricas de {tema.nome.lower()} hoje: "
                      "diga o modelo, a espécie ou a raça para ganhar mais")
        if motivo:
            linhas.append({"pontos": 0, "base": 0, "novidade": 0, "raridade": 0, "do_dia": do_dia, "extra": 0,
                           "lupa": 0, "meta": 0, "detalhes": "", "aceita": False, "motivo": motivo})
            continue

        generico = generico_
        if generico:
            genericos_dia[(c.usuario, tema.id, dia)] = genericos_dia.get((c.usuario, tema.id, dia), 0) + 1
        novo = not generico and (c.usuario, tema.id, chave) not in vistos_usuario
        anteriores = contagem.get((tema.id, chave), 0)
        # objeto que a turma já fotografou ali não é achado novo: vale, mas sem bônus de raridade
        ja_da_turma = _valor(getattr(c, "mesmo_objeto", None)) == "turma"
        rar = 0 if generico or ja_da_turma else round(RARIDADE / (1 + anteriores))
        principal = (BASE + (NOVIDADE if novo else 0) + rar) * (MULTIPLICADOR_DO_DIA if do_dia else 1)
        detalhes: list[str] = []
        chave_dia = (c.usuario, dia)

        mirante = bool(_valor(getattr(c, "mirante", None)))
        bonus_mirante = MIRANTE if mirante and mirantes_dia[chave_dia] < MIRANTES_DIA else 0
        if bonus_mirante:
            mirantes_dia[chave_dia] += 1
            detalhes.append(f"mirante +{MIRANTE}")
        bonus_chuva = CHUVA if (_valor(getattr(c, "clima", None)) == "chuva" and tema.id in TEMAS_CHUVA
                                and not do_dia) else 0
        if bonus_chuva:
            detalhes.append(f"chuva +{CHUVA}")

        carga = lupa.setdefault(chave_dia, set())
        bonus_lupa = 0
        if len(carga) >= LUPA_TEMAS:  # lupa cheia: este achado ganha +50% e ela esvazia
            bonus_lupa = round(principal * LUPA_BONUS)
            carga.clear()
            detalhes.append(f"lupa cheia +{bonus_lupa}")
        else:
            carga.add(tema.id)

        ultimo, seguidos = corrente.get(c.usuario, (None, 0))
        bonus_corrente = 0
        if ultimo != dia:
            seguidos = seguidos + 1 if ultimo == dia - timedelta(days=1) else 1
            corrente[c.usuario] = (dia, seguidos)
            if seguidos % CORRENTE_DIAS == 0:
                bonus_corrente = CORRENTE
                detalhes.append(f"corrente de {seguidos} dias +{CORRENTE}")

        est = dias_usuario.setdefault(chave_dia, _novo_dia())
        _somar(est, tema.id, generico, raro=not generico and anteriores == 0, mirante=mirante)
        bonus_desafio = 0
        cumpridos = feitos.setdefault(chave_dia, set())
        for d in desafios.setdefault(dia, desafios_do_dia(dia)):
            if d.id not in cumpridos and progresso(est, d) >= d.alvo:
                cumpridos.add(d.id)
                bonus_desafio += DESAFIO
                detalhes.append(f"desafio: {d.texto[0].lower() + d.texto[1:]} +{DESAFIO}")

        extra = bonus_mirante + bonus_chuva + bonus_lupa + bonus_corrente + bonus_desafio
        linhas.append({"pontos": principal + extra, "base": BASE,
                       "novidade": NOVIDADE if novo else 0, "raridade": rar, "do_dia": do_dia, "extra": extra,
                       "lupa": bonus_lupa, "meta": 0, "detalhes": "; ".join(detalhes),
                       "aceita": True, "motivo": None})
        vistos_usuario.add((c.usuario, tema.id, chave))
        vistos_no_dia.add((c.usuario, tema.id, chave, dia))
        contagem[(tema.id, chave)] = anteriores + 1
        if h:
            hashes.setdefault((tema.id, chave), []).append(h)
    pontos = pd.DataFrame(linhas, columns=COLUNAS_PONTOS)
    _meta_da_turma(df, pontos)
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


# ---------------------------------------------------------------- mecânicas: o que a tela mostra
def _na_meta(criado_em, do_dia, aceita) -> bool:
    return bool(aceita) and bool(do_dia) and META_HORAS[0] <= pd.Timestamp(criado_em).hour < META_HORAS[1]


def _meta_da_turma(capturas: pd.DataFrame, pontos: pd.DataFrame) -> None:
    """Se a turma fez META_FOTOS fotos do tema do dia na janela, cada uma delas ganha +META (todos ganham juntos)."""
    if pontos.empty:
        return
    na_janela = [_na_meta(t, d, a) for t, d, a in zip(capturas["criado_em"], pontos["do_dia"], pontos["aceita"])]
    dias = [dia_de(pd.Timestamp(x).to_pydatetime()) for x in capturas["criado_em"]]
    contagem = Counter(d for d, ok in zip(dias, na_janela) if ok)
    for i, (d, ok) in enumerate(zip(dias, na_janela)):
        if ok and contagem[d] >= META_FOTOS:
            pontos.at[i, "meta"] = META
            pontos.at[i, "extra"] += META
            pontos.at[i, "pontos"] += META
            pontos.at[i, "detalhes"] = "; ".join(filter(None, [pontos.at[i, "detalhes"], f"meta da turma +{META}"]))


def meta_da_turma(pontuadas: pd.DataFrame, agora: datetime | None = None) -> dict:
    """Meta de hoje: feitas, alvo, aberta (estamos na janela), cumprida, faltam_min, comeca, termina, tema."""
    agora = agora or agora_naive()
    hoje = dia_de(agora)
    feitas = 0
    if not pontuadas.empty:
        df = no_periodo(pontuadas, "hoje", hoje)
        feitas = sum(_na_meta(t, d, a) for t, d, a in zip(df["criado_em"], df["do_dia"], df["aceita"]))
    inicio = agora.replace(hour=META_HORAS[0], minute=0, second=0, microsecond=0)
    fim = agora.replace(hour=META_HORAS[1], minute=0, second=0, microsecond=0)
    return {"feitas": int(feitas), "alvo": META_FOTOS, "aberta": inicio <= agora < fim,
            "cumprida": feitas >= META_FOTOS, "faltam_min": max(0, int((fim - agora).total_seconds() // 60)),
            "comeca": f"{META_HORAS[0]}h", "termina": f"{META_HORAS[1]}h", "tema": tema_do_dia(hoje)}


def estado_do_dia(pontuadas: pd.DataFrame, usuario: str, dia: date | None = None) -> dict:
    """Para a tela: carga da lupa (0-3) e progresso de cada desafio do dia (repete o que calcular_pontos fez)."""
    dia = dia or dia_de(None)
    est, carga = _novo_dia(), set()
    if not pontuadas.empty:
        df = no_periodo(pontuadas, "hoje", dia)
        for r in df[(df["usuario"] == usuario) & df["aceita"]].itertuples():
            generico = eh_generico(r.tema, normalizar(r.achado))
            # raridade máxima = ninguém tinha achado antes
            _somar(est, r.tema, generico, raro=not generico and r.raridade == RARIDADE,
                   mirante=bool(_valor(getattr(r, "mirante", None))))
            if r.lupa:
                carga.clear()
            else:
                carga.add(r.tema)
    desafios = [{"texto": d.texto, "feito": min(progresso(est, d), d.alvo), "alvo": d.alvo,
                 "ok": progresso(est, d) >= d.alvo} for d in desafios_do_dia(dia)]
    return {"lupa": min(len(carga), LUPA_TEMAS), "lupa_cheia": len(carga) >= LUPA_TEMAS, "desafios": desafios}


def corrente_atual(pontuadas: pd.DataFrame, usuario: str, hoje: date | None = None) -> int:
    """Dias seguidos com foto aceita até hoje (ou até ontem, se ainda não jogou hoje)."""
    hoje = hoje or dia_de(None)
    if pontuadas.empty:
        return 0
    meus = pontuadas[(pontuadas["usuario"] == usuario) & pontuadas["aceita"]]
    dias = {dia_de(pd.Timestamp(x).to_pydatetime()) for x in meus["criado_em"]}
    d = hoje if hoje in dias else hoje - timedelta(days=1)
    n = 0
    while d in dias:
        n, d = n + 1, d - timedelta(days=1)
    return n


# Medalhas: (id, nome, o que conta). Níveis pela quantidade.
MEDALHAS = [("passaros", "Olho de águia", "pássaros diferentes"), ("plantas", "Mão verde", "plantas diferentes"),
            ("carros", "Garagem cheia", "carros diferentes"), ("pets", "Amigo dos bichos", "pets diferentes"),
            ("pecas", "Garimpo tech", "peças diferentes"), ("mirantes", "Andarilho", "fotos em mirantes")]
NIVEIS = [("bronze", 3), ("prata", 8), ("ouro", 15)]


def medalhas(pontuadas: pd.DataFrame, usuario: str) -> list[dict]:
    """Cada medalha: id, nome, conta, nivel (None, "bronze", "prata", "ouro"), valor, proximo (quanto falta)."""
    meus = pontuadas[(pontuadas["usuario"] == usuario) & pontuadas["aceita"]] if not pontuadas.empty else pontuadas
    saida = []
    for mid, nome, conta in MEDALHAS:
        if meus.empty:
            valor = 0
        elif mid == "mirantes":
            valor = int(sum(bool(_valor(v)) for v in meus["mirante"])) if "mirante" in meus else 0
        else:
            chaves = {normalizar(a) for a in meus.loc[meus["tema"] == mid, "achado"]}
            valor = sum(1 for k in chaves if k and not eh_generico(mid, k))
        nivel = None
        for n, minimo in NIVEIS:
            if valor >= minimo:
                nivel = n
        proximo = next((minimo - valor for _, minimo in NIVEIS if valor < minimo), 0)
        saida.append({"id": mid, "nome": nome, "conta": conta, "nivel": nivel, "valor": valor, "proximo": proximo})
    return saida


def lacunas(pontuadas: pd.DataFrame, usuario: str, tema: str, limite: int = 5) -> list[tuple[str, int]]:
    """Achados específicos que a turma já tem e você não: (dica com a 1ª letra, vezes na turma)."""
    if pontuadas.empty:
        return []
    ok = pontuadas[pontuadas["aceita"] & (pontuadas["tema"] == tema)]
    chaves = ok["achado"].map(normalizar)
    meus = set(chaves[ok["usuario"] == usuario])
    outros = Counter(k for k, u in zip(chaves, ok["usuario"])
                     if u != usuario and k and k not in meus and not eh_generico(tema, k))
    return [(k[0].upper() + "…", n) for k, n in outros.most_common(limite)]


def pistas_por_tipo(pontuadas: pd.DataFrame, limite: int = 3) -> dict[str, list[str]]:
    """O que a turma mais achou em cada tipo de lugar do mapa (parque, pet shop...): a pista do mirante."""
    if pontuadas.empty or "tipo_lugar" not in pontuadas:
        return {}
    ok = pontuadas[pontuadas["aceita"] & pontuadas["tipo_lugar"].map(lambda v: bool(_valor(v)))]
    saida = {}
    for tipo, g in ok.groupby("tipo_lugar"):
        especificos = [a for t, a in zip(g["tema"], g["achado"]) if not eh_generico(t, normalizar(a))]
        saida[str(tipo)] = [a for a, _ in Counter(especificos).most_common(limite)]
    return saida


def guardioes(capturas: pd.DataFrame, hoje: date | None = None) -> pd.DataFrame:
    """Guardião de cada quadrado de ~500 m na semana: quem tem mais achados diferentes ali.

    Só quadrados onde ≥2 pessoas fotografaram (ninguém aparece sozinho num lugar). Empate: quem chegou antes.
    A mesma regra está em supabase/schema.sql (guardioes_quadrados), para o banco.
    """
    colunas = ["celula", "usuario", "achados"]
    if capturas.empty or "celula" not in capturas:
        return pd.DataFrame(columns=colunas)
    df = no_periodo(capturas, "semana", hoje)
    df = df[df["celula"].map(lambda v: bool(_valor(v))) & df["foto_real"].astype(bool) & (df["tema"] != "nenhum")]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    df = df.assign(chave=df["tema"] + ":" + df["achado"].map(normalizar))
    por = (df.groupby(["celula", "usuario"]).agg(achados=("chave", "nunique"), primeiro=("criado_em", "min"))
           .reset_index())
    por = por[por.groupby("celula")["usuario"].transform("size") >= 2]
    por = por.sort_values(["celula", "achados", "primeiro"], ascending=[True, False, True])
    return por.drop_duplicates("celula")[colunas].reset_index(drop=True)


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
    """Compara o CLIP e a IA (juiz principal) nas fotos em que os dois julgaram.

    Devolve: comparadas, concordancia (0-1), matriz (IA x CLIP, contagens), por_tema (concordância
    por tema da IA), vetos (por motivo), recusas (por motivo), especificos (fração de achados com
    modelo/espécie/raça entre as aceitas pela IA) e contestadas (o que as pessoas disseram que era).
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

    ambos = df[df["juiz"].map(normalizar_juiz) == "ia+clip"].copy()
    if not ambos.empty:
        ambos["ia"] = ambos["tema"].map(nome)
        ambos["clip"] = ambos["clip_tema"].map(lambda t: nome(_valor(t)))
        ambos["concorda"] = ambos["ia"] == ambos["clip"]
        saida["comparadas"] = len(ambos)
        saida["concordancia"] = float(ambos["concorda"].mean())
        saida["matriz"] = pd.crosstab(ambos["ia"], ambos["clip"]).rename_axis(index="IA", columns="CLIP")
        saida["por_tema"] = ambos.groupby("ia")["concorda"].mean().drop("nenhum", errors="ignore").sort_values()
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
