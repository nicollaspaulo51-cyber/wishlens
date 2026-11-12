"""Preço: Mercado Livre (mockado) -> estimativa do Gemma -> tabela de referência."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from src import precos
from src.categorias import ITENS, Item, faixa_reais, reais, termo_de_busca

TENIS = Item("sneakers", "tênis", "calçados", "comprar", marca="Nike", modelo="Air Max")
PIZZA = next(i for i in ITENS if i.nome == "pizza")
CAO = next(i for i in ITENS if i.nome == "cachorro")


def _ml(precos_):
    r = MagicMock()
    r.json.return_value = {"results": [{"price": p} for p in precos_]}
    return r


def test_formato_em_reais():
    assert reais(1234.4) == "R$ 1.234" and reais(9.9) == "R$ 9,90"
    assert faixa_reais(300, 300.2) == "R$ 300"


def test_termo_de_busca_usa_marca_e_modelo():
    assert termo_de_busca(TENIS) == "Nike Air Max tênis"
    assert termo_de_busca(Item("x", "boné/chapéu", "vestuário", "comprar")) == "boné"


def test_quartis_cortam_acessorios_e_kits():
    # 2 cadarços baratos e 1 kit caro não puxam a faixa
    assert precos.faixa_dos_anuncios([20, 25, 500, 550, 600, 620, 650, 700, 5000]) == (262.5, 675.0)
    assert precos.faixa_dos_anuncios([100, 200]) is None  # poucos anúncios


def test_mercado_livre_primeiro():
    with patch("src.precos.requests.get", return_value=_ml([500, 550, 600, 650, 700, 750])) as get:
        p = precos.estimar(TENIS, ia=(100, 200))
    assert p.fonte == "Mercado Livre, 6 anúncios" and p.texto.startswith("R$ 5")
    assert get.call_args.kwargs["params"]["q"] == "Nike Air Max tênis"


def test_sem_mercado_livre_usa_ia_e_depois_tabela():
    with patch("src.precos.requests.get", side_effect=requests.HTTPError("403")):
        assert precos.estimar(TENIS, ia=(600, 1000)) == precos.Preco("R$ 600–R$ 1.000", "estimativa da IA")
        p = precos.estimar(TENIS)
    assert p.fonte == "referência" and p.texto == "R$ 150–1.200"


def test_comida_e_animal_nao_buscam_anuncios():
    with patch("src.precos.requests.get") as get:
        assert precos.estimar(PIZZA).fonte == "referência"
        assert precos.estimar(CAO) == precos.Preco("adoção gratuita", "adoção")
    get.assert_not_called()
