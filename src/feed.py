"""Feed "Descobrir": recomendações para rolar, a partir dos desejos da pessoa.

Cada item do catálogo que a pessoa ainda não deseja recebe uma pontuação:

    pontuação = 0,55 × peso da categoria no perfil da pessoa          (conteúdo)
              + 0,45 × quanto as pessoas parecidas desejam o item      (colaborativo)

"Pessoas parecidas" são as de maior similaridade do cosseno com o perfil da pessoa
(o mesmo cálculo da página Comparar). Para o feed não ficar repetitivo, cerca de
1 em cada 6 cartões é uma "exploração": um item de uma categoria que a pessoa
ainda não deseja.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd

from src.categorias import FAIXA_PRECO, ITENS, Item
from src.perfil import similaridade_cosseno, vetor_perfil

PESO_CONTEUDO = 0.55
PESO_VIZINHOS = 0.45
VIZINHOS = 3
A_CADA_EXPLORACAO = 6


@dataclass
class Cartao:
    item: Item
    motivo: str          # frase curta explicando por que apareceu
    tipo_motivo: str     # "perfil", "vizinhos" ou "novo"
    pontuacao: float

    @property
    def faixa_preco(self) -> str:
        return FAIXA_PRECO.get(self.item.categoria, "—")


def _nome(usuario: str) -> str:
    nome = usuario.removeprefix("exemplo:")
    return "O perfil “eu”" if nome == "eu" else nome.capitalize()


def vizinhos(df: pd.DataFrame, usuario: str, n: int = VIZINHOS) -> list[tuple[str, float]]:
    """As n pessoas com perfil mais parecido (similaridade do cosseno > 0)."""
    meu = vetor_perfil(df[df["usuario"] == usuario])
    sims = [(u, similaridade_cosseno(meu, vetor_perfil(g)))
            for u, g in df.groupby("usuario") if u != usuario]
    return sorted([s for s in sims if s[1] > 0], key=lambda s: s[1], reverse=True)[:n]


def gerar_feed(df: pd.DataFrame, usuario: str, ocultos: set[str] | None = None,
               quantidade: int = 12, pagina: int = 0, semente: int = 7) -> list[Cartao]:
    """Retorna a `pagina`-ésima página do feed (quantidade cartões por página)."""
    ocultos = ocultos or set()
    meus = df[df["usuario"] == usuario]
    ja_desejo = set(meus["item"])
    candidatos = [i for i in ITENS if i.nome not in ja_desejo and i.nome not in ocultos]
    if not candidatos:
        return []

    perfil = vetor_perfil(meus) if not meus.empty else None
    viz = vizinhos(df, usuario) if not meus.empty else []
    nomes_viz = {u: s for u, s in viz}

    # Quanto os vizinhos desejam cada item (frequência ponderada pela similaridade), de 0 a 1
    pop: dict[str, float] = {}
    quem_quer: dict[str, tuple[str, float]] = {}
    for u, s in viz:
        for item, n in df[df["usuario"] == u]["item"].value_counts().items():
            pop[item] = pop.get(item, 0) + s * n
            if item not in quem_quer or s > quem_quer[item][1]:
                quem_quer[item] = (u, s)
    maior = max(pop.values(), default=1) or 1

    pontuados, novos = [], []
    for item in candidatos:
        peso_cat = float(perfil[item.categoria]) if perfil is not None else 0.0
        peso_viz = pop.get(item.nome, 0) / maior
        nota = PESO_CONTEUDO * peso_cat + PESO_VIZINHOS * peso_viz
        if nota <= 0:
            novos.append(item)
            continue
        if peso_viz >= peso_cat and item.nome in quem_quer:
            u, s = quem_quer[item.nome]
            motivo = f"{_nome(u)} tem {s:.0%} de gosto em comum com você e também quer"
            tipo = "vizinhos"
        else:
            motivo = f"Porque {peso_cat:.0%} dos seus desejos são de {item.categoria}"
            tipo = "perfil"
        pontuados.append(Cartao(item, motivo, tipo, nota))

    rng = random.Random(f"{semente}-{usuario}")
    # Um pouco de aleatoriedade para variar a ordem entre itens com notas parecidas
    pontuados.sort(key=lambda c: c.pontuacao * rng.uniform(0.85, 1.15), reverse=True)
    rng.shuffle(novos)

    # Intercala: a cada A_CADA_EXPLORACAO cartões, um item "novo" (se houver)
    feed: list[Cartao] = []
    while pontuados or novos:
        if novos and (len(feed) + 1) % A_CADA_EXPLORACAO == 0 or not pontuados:
            item = novos.pop()
            feed.append(Cartao(item, f"Algo diferente: você ainda não deseja nada de {item.categoria}",
                               "novo", 0.0))
        else:
            feed.append(pontuados.pop(0))

    inicio = pagina * quantidade
    return feed[inicio:inicio + quantidade]
