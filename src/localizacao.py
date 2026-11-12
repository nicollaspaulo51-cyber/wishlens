"""Localização do usuário via Nominatim (geocodificador aberto do OpenStreetMap, dados ODbL).

Política de uso do Nominatim: User-Agent identificável e no máximo 1 requisição por segundo.
O app guarda em cache as respostas; aqui garantimos o intervalo mínimo entre chamadas.
"""

from __future__ import annotations

import threading
import time

import requests

from src.lugares import USER_AGENT

NOMINATIM_URL = "https://nominatim.openstreetmap.org"

_trava = threading.Lock()
_ultima_chamada = 0.0


def _get(caminho: str, params: dict):
    global _ultima_chamada
    with _trava:  # no máximo 1 req/s, mesmo com várias sessões do Streamlit
        espera = 1.0 - (time.monotonic() - _ultima_chamada)
        if espera > 0:
            time.sleep(espera)
        _ultima_chamada = time.monotonic()
    resp = requests.get(NOMINATIM_URL + caminho, params={"format": "jsonv2", **params},
                        headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def geocodificar(endereco: str) -> tuple[float, float, str] | None:
    """Converte um endereço/bairro em (lat, lon, nome encontrado); None se não achar."""
    endereco = endereco.strip()
    if not endereco:
        return None
    achados = _get("/search", {"q": endereco, "countrycodes": "br", "limit": 1})
    if not achados:
        return None
    a = achados[0]
    return float(a["lat"]), float(a["lon"]), a.get("display_name", endereco)


def bairro_de(lat: float, lon: float) -> str | None:
    """Coordenada → "Bairro, Cidade - UF". Só isso é guardado (nunca a coordenada exata)."""
    dados = _get("/reverse", {"lat": lat, "lon": lon, "zoom": 16, "addressdetails": 1})
    end = dados.get("address") or {}
    bairro = end.get("suburb") or end.get("neighbourhood") or end.get("quarter")
    cidade = end.get("city") or end.get("town") or end.get("village") or end.get("municipality")
    if not cidade:
        return None
    uf = end.get("ISO3166-2-lvl4", "").removeprefix("BR-")
    texto = f"{cidade} - {uf}" if uf else cidade
    return f"{bairro}, {texto}" if bairro else texto
