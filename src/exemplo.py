"""Dados de EXEMPLO (fictícios) só para demonstrar a interface.

Não são dados reais e não devem entrar na análise do projeto.
Todos os usuários gerados aqui começam com "exemplo:" para ficarem identificáveis.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from src.categorias import ITENS, faixa_preco

# Quatro estilos de desejo (peso de cada categoria). Cada pessoa fictícia parte de um estilo
# e ganha variações próprias, para existirem grupos de verdade para o clustering encontrar.
ESTILOS = {
    "gastronômico": {"comida": 6, "bebidas": 3, "casa e decoração": 2},
    "tech": {"eletrônicos": 6, "brinquedos e games": 4, "esporte e lazer": 1},
    "moda": {"vestuário": 5, "calçados": 3, "beleza": 3},
    "pet": {"animais": 6, "esporte e lazer": 2, "comida": 1},
}

PESSOAS_EXEMPLO = {
    "exemplo:ana": "gastronômico", "exemplo:bia": "gastronômico", "exemplo:caio": "gastronômico",
    "exemplo:bruno": "tech", "exemplo:diego": "tech", "exemplo:enzo": "tech",
    "exemplo:carla": "moda", "exemplo:fernanda": "moda", "exemplo:gabi": "moda",
    "exemplo:davi": "pet", "exemplo:helena": "pet", "exemplo:igor": "pet",
}


def _variar(estilo: dict[str, int], rng: random.Random) -> dict[str, int]:
    """Cópia do estilo com pesos levemente alterados e 1-2 categorias extras de baixo peso."""
    from src.categorias import CATEGORIAS
    pesos = {c: max(1, p + rng.randint(-1, 1)) for c, p in estilo.items()}
    for extra in rng.sample([c for c in CATEGORIAS if c not in pesos], rng.randint(1, 2)):
        pesos[extra] = 1
    return pesos


def _gerar(usuario: str, pesos: dict[str, int], n: int, rng: random.Random,
           cidade: str, fim: datetime) -> list[dict]:
    categorias = list(pesos)
    registros = []
    for _ in range(n):
        cat = rng.choices(categorias, weights=[pesos[c] for c in categorias])[0]
        item = rng.choice([i for i in ITENS if i.categoria == cat])
        quando = fim - timedelta(days=rng.randint(0, 20), hours=rng.randint(0, 14),
                                 minutes=rng.randint(0, 59))
        registros.append({
            "id": str(uuid.uuid4()), "usuario": usuario, "criado_em": quando,
            "item": item.nome, "categoria": item.categoria, "tipo": item.tipo,
            "faixa_preco": faixa_preco(item),
            "confianca": round(rng.uniform(0.4, 0.95), 2), "cidade": cidade,
            "acao": rng.choice(["ver_loja_online", "ver_mapa", "ver_receita", "salvou"]),
        })
    return registros


def gerar_exemplos(incluir_eu: bool = True, semente: int = 42) -> list[dict]:
    rng = random.Random(semente)
    fim = datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)
    registros = []
    for usuario, estilo in PESSOAS_EXEMPLO.items():
        registros += _gerar(usuario, _variar(ESTILOS[estilo], rng), rng.randint(22, 36), rng, "Vitória - ES", fim)
    if incluir_eu:
        meus = {"comida": 4, "eletrônicos": 3, "animais": 2, "vestuário": 1}
        registros += _gerar("exemplo:eu", meus, 30, rng, "Vitória - ES", fim)
    return registros
