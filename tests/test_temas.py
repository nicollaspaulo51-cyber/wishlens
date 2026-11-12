"""Temas e tema do dia (rodízio pela data, horário de Brasília)."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import temas
from src.categorias import nome_valido


def test_rodizio_passa_por_todos():
    inicio = date(2026, 11, 1)
    vistos = [temas.tema_do_dia(inicio + timedelta(days=i)).id for i in range(len(temas.TEMAS))]
    assert sorted(vistos) == sorted(t.id for t in temas.TEMAS)
    assert temas.tema_do_dia(inicio) == temas.tema_do_dia(inicio + timedelta(days=len(temas.TEMAS)))


def test_dia_vira_a_meia_noite_de_brasilia():
    # 02:30 UTC do dia 13 ainda é 23:30 do dia 12 em Brasília
    assert temas.dia_de(datetime(2026, 11, 13, 2, 30, tzinfo=timezone.utc)) == date(2026, 11, 12)
    assert temas.dia_de(datetime(2026, 11, 13, 3, 30, tzinfo=timezone.utc)) == date(2026, 11, 13)
    assert temas.dia_de(datetime(2026, 11, 12, 23, 59)) == date(2026, 11, 12)  # sem fuso: já é Brasília


def test_temas_consistentes():
    assert len({t.id for t in temas.TEMAS}) == len(temas.TEMAS)
    for t in temas.TEMAS:
        assert t.frases_clip and t.tags_osm and nome_valido(t.generico)
