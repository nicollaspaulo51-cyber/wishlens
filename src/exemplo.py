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


# ---------------------------------------------------------------- capturas do jogo (fictícias)
# Achados por tema, dos mais comuns aos mais raros (o peso cai ao longo da lista)
ACHADOS_EXEMPLO = {
    "carros": ["Chevrolet Onix", "Volkswagen Gol", "Fiat Mobi", "Hyundai HB20", "Fiat Strada", "Toyota Corolla",
               "Jeep Renegade", "Honda Civic", "Volkswagen Fusca", "Ford Mustang", "Porsche 911"],
    "plantas": ["costela-de-adão", "espada-de-são-jorge", "girassol", "ipê-amarelo", "hibisco", "orquídea",
                "bromélia", "ipê-roxo", "pau-brasil"],
    "passaros": ["pombo", "bem-te-vi", "sabiá-laranjeira", "pardal", "quero-quero", "rolinha", "beija-flor",
                 "tucano", "garça-branca", "gavião-carijó"],
    "pets": ["cachorro vira-lata caramelo", "gato vira-lata", "cachorro shih-tzu", "cachorro poodle",
             "gato siamês", "cachorro golden retriever", "gato persa", "cachorro husky siberiano"],
    "pecas": ["mouse", "teclado mecânico", "memória RAM", "SSD", "placa de vídeo", "processador",
              "placa-mãe", "fonte de alimentação", "cooler de processador"],
}
# Estilo de jogador: peso de cada tema
ESTILOS_JOGO = {"carros": {"carros": 6, "pecas": 2}, "natureza": {"plantas": 4, "passaros": 4},
                "pets": {"pets": 6, "plantas": 1}, "tech": {"pecas": 5, "carros": 2}}
JOGADORES_EXEMPLO = {
    "exemplo:ana": "natureza", "exemplo:bia": "pets", "exemplo:caio": "carros", "exemplo:bruno": "tech",
    "exemplo:diego": "carros", "exemplo:carla": "natureza", "exemplo:davi": "pets", "exemplo:helena": "tech",
    "exemplo:eu": "carros",
}
CENTRO_EXEMPLO = (-20.2905, -40.2930)  # Vitória - ES


def gerar_capturas(semente: int = 7, dias: int = 14, centro: tuple[float, float] = CENTRO_EXEMPLO) -> list[dict]:
    """Capturas fictícias de ~2 semanas para o pódio, a coleção e o mapa aparecerem antes da turma jogar."""
    from src.jogo import agora_naive, celula

    rng = random.Random(semente)
    fim = agora_naive()
    registros = []
    for usuario, estilo in JOGADORES_EXEMPLO.items():
        pesos = {t: p + rng.randint(0, 1) for t, p in ESTILOS_JOGO[estilo].items()}
        for _ in range(rng.randint(12, 30)):
            tema = rng.choices(list(pesos), weights=list(pesos.values()))[0]
            lista = ACHADOS_EXEMPLO[tema]
            achado = rng.choices(lista, weights=[len(lista) - k for k in range(len(lista))])[0]
            quando = fim - timedelta(days=rng.randint(0, dias), hours=rng.randint(0, 12), minutes=rng.randint(0, 59))
            lat, lon = centro[0] + rng.gauss(0, 0.012), centro[1] + rng.gauss(0, 0.012)
            real = rng.random() > 0.04
            registros.append({
                "id": str(uuid.uuid4()), "usuario": usuario, "criado_em": quando, "tema": tema,
                "achado": achado, "confianca": round(rng.uniform(0.5, 0.97), 2),
                "foto_real": real, "foto_hash": f"{rng.getrandbits(64):016x}",
                "cidade": "Vitória - ES", "celula": celula(lat, lon),
                **_opiniao_clip(tema, real, rng),
            })
        # Algumas fotos que o juiz recusou e a pessoa contestou (ex.: mouse que virou "nenhum")
        for _ in range(rng.randint(0, 2)):
            tema = rng.choice(list(pesos))
            registros.append({
                "id": str(uuid.uuid4()), "usuario": usuario, "criado_em": fim - timedelta(days=rng.randint(0, dias)),
                "tema": "nenhum", "achado": "", "confianca": round(rng.uniform(0.3, 0.6), 2), "foto_real": True,
                "foto_hash": f"{rng.getrandbits(64):016x}", "cidade": "Vitória - ES", "celula": None,
                "juiz": "gemma+clip", "clip_tema": tema, "clip_foto_real": True,
                "clip_prob_tema": None, "clip_prob_tela": round(rng.uniform(0.0, 0.1), 2), "contestada": tema,
            })
    return registros


def _opiniao_clip(tema: str, real: bool, rng: random.Random) -> dict:
    """CLIP fictício: concorda com o Gemma ~85% das vezes; às vezes discorda com clareza (vira veto)."""
    from src.temas import TEMAS

    concorda = rng.random() < 0.85
    clip_tema = tema if concorda else rng.choice([t.id for t in TEMAS if t.id != tema] + ["nenhum"])
    prob_tema = rng.uniform(0.35, 0.9) if concorda else rng.uniform(0.02, 0.25)
    prob_tela = rng.uniform(0.55, 0.8) if not real else rng.uniform(0.0, 0.2)
    return {"juiz": "gemma+clip", "clip_tema": None if clip_tema == "nenhum" else clip_tema,
            "clip_foto_real": prob_tela < 0.5, "clip_prob_tema": round(prob_tema, 3),
            "clip_prob_tela": round(prob_tela, 3), "contestada": None}
