"""Clustering de perfis de desejo com K-Means (fase de Modelagem do CRISP-DM).

Cada pessoa vira um vetor com a proporção dos seus desejos em cada categoria
(o mesmo vetor usado na comparação por similaridade do cosseno, em src/perfil.py).
O K-Means agrupa pessoas com vetores parecidos, e cada grupo recebe um nome
a partir das categorias que mais pesam no seu centro.
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.categorias import CATEGORIAS
from src.perfil import vetor_perfil

SEMENTE = 42

# Nome do perfil a partir da categoria dominante do centro do cluster
NOMES = {
    "comida": "Gastronômico", "bebidas": "Gastronômico",
    "eletrônicos": "Tech & Games", "brinquedos e games": "Tech & Games",
    "vestuário": "Moda & Beleza", "calçados": "Moda & Beleza", "beleza": "Moda & Beleza",
    "animais": "Pet lover",
    "esporte e lazer": "Esporte & Aventura", "veículos": "Esporte & Aventura",
    "casa e decoração": "Casa & Conforto",
    "livros e papelaria": "Cultura & Estudos",
}


def matriz_perfis(df: pd.DataFrame, minimo: int = 1) -> pd.DataFrame:
    """Linhas = usuários, colunas = categorias, valores = proporção de desejos (cada linha soma 1).

    Usuários com menos de `minimo` desejos ficam de fora (perfil pouco confiável).
    """
    grupos = {u: g for u, g in df.groupby("usuario") if len(g) >= minimo}
    if not grupos:
        return pd.DataFrame(columns=CATEGORIAS, dtype=float)
    return pd.DataFrame({u: vetor_perfil(g) for u, g in grupos.items()}).T[CATEGORIAS]


def escolher_k(X: pd.DataFrame, ks=range(2, 7)) -> pd.DataFrame:
    """Inércia (método do cotovelo) e silhueta para cada k possível."""
    linhas = []
    for k in ks:
        if k >= len(X):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=SEMENTE).fit(X)
        linhas.append({"k": k, "inercia": km.inertia_, "silhueta": silhouette_score(X, km.labels_)})
    return pd.DataFrame(linhas, columns=["k", "inercia", "silhueta"])


def melhor_k(X: pd.DataFrame, ks=range(2, 7)) -> int:
    tabela = escolher_k(X, ks)
    return int(tabela.loc[tabela["silhueta"].idxmax(), "k"]) if not tabela.empty else 1


def nomear_cluster(centro: pd.Series) -> str:
    """Ex.: 'Gastronômico' ou 'Tech & Games + Pet lover' quando duas categorias pesam parecido."""
    ordem = centro.sort_values(ascending=False)
    nomes = []
    for cat, peso in ordem.items():
        nome = NOMES.get(cat, cat.capitalize())
        if nome in nomes:
            continue
        if not nomes or peso >= 0.6 * ordem.iloc[0]:
            nomes.append(nome)
        if len(nomes) == 2:
            break
    return " + ".join(nomes)


def agrupar(X: pd.DataFrame, k: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (rótulos por usuário, centros nomeados).

    rotulos: colunas usuario, cluster, perfil
    centros: uma linha por cluster, colunas = categorias + perfil
    """
    if len(X) < 2:
        perfil = nomear_cluster(X.iloc[0]) if len(X) else ""
        rot = pd.DataFrame({"usuario": X.index, "cluster": 0, "perfil": perfil})
        return rot, X.assign(perfil=perfil).reset_index(drop=True)
    k = k or melhor_k(X)
    km = KMeans(n_clusters=k, n_init=10, random_state=SEMENTE).fit(X)
    centros = pd.DataFrame(km.cluster_centers_, columns=X.columns)
    centros["perfil"] = [nomear_cluster(c) for _, c in centros[X.columns].iterrows()]
    rot = pd.DataFrame({"usuario": X.index, "cluster": km.labels_})
    rot["perfil"] = rot["cluster"].map(centros["perfil"])
    return rot.reset_index(drop=True), centros


def perfil_do_usuario(df: pd.DataFrame, usuario: str) -> str | None:
    """Nome do perfil (cluster) de um usuário, considerando todos os usuários disponíveis."""
    X = matriz_perfis(df)
    if usuario not in X.index:
        return None
    if len(X) < 3:  # poucas pessoas: usa só o próprio perfil
        return nomear_cluster(X.loc[usuario])
    rot, _ = agrupar(X)
    return rot.set_index("usuario").loc[usuario, "perfil"]
