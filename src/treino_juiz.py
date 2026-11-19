"""Treino do juiz (CRISP-DM: modelagem e avaliação): uma camada aprendida em cima do CLIP.

O CLIP zero-shot (src/reconhecimento.py) só compara a foto com frases. Aqui ele ganha duas "sondas
lineares" treinadas com fotos de verdade (Open Images, scripts/baixar_fotos_treino.py):
- tema: os 5 temas do Mapa livre + "nenhum";
- falsa: a chance de ser foto de tela, impressão, desenho ou brinquedo (src/falsas.py gera tela e impressão).

A decisão final mistura a sonda com o zero-shot (α e β escolhidos na validação), para não perder o que o
CLIP já sabe. O resultado é um arquivo pequeno (modelos/juiz_clip.npz) que o juiz carrega se existir.

As funções de decisão (aplicar_sonda, zs_temas) são só numpy: dá para testar sem torch.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

ORDEM = ("carros", "plantas", "comidas", "pets", "pecas", "nenhum")
CAMINHO = Path(__file__).resolve().parent.parent / "modelos" / "juiz_clip.npz"
MAX_REAL_RECUSADA = 0.03  # na validação, no máximo 3% das fotos reais podem ser chamadas de falsas


# ---------------------------------------------------------------- decisão (usada pelo juiz)
@dataclass(frozen=True)
class Sonda:
    w_tema: np.ndarray   # (6, 512)
    b_tema: np.ndarray   # (6,)
    w_falsa: np.ndarray  # (512,)
    b_falsa: float
    alfa: float          # peso da sonda de tema (1 - alfa = zero-shot)
    beta: float          # peso da sonda de falsa
    limiar: float        # chance de falsa a partir da qual a foto não é real
    versao: str = ""
    # Junção com a IA (Qwen): ela só derruba o "é real" se a chance de falsa do CLIP passar deste limite
    # (sozinha ela recusava 1 em cada 3 fotos reais). 1.0 = a IA nunca derruba sozinha.
    limiar_ia: float = 0.0
    tema_da_ia: bool = True  # o tema vem da IA (com o achado detalhado) ou do CLIP treinado
    # Qual objeto é, dentro do tema (teclado x mouse x monitor...): tema -> (pesos, vieses, classes do Open Images)
    objetos: dict = field(default_factory=dict)
    # Qual MODELO ou marca é (Gol x Onix, mouse Logitech x Razer), aprendido com as fotos que a turma marcou:
    # tema -> (pesos, vieses, nomes dos modelos). Só existe para o tema que já tem exemplos suficientes de cada modelo.
    modelos: dict = field(default_factory=dict)


# Objetos de cada tema (classes do Open Images): nome em português e as palavras que o achado costuma ter.
# Classe sem palavras = o achado detalhado da IA (modelo do carro, espécie da flor) nunca é trocado por este nome.
OBJETOS: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    "carros": {"Car": ("carro", ()), "Van": ("van", ())},
    "plantas": {"Flower": ("flor", ()), "Houseplant": ("planta em vaso", ()), "Tree": ("árvore", ()), "Plant": ("planta", ())},
    "comidas": {"Apple": ("maçã", ("maca",)), "Banana": ("banana", ("banana",)), "Strawberry": ("morango", ("morango",)),
                "Bread": ("pão", ("pao", "pao frances")), "Baked goods": ("doce ou salgado", ()),
                "Fast food": ("lanche", ()), "Fruit": ("fruta", ()), "Vegetable": ("legume", ())},
    "pets": {"Dog": ("cachorro", ("cachorro", "cachorra")), "Cat": ("gato", ("gato", "gata")),
             "Bird": ("pássaro", ("passaro", "pombo", "bem te vi", "sabia", "periquito", "galinha", "pato", "tucano", "beija flor")),
             "Horse": ("cavalo", ("cavalo", "egua")), "Butterfly": ("borboleta", ("borboleta",)),
             "Lizard": ("lagarto", ("lagarto", "lagartixa"))},
    "pecas": {"Computer keyboard": ("teclado", ("teclado",)), "Computer monitor": ("monitor", ("monitor",)),
              "Computer mouse": ("mouse", ("mouse",)), "Laptop": ("notebook", ("notebook", "laptop")),
              "Headphones": ("fone de ouvido", ("fone", "headset", "headphone"))},
}
MINIMO_POR_MODELO = 8   # fotos de cada modelo para ele entrar no classificador
LIMIAR_MODELO = 0.8     # só troca o achado da IA quando tem bastante certeza (poucos exemplos = cuidado)
LIMIAR_OBJETO = 0.6  # abaixo disto o classificador de objeto não tem certeza e não mexe no achado


def classe_do_nome(tema: str, nome: str | None) -> str | None:
    """A classe de objeto que um nome em português diz ("teclado mecânico" -> Computer keyboard), ou None."""
    from src.jogo import normalizar

    x = f" {normalizar(nome)} "
    for classe, (_, palavras) in OBJETOS.get(tema, {}).items():
        if any(f" {p} " in x or f" {p}s " in x for p in palavras):
            return classe
    return None


def objeto(vetor, tema: str | None, s: Sonda) -> dict | None:
    """Qual objeto do tema é, pelo classificador treinado: {classe, nome, conf}, ou None (tema sem classificador)."""
    o = s.objetos.get(tema or "")
    if o is None:
        return None
    w, b, classes = o
    p = _softmax(np.asarray(w) @ np.asarray(vetor, dtype=np.float32) + np.asarray(b))
    i = int(p.argmax())
    return {"classe": classes[i], "nome": OBJETOS[tema][classes[i]][0], "conf": float(p[i])}


def modelo_de(vetor, tema: str | None, s: Sonda) -> dict | None:
    """Qual modelo ou marca é, pelo classificador da turma: {nome, conf}, ou None (tema sem exemplos suficientes)."""
    m = s.modelos.get(tema or "")
    if m is None:
        return None
    w, b, nomes = m
    p = _softmax(np.asarray(w) @ np.asarray(vetor, dtype=np.float32) + np.asarray(b))
    i = int(p.argmax())
    return {"nome": nomes[i], "conf": float(p[i])}


def escolher_achado(achado_ia: str, tema: str | None, obj: dict | None, modelo: dict | None = None) -> str:
    """O achado final: o da IA (detalhado), a não ser que ela diga OUTRO objeto do mesmo tema que o classificador
    reconhece com certeza (a IA disse "mouse", o classificador viu um teclado com 90%): aí vale o nome do objeto."""
    # O modelo aprendido com a turma (Gol, mouse Logitech G203...) vale quando tem bastante certeza
    if modelo and modelo["conf"] >= LIMIAR_MODELO:
        return modelo["nome"]
    if not obj or not tema or obj["conf"] < LIMIAR_OBJETO:
        return achado_ia
    if not achado_ia:
        return obj["nome"]
    dito = classe_do_nome(tema, achado_ia)
    return achado_ia if dito is None or dito == obj["classe"] else obj["nome"]


def juntar(ia_tema: str | None, ia_real: bool, clip_tema: str | None, clip_real: bool, falsa: float,
           s: Sonda) -> tuple[str | None, bool]:
    """Decisão final no Mapa livre com a IA e o CLIP treinado: (tema, foto_real)."""
    real = clip_real and not (not ia_real and falsa >= s.limiar_ia)
    return (ia_tema if s.tema_da_ia else clip_tema), real


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def zs_temas(por_grupo: dict[str, float]) -> np.ndarray:
    """Chances do zero-shot na ordem ORDEM (sem a tela). As outras abas ("outro:...") contam como nenhum."""
    v = np.array([por_grupo.get(t, 0.0) for t in ORDEM[:-1]]
                 + [por_grupo.get("nenhum", 0.0) + sum(p for g, p in por_grupo.items() if g.startswith("outro:"))])
    return v / (v.sum() or 1.0)


def aplicar_sonda(vetor, por_grupo: dict[str, float], s: Sonda) -> tuple[dict[str, float], str | None, bool, float]:
    """-> (chances novas por grupo, tema ou None, foto_real, confiança). As chances somam 1 e têm "tela"."""
    v = np.asarray(vetor, dtype=np.float32)
    mix = s.alfa * _softmax(s.w_tema @ v + s.b_tema) + (1 - s.alfa) * zs_temas(por_grupo)
    falsa = s.beta / (1 + np.exp(-(float(s.w_falsa @ v) + s.b_falsa))) + (1 - s.beta) * por_grupo.get("tela", 0.0)
    chances = {t: float((1 - falsa) * mix[i]) for i, t in enumerate(ORDEM)} | {"tela": float(falsa)}
    melhor = int(mix.argmax())
    tema = None if ORDEM[melhor] == "nenhum" else ORDEM[melhor]
    return chances, tema, bool(falsa < s.limiar), float(mix[melhor])


def salvar(s: Sonda, caminho: Path = CAMINHO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(caminho, w_tema=s.w_tema.astype(np.float32), b_tema=s.b_tema.astype(np.float32),
                        w_falsa=s.w_falsa.astype(np.float32), b_falsa=np.float32(s.b_falsa), alfa=np.float32(s.alfa),
                        beta=np.float32(s.beta), limiar=np.float32(s.limiar), ordem=np.array(ORDEM), versao=np.array(s.versao),
                        limiar_ia=np.float32(s.limiar_ia), tema_da_ia=np.array(s.tema_da_ia),
                        **{f"mod_{t}_{k}": v for t, (w, b, cl) in s.modelos.items()
                           for k, v in (("w", np.asarray(w, np.float32)), ("b", np.asarray(b, np.float32)), ("nomes", np.array(cl)))},
                        **{f"obj_{t}_{k}": v for t, (w, b, cl) in s.objetos.items()
                           for k, v in (("w", np.asarray(w, np.float32)), ("b", np.asarray(b, np.float32)), ("classes", np.array(cl)))})


def carregar(caminho: Path = CAMINHO) -> Sonda | None:
    """A sonda salva, ou None (sem arquivo, ou treinada para outros temas): aí o juiz usa só o zero-shot."""
    if not caminho.exists():
        return None
    d = np.load(caminho)
    if tuple(str(x) for x in d["ordem"]) != ORDEM:
        return None
    return Sonda(d["w_tema"], d["b_tema"], d["w_falsa"], float(d["b_falsa"]), float(d["alfa"]), float(d["beta"]),
                 float(d["limiar"]), str(d["versao"]), float(d["limiar_ia"]) if "limiar_ia" in d else 0.0,
                 bool(d["tema_da_ia"]) if "tema_da_ia" in d else True,
                 {t: (d[f"obj_{t}_w"], d[f"obj_{t}_b"], tuple(str(c) for c in d[f"obj_{t}_classes"]))
                  for t in OBJETOS if f"obj_{t}_w" in d},
                 {t: (d[f"mod_{t}_w"], d[f"mod_{t}_b"], tuple(str(c) for c in d[f"mod_{t}_nomes"]))
                  for t in OBJETOS if f"mod_{t}_w" in d})


# ---------------------------------------------------------------- dados
def parte(foto_id: str) -> str:
    """treino / validacao / teste pela foto ORIGINAL: as versões tela e impressa de uma foto ficam juntas."""
    n = int(hashlib.md5(foto_id.encode()).hexdigest()[:8], 16) % 100
    return "treino" if n < 70 else "validacao" if n < 85 else "teste"


def variantes(grupo: str, real: bool) -> list[str]:
    if not real:  # brinquedo e desenho já são falsas
        return ["original", "celular"]
    return ["original", "celular", "tela", "impressa"]


def gerar(foto, variante: str, foto_id: str):
    """A versão pedida da foto, sempre igual para o mesmo id (dá para refazer na avaliação com a IA)."""
    from src import falsas

    rng = random.Random(f"{foto_id}:{variante}")
    if variante == "original":
        return foto.convert("RGB")
    if variante == "celular":
        return falsas.como_celular(foto, rng)
    if variante == "tela":
        return falsas.como_celular(falsas.na_tela(foto, rng), rng)
    return falsas.como_celular(falsas.impressa(foto, rng), rng)


def extrair(pasta: Path, saida: Path) -> pd.DataFrame:
    """Passa todas as versões de todas as fotos pelo CLIP do juiz. Guarda vetor e chances zero-shot (pickle;
    se parar no meio, continua de onde estava)."""
    from PIL import Image

    from src.reconhecimento import julgar_clip

    fotos = pd.read_csv(pasta / "fotos.csv")
    feitas = pd.read_pickle(saida) if saida.exists() else pd.DataFrame()
    prontas = set(zip(feitas.get("id", []), feitas.get("variante", [])))
    linhas = []
    for k, f in enumerate(fotos.itertuples(index=False)):
        img = None
        for var in variantes(f.grupo, bool(f.real)):
            if (f.id, var) in prontas:
                continue
            if img is None:
                img = Image.open(pasta / "fotos" / f"{f.id}.jpg")
            j = julgar_clip(gerar(img, var, f.id), "livre", treinado=False)
            linhas.append({"id": f.id, "grupo": f.grupo, "classe": f.classe, "tema": f.tema, "variante": var,
                           "real": bool(f.real) and var in ("original", "celular"), "parte": parte(f.id),
                           "zs_tema": j["tema"], "zs_real": j["foto_real"], "probs": j["probs"],
                           "vetor": np.array(j["vetor"], dtype=np.float32)})
        if linhas and (k % 200 == 0 or k == len(fotos) - 1):
            feitas = pd.concat([feitas, pd.DataFrame(linhas)], ignore_index=True)
            feitas.to_pickle(saida)
            linhas = []
            print(f"{k + 1}/{len(fotos)} fotos", flush=True)
    return feitas


# ---------------------------------------------------------------- treino e calibração
def _acerto_tema(tema_previsto, verdade) -> float:
    return float(np.mean([(p or "nenhum") == v for p, v in zip(tema_previsto, verdade)]))


def treinar(df: pd.DataFrame, versao: str = "") -> tuple[Sonda, dict]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    X = np.stack(df["vetor"].to_numpy())
    y_tema = df["tema"].to_numpy()
    y_falsa = (~df["real"]).to_numpy().astype(int)
    zs = np.stack([zs_temas(p) for p in df["probs"]])
    zs_tela = np.array([p.get("tela", 0.0) for p in df["probs"]])
    tr, va = (df["parte"] == "treino").to_numpy(), (df["parte"] == "validacao").to_numpy()
    real = df["real"].to_numpy()
    idx = {t: i for i, t in enumerate(ORDEM)}
    alvo = np.array([idx[t] for t in y_tema])

    # sonda de tema: só fotos reais (as falsas são barradas antes do tema importar)
    melhor = None
    for C in (0.1, 0.3, 1.0, 3.0, 10.0):
        m = LogisticRegression(C=C, max_iter=3000, class_weight="balanced").fit(X[tr & real], alvo[tr & real])
        acc = float((m.predict(X[va & real]) == alvo[va & real]).mean())
        if melhor is None or acc > melhor[0]:
            melhor = (acc, C, m)
    _, C_tema, m_tema = melhor
    p_sonda = m_tema.predict_proba(X)  # colunas na ordem das classes = 0..5 (todas presentes)

    # sonda de falsa: todas as versões. Testado: dar o mesmo peso a cada tipo de falsa (para os poucos desenhos
    # pesarem mais) baixou o acerto geral no teste de 87% para 83% sem quase melhorar os desenhos; ficou o simples.
    melhor = None
    for C in (0.1, 0.3, 1.0, 3.0, 10.0):
        m = LogisticRegression(C=C, max_iter=3000, class_weight="balanced").fit(X[tr], y_falsa[tr])
        auc = float(roc_auc_score(y_falsa[va], m.predict_proba(X[va])[:, 1]))
        if melhor is None or auc > melhor[0]:
            melhor = (auc, C, m)
    _, C_falsa, m_falsa = melhor
    p_falsa = m_falsa.predict_proba(X)[:, 1]

    # α: peso da sonda de tema, pelo acerto de tema nas fotos reais da validação
    alfas = np.round(np.linspace(0, 1, 11), 2)
    acc_alfa = {float(a): _acerto_tema([ORDEM[i] for i in (a * p_sonda[va & real] + (1 - a) * zs[va & real]).argmax(1)],
                                       y_tema[va & real]) for a in alfas}
    alfa = max(acc_alfa, key=lambda a: (acc_alfa[a], a))

    # β e limiar: pegar o máximo de falsas sem recusar mais que MAX_REAL_RECUSADA das reais
    melhor = None
    for b in alfas:
        s = b * p_falsa[va] + (1 - b) * zs_tela[va]
        reais, falsas_ = s[y_falsa[va] == 0], s[y_falsa[va] == 1]
        limiar = float(np.quantile(reais, 1 - MAX_REAL_RECUSADA))
        pega = float((falsas_ >= limiar).mean())
        if melhor is None or pega > melhor[0]:
            melhor = (pega, float(b), limiar)
    _, beta, limiar = melhor

    sonda = Sonda(m_tema.coef_.astype(np.float32), m_tema.intercept_.astype(np.float32),
                  m_falsa.coef_[0].astype(np.float32), float(m_falsa.intercept_[0]), alfa, beta, limiar, versao)
    objetos, info_objetos = treinar_objetos(df)
    sonda = replace(sonda, objetos=objetos)
    info = {"C_tema": C_tema, "C_falsa": C_falsa, "alfa": alfa, "beta": beta, "limiar": limiar,
            "acerto_tema_por_alfa": acc_alfa, "objetos": info_objetos}
    return sonda, info


def treinar_objetos(df: pd.DataFrame) -> tuple[dict, dict]:
    """Um classificador de objeto por tema, só com fotos reais: o que é, entre as classes do tema (teclado x mouse...).
    O C sai da validação. Devolve (tema -> (pesos, vieses, classes), relatório)."""
    from sklearn.linear_model import LogisticRegression

    saida, relatorio = {}, {}
    for tema, classes in OBJETOS.items():
        d = df[(df["tema"] == tema) & df["real"] & df["classe"].isin(classes)]
        tr, va = d[d["parte"] == "treino"], d[d["parte"] == "validacao"]
        presentes = sorted(set(tr["classe"]))
        if len(presentes) < 2 or va.empty:
            continue
        Xtr, Xva = np.stack(tr["vetor"].to_numpy()), np.stack(va["vetor"].to_numpy())
        melhor = None
        for C in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0):
            m = LogisticRegression(C=C, max_iter=3000, class_weight="balanced").fit(Xtr, tr["classe"])
            acc = float((m.predict(Xva) == va["classe"]).mean())
            if melhor is None or acc > melhor[0]:
                melhor = (acc, C, m)
        acc, C, m = melhor
        w, b = m.coef_.astype(np.float32), m.intercept_.astype(np.float32)
        if w.shape[0] == 1:  # duas classes: o sklearn dá uma linha só; softmax([-z/2, z/2]) = sigmoide(z)
            w, b = np.vstack([-w[0] / 2, w[0] / 2]), np.array([-b[0] / 2, b[0] / 2], dtype=np.float32)
        saida[tema] = (w, b, tuple(str(c) for c in m.classes_))
        relatorio[tema] = {"C": C, "acerto_validacao": round(acc, 3), "classes": list(m.classes_)}
    return saida, relatorio


# ---------------------------------------------------------------- medição
def decisoes(df: pd.DataFrame, sonda: Sonda | None) -> pd.DataFrame:
    """Tema e foto_real que o CLIP decidiria em cada linha: zero-shot (sonda=None) ou com a sonda."""
    if sonda is None:
        return pd.DataFrame({"tema": df["zs_tema"].to_numpy(), "real": df["zs_real"].to_numpy()}, index=df.index)
    r = [aplicar_sonda(v, p, sonda) for v, p in zip(df["vetor"], df["probs"])]
    return pd.DataFrame({"tema": [x[1] for x in r], "real": [x[2] for x in r], "chances": [x[0] for x in r]},
                        index=df.index)


def aceita_certo(df: pd.DataFrame, tema, real) -> np.ndarray:
    """O jogo acertou? Foto real de tema: aceita no tema certo. Nenhum ou falsa: recusada."""
    tema = pd.Series(tema, index=df.index).fillna("nenhum")
    real = pd.Series(real, index=df.index).astype(bool)
    aceita = real & (tema != "nenhum")
    deveria = df["real"] & (df["tema"] != "nenhum")
    return np.where(deveria, aceita & (tema == df["tema"]), ~aceita).astype(bool)


def resumo(df: pd.DataFrame, tema, real) -> dict:
    certo = aceita_certo(df, tema, real)
    tema_s = pd.Series(tema, index=df.index).fillna("nenhum")
    real_s = pd.Series(real, index=df.index).astype(bool)
    reais_tema = df["real"] & (df["tema"] != "nenhum")
    return {"acerto_geral": float(certo.mean()),
            "foto_real_recusada": float((~real_s[df["real"]]).mean()),
            "falsa_aceita": float((real_s[~df["real"]] & (tema_s[~df["real"]] != "nenhum")).mean()),
            "tema_certo_nas_reais": float((tema_s[reais_tema] == df.loc[reais_tema, "tema"]).mean()),
            "n": int(len(df))}


# ---------------------------------------------------------------- modelos (fotos que a turma marcou no app)
def _chave_modelo(texto: str) -> str:
    from src.jogo import normalizar

    return normalizar(texto)


def carregar_turma(pasta: Path, saida: Path) -> pd.DataFrame:
    """As fotos reais da turma com o modelo marcado (rotulos.csv do volume "treino"), com o vetor do CLIP de cada uma.
    Guarda em cache (pickle); só processa as fotos novas."""
    from PIL import Image

    from src.reconhecimento import julgar_clip

    rotulos = pd.read_csv(pasta / "rotulos.csv", dtype=str).fillna("")
    rotulos = rotulos[(rotulos["tipo"] == "real") & (rotulos["modelo"] != "")]
    feitas = pd.read_pickle(saida) if saida.exists() else pd.DataFrame(columns=["id"])
    novas = []
    for r in rotulos[~rotulos["id"].isin(set(feitas["id"]))].itertuples(index=False):
        img = Image.open(pasta / "fotos" / f"{r.id}.jpg").convert("RGB")
        v = np.array(julgar_clip(img, "livre", treinado=False)["vetor"], dtype=np.float32)
        novas.append({"id": r.id, "tema": r.tema, "objeto": r.achado, "modelo": r.modelo, "vetor": v, "parte": parte(r.id)})
    if novas:
        feitas = pd.concat([feitas, pd.DataFrame(novas)], ignore_index=True)
        feitas.to_pickle(saida)
    return feitas


def treinar_modelos(turma: pd.DataFrame) -> tuple[dict, dict]:
    """Um classificador de modelo por tema com as fotos da turma. Só entram os modelos com MINIMO_POR_MODELO fotos
    ou mais (nomes iguais com maiúscula, acento ou espaço diferente contam como um só). O tema precisa de 2 modelos.
    Devolve (tema -> (pesos, vieses, nomes), relatório com o acerto na validação)."""
    from collections import Counter

    from sklearn.linear_model import LogisticRegression

    saida, relatorio = {}, {}
    if turma.empty:
        return saida, relatorio
    turma = turma.assign(chave=turma["modelo"].map(_chave_modelo))
    for tema, d in turma.groupby("tema"):
        tamanho = d["chave"].value_counts()
        validos = list(tamanho[tamanho >= MINIMO_POR_MODELO].index)
        d = d[d["chave"].isin(validos)]
        tr, va = d[d["parte"] == "treino"], d[d["parte"] == "validacao"]
        if len(validos) < 2 or tr["chave"].nunique() < 2:
            relatorio[tema] = {"aviso": f"ainda faltam fotos: precisa de {MINIMO_POR_MODELO} de pelo menos 2 modelos",
                               "fotos_por_modelo": {k: int(v) for k, v in tamanho.items()}}
            continue
        nome_de = {k: Counter(g["modelo"]).most_common(1)[0][0] for k, g in d.groupby("chave")}
        Xtr = np.stack(tr["vetor"].to_numpy())
        melhor = None
        for C in (0.3, 1.0, 3.0, 10.0):
            m = LogisticRegression(C=C, max_iter=3000, class_weight="balanced").fit(Xtr, tr["chave"])
            acc = float((m.predict(np.stack(va["vetor"].to_numpy())) == va["chave"]).mean()) if len(va) else float("nan")
            if melhor is None or (not np.isnan(acc) and (np.isnan(melhor[0]) or acc > melhor[0])):
                melhor = (acc, C, m)
        acc, C, m = melhor
        w, b = m.coef_.astype(np.float32), m.intercept_.astype(np.float32)
        if w.shape[0] == 1:
            w, b = np.vstack([-w[0] / 2, w[0] / 2]), np.array([-b[0] / 2, b[0] / 2], dtype=np.float32)
        saida[tema] = (w, b, tuple(nome_de[k] for k in m.classes_))
        relatorio[tema] = {"modelos": [nome_de[k] for k in m.classes_],
                           "acerto_validacao": None if np.isnan(acc) else round(acc, 3),
                           "fotos_validacao": int(len(va)), "C": C}
    return saida, relatorio
