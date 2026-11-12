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
    assert abs(r[0].confianca - 0.8 / 0.9) < 1e-9  # base + só a marca mais forte (Adidas não soma)
    r = agrupar(rotulos, [0.5, 0.2, 0.2, 0.1], n_curados=4)
    assert r[0].item.marca == ""  # nenhuma marca chega à metade: sem marca


def test_marcas_apontam_para_itens_do_catalogo():
    nomes = {i.nome for i, _, _ in _ROTULOS}
    assert set(MARCAS) <= nomes
    assert any(m == ("Monster", "") for _, _, m in _ROTULOS)


def test_muitas_marcas_nao_inflam_o_item():
    """Refrigerante tem mais frases de marca que energético: não pode ganhar só por isso."""
    ENERG = Item("energy drink", "energético", "bebidas", "receita")
    REFRI = Item("soda", "refrigerante", "bebidas", "receita")
    rotulos = ([(ENERG, "can", SEM)] + [(ENERG, f"e{k}", (f"E{k}", "")) for k in range(3)]
               + [(REFRI, "can", SEM)] + [(REFRI, f"r{k}", (f"R{k}", "")) for k in range(6)])
    probs = [0.08] * 4 + [0.07] * 7
    r = agrupar(rotulos, probs, n_curados=len(rotulos))
    assert r[0].item.nome == "energético"


def test_links_das_lojas_usam_a_marca():
    from src.links import links_para
    links = links_para(Item("sneakers", "tênis", "calçados", "comprar", "Nike", "Air Max"))
    assert links["Amazon"].endswith("k=Nike+Air+Max+t%C3%AAnis")
    assert "Nike-Air-Max" in links["Mercado Livre"]
