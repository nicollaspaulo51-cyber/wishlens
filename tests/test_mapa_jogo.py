"""Mapa da tela principal (src/mapa_jogo.py): HTML com o personagem e os pontos que piscam."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import mapa_jogo
from src.temas import POR_ID, TEMAS


def _dados(html: str) -> dict:
    bruto = re.search(r"const D = (.*?);\n", html).group(1)
    return json.loads(bruto.replace("<\\/", "</"))


def test_html_tem_personagem_pontos_e_tema_do_dia():
    pontos = [{"tema": "passaros", "nome": "Parque", "lat": -20.29, "lon": -40.29, "horario": "seg–sex"},
              {"tema": "carros", "nome": "Estacionamento", "lat": -20.28, "lon": -40.28}]
    manchas = [{"tema": "pets", "lat": -20.3, "lon": -40.3, "n": 4, "raros": ["husky"]}]
    html = mapa_jogo.montar(-20.29, -40.29, pontos, manchas, POR_ID["passaros"], TEMAS, cor="#123456")
    d = _dados(html)
    assert d["hoje"]["id"] == "passaros" and len(d["pontos"]) == 2 and d["manchas"][0]["n"] == 4
    assert "#123456" in d["personagem"] and "<svg" in d["personagem"]
    # tema do dia pisca mais rápido; todos começam em momentos diferentes (atraso negativo)
    do_dia = next(p for p in d["pontos"] if p["tema"] == "passaros")
    outro = next(p for p in d["pontos"] if p["tema"] == "carros")
    assert do_dia["duracao"] <= 6 < outro["duracao"] or do_dia["duracao"] <= outro["duracao"]
    assert all(p["atraso"] <= 0 for p in d["pontos"])
    assert "watchPosition" in html and "@keyframes piscar" in html


def test_nome_malicioso_do_osm_nao_vira_html():
    ruim = '</script><script>alert(1)</script><img src=x onerror=alert(2)>'
    html = mapa_jogo.montar(0, 0, [{"tema": "pets", "nome": ruim, "lat": 0, "lon": 0}], [], TEMAS[0], TEMAS)
    assert "</script><script>alert(1)" not in html      # não fecha a tag do script
    assert _dados(html)["pontos"][0]["nome"] == ruim    # o texto chega igual, como dado
    js = html[html.index("const D ="):]
    assert "innerHTML" not in js                          # o JavaScript usa só textContent


def test_tema_escuro():
    claro = mapa_jogo.montar(0, 0, [], [], TEMAS[0], TEMAS)
    escuro = mapa_jogo.montar(0, 0, [], [], TEMAS[0], TEMAS, escuro=True)
    assert '<body class="escuro">' in escuro and '<body class="">' in claro


def test_mirante_pista_e_guardiao_vao_para_o_mapa():
    pontos = [{"tema": "passaros", "nome": "Parque", "lat": -20.29, "lon": -40.29, "tipo": "park"}]
    manchas = [{"tema": "pets", "lat": -20.3, "lon": -40.3, "n": 4, "raros": [], "guardiao": "bia"}]
    html = mapa_jogo.montar(-20.29, -40.29, pontos, manchas, TEMAS[0], TEMAS, pistas={"park": ["sabiá"]})
    d = _dados(html)
    assert d["mirante_m"] == 40 and d["pontos"][0]["tipo"] == "park" and d["pistas"] == {"park": ["sabiá"]}
    assert d["manchas"][0]["guardiao"] == "bia" and "atualizarPerto()" in html
