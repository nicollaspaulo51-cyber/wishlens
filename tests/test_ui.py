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
