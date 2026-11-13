"""Clima (src/clima.py): código WMO do Open-Meteo para o que o jogo usa."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import clima


def test_codigos_wmo():
    assert clima.de_codigo(0) == "sol"
    assert clima.de_codigo(3) == "nublado"
    assert clima.de_codigo(63) == clima.de_codigo(95) == "chuva"
    assert clima.de_codigo(None) is None


def test_sem_internet_devolve_none(monkeypatch):
    import requests

    def falha(*a, **k):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(clima.requests, "get", falha)
    assert clima.agora(-20.29, -40.29) is None
