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
from dataclasses import dataclass
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
                        limiar_ia=np.float32(s.limiar_ia), tema_da_ia=np.array(s.tema_da_ia))


def carregar(caminho: Path = CAMINHO) -> Sonda | None:
    """A sonda salva, ou None (sem arquivo, ou treinada para outros temas): aí o juiz usa só o zero-shot."""
    if not caminho.exists():
        return None
    d = np.load(caminho)
    if tuple(str(x) for x in d["ordem"]) != ORDEM:
        return None
    return Sonda(d["w_tema"], d["b_tema"], d["w_falsa"], float(d["b_falsa"]), float(d["alfa"]), float(d["beta"]),
                 float(d["limiar"]), str(d["versao"]), float(d["limiar_ia"]) if "limiar_ia" in d else 0.0,
                 bool(d["tema_da_ia"]) if "tema_da_ia" in d else True)


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
    info = {"C_tema": C_tema, "C_falsa": C_falsa, "alfa": alfa, "beta": beta, "limiar": limiar,
            "acerto_tema_por_alfa": acc_alfa}
    return sonda, info


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
