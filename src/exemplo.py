"""Dados de EXEMPLO (fictícios) só para demonstrar a interface.

Não são dados reais e não devem entrar na análise do projeto.
Todos os usuários gerados aqui começam com "exemplo:" para ficarem identificáveis.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from src.categorias import FAIXA_PRECO, ITENS

# Peso de cada categoria em cada perfil fictício
PERFIS_EXEMPLO = {
    "exemplo:ana": {"comida": 6, "bebidas": 3, "casa e decoração": 2, "animais": 1},
    "exemplo:bruno": {"eletrônicos": 6, "brinquedos e games": 4, "esporte e lazer": 1},
    "exemplo:carla": {"vestuário": 5, "calçados": 3, "beleza": 3, "comida": 1},
    "exemplo:davi": {"animais": 5, "esporte e lazer": 3, "comida": 2},
}


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
            "faixa_preco": FAIXA_PRECO[item.categoria],
            "confianca": round(rng.uniform(0.4, 0.95), 2), "cidade": cidade,
            "acao": rng.choice(["ver_loja_online", "ver_mapa", "ver_receita", "salvou"]),
        })
    return registros


def gerar_exemplos(incluir_eu: bool = True, semente: int = 42) -> list[dict]:
    rng = random.Random(semente)
    fim = datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)
    registros = []
    for usuario, pesos in PERFIS_EXEMPLO.items():
        registros += _gerar(usuario, pesos, rng.randint(25, 40), rng, "Vitória - ES", fim)
    if incluir_eu:
        meus = {"comida": 4, "eletrônicos": 3, "animais": 2, "vestuário": 1}
        registros += _gerar("exemplo:eu", meus, 30, rng, "Vitória - ES", fim)
    return registros
