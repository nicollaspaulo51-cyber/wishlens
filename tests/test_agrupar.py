"""Regra de ranking do CLIP (src/reconhecimento.agrupar), sem torch: probabilidades falsas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.categorias import Item
from src.reconhecimento import MARCAS, PESO_CATALOGO, _ROTULOS, agrupar

CARRO = Item("a car", "carro", "veículos", "comprar")
TENIS = Item("sneakers", "tênis", "calçados", "comprar")
CAMINHAO = Item("truck", "camião", "veículos", "comprar")
SEM = ("", "")


def test_catalogo_pesa_mais_que_o_lvis():
    rotulos = [(CARRO, "a car", SEM), (CAMINHAO, "truck", SEM)]
    r = agrupar(rotulos, [0.45, 0.55], n_curados=1)
    assert r[0].item.nome == "carro"  # 0,45 x 1,7 > 0,55
    assert abs(sum(x.confianca for x in r) - 1) < 1e-9
    assert abs(r[0].confianca - 0.45 * PESO_CATALOGO / (0.45 * PESO_CATALOGO + 0.55)) < 1e-9


def test_marca_quando_domina_o_item():
    rotulos = [(TENIS, "sneakers", SEM), (TENIS, "Nike sneakers", ("Nike", "")),
               (TENIS, "Adidas sneakers", ("Adidas", "")), (CARRO, "a car", SEM)]
    r = agrupar(rotulos, [0.2, 0.6, 0.1, 0.1], n_curados=4)
    assert r[0].item.nome == "tênis" and r[0].item.marca == "Nike"
    assert abs(r[0].confianca - 0.9) < 1e-9  # as frases somam no mesmo item
    r = agrupar(rotulos, [0.5, 0.2, 0.2, 0.1], n_curados=4)
    assert r[0].item.marca == ""  # nenhuma marca chega à metade: sem marca


def test_marcas_apontam_para_itens_do_catalogo():
    nomes = {i.nome for i, _, _ in _ROTULOS}
    assert set(MARCAS) <= nomes
    assert any(m == ("Monster", "") for _, _, m in _ROTULOS)
