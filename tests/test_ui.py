"""Painel do dia: o resumo de uma linha e quando ele abre sozinho."""
from datetime import datetime

from src import jogo, ui
from src.armazenamento import COLUNAS_CAPTURA

import pandas as pd


def _painel(aberta: bool, lupa: int = 0) -> str:
    pontuadas = jogo.calcular_pontos(pd.DataFrame(columns=COLUNAS_CAPTURA))
    estado = jogo.estado_do_dia(pontuadas, "ana")
    estado["lupa"], estado["lupa_cheia"] = lupa, lupa >= 3
    meta = jogo.meta_da_turma(pontuadas, datetime(2026, 11, 13, 13 if aberta else 9, 0))
    return ui.painel_do_dia(estado, 0, meta)


def test_resumo_mostra_os_tres_numeros():
    html = _painel(aberta=False)
    assert "Lupa <b>0/3</b>" in html and "Meta <b>0 de 20</b>" in html and "Desafios <b>0 de 3</b>" in html
    assert "<details class=\"wl-hoje\">" in html  # fechado: nada urgente


def test_abre_sozinho_com_meta_aberta_ou_lupa_cheia():
    assert "<details class=\"wl-hoje\" open>" in _painel(aberta=True)
    assert "<details class=\"wl-hoje\" open>" in _painel(aberta=False, lupa=3)


def test_album_mostra_coladas_lacunas_e_total():
    from src.temas import POR_ID

    html = ui.album_html(POR_ID["pets"], [("<b>golden</b>", 1), ("vira-lata", 5)], [("B…", 3)], 7,
                         {"nome": "Amigo dos bichos", "nivel": None, "proximo": 1})
    assert "2 de 7" in html and "&lt;b&gt;golden&lt;/b&gt;" in html and "<b>golden</b>" not in html
    assert html.count("wl-fig colada") == 2 and html.count("wl-fig vazia") == 1
    assert "raro, 1× na turma" in html and "comum, 5× na turma" in html
    assert "E mais 4 que a turma já achou" in html and "faltam 1 para o próximo nível" in html


def test_album_vazio_convida_a_procurar():
    from src.temas import POR_ID

    html = ui.album_html(POR_ID["pets"], [], [], 0)
    assert "0 de 0" in html and "Nenhuma figurinha ainda" in html and "wl-grade" not in html
