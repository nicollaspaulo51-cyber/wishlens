"""Clima de agora (Open-Meteo: sem chave, dados CC-BY 4.0). Com chuva, plantas e pássaros dão bônus (src/jogo.py).

Só vai para o Open-Meteo a coordenada arredondada (~1 km); se o serviço falhar, devolve None e o jogo segue.
"""

from __future__ import annotations

import requests

URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "WishLens/0.1 (projeto academico de Ciencia de Dados)"

# Códigos WMO do Open-Meteo: https://open-meteo.com/en/docs (weather_code)
CHUVA = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
NUBLADO = {1, 2, 3, 45, 48}
NEVE = {71, 73, 75, 77, 85, 86}


def de_codigo(codigo: int | None) -> str | None:
    """Código WMO -> "chuva", "nublado", "sol", "neve" ou None."""
    if codigo is None:
        return None
    if codigo in CHUVA:
        return "chuva"
    if codigo in NEVE:
        return "neve"
    if codigo in NUBLADO:
        return "nublado"
    return "sol" if codigo == 0 else None


def agora(lat: float, lon: float) -> str | None:
    try:
        resp = requests.get(URL, params={"latitude": round(lat, 2), "longitude": round(lon, 2),
                                         "current": "weather_code"},
                            headers={"User-Agent": USER_AGENT}, timeout=5)
        resp.raise_for_status()
        return de_codigo(resp.json()["current"]["weather_code"])
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return None
