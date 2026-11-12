"""Estimativa de preço: anúncios reais do Mercado Livre → estimativa do Gemma → tabela de referência.

Sempre devolve de onde veio o número, para o app mostrar ("Mercado Livre, 18 anúncios",
"estimativa da IA", "referência").

A busca pública do Mercado Livre (api.mercadolibre.com) pode exigir login em algumas épocas/regiões;
nesse caso ela simplesmente falha e o app passa para a próxima fonte.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import requests

from src.categorias import Item, faixa_preco, faixa_reais
from src.lugares import USER_AGENT

ML_URL = "https://api.mercadolibre.com/sites/MLB/search"
MIN_ANUNCIOS = 5


@dataclass
class Preco:
    texto: str   # ex.: "R$ 280–R$ 450"
    fonte: str   # ex.: "Mercado Livre, 18 anúncios"


def termo_de_busca(item: Item) -> str:
    """"Nike Air Max tênis": marca e modelo primeiro, que é o que mais muda o preço."""
    return " ".join(x for x in (item.marca, item.modelo, item.nome.split("/")[0]) if x)


def faixa_dos_anuncios(precos: list[float]) -> tuple[float, float] | None:
    """Do 1º ao 3º quartil: corta acessórios baratos e kits caros que aparecem na busca."""
    precos = sorted(p for p in precos if p and p > 0)
    if len(precos) < MIN_ANUNCIOS:
        return None
    q1, _, q3 = statistics.quantiles(precos, n=4)
    return q1, q3


def mercado_livre(item: Item, limite: int = 20) -> Preco | None:
    """Faixa de preço dos anúncios novos; None se a API falhar ou houver poucos anúncios."""
    try:
        resp = requests.get(ML_URL, params={"q": termo_de_busca(item), "limit": limite, "condition": "new"},
                            headers={"User-Agent": USER_AGENT}, timeout=8)
        resp.raise_for_status()
        resultados = resp.json().get("results", [])
    except (requests.RequestException, ValueError, AttributeError):
        return None
    faixa = faixa_dos_anuncios([r.get("price") for r in resultados if isinstance(r, dict)])
    if not faixa:
        return None
    return Preco(faixa_reais(*faixa), f"Mercado Livre, {len(resultados)} anúncios")


def estimar(item: Item, ia: tuple[float | None, float | None] | None = None,
            buscar_online: bool = True) -> Preco:
    """Melhor estimativa disponível. `ia` = (preco_min, preco_max) do Gemma, se houver."""
    if item.tipo == "adotar":
        return Preco(faixa_preco(item), "adoção")
    if buscar_online and item.tipo == "comprar":  # comida/bebida: anúncio não é o preço do prato
        achado = mercado_livre(item)
        if achado:
            return achado
    if ia and ia[0] is not None and ia[1] is not None:
        return Preco(faixa_reais(*ia), "estimativa da IA")
    return Preco(faixa_preco(item).replace(" (estimativa da categoria)", ""),
                 "referência da categoria" if "(estimativa da categoria)" in faixa_preco(item) else "referência")
