"""Localização (Nominatim) e lugares (Overpass) com a rede mockada."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests

from src import localizacao, lugares
from src.categorias import ITENS


def _resposta(json):
    r = MagicMock()
    r.json.return_value = json
    return r


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(localizacao.time, "sleep", lambda s: None)


def test_geocodificar_encontra():
    with patch("src.localizacao.requests.get",
               return_value=_resposta([{"lat": "-20.29", "lon": "-40.29", "display_name": "Jardim da Penha"}])) as get:
        assert localizacao.geocodificar("Jardim da Penha, Vitória") == (-20.29, -40.29, "Jardim da Penha")
    assert "WishLens" in get.call_args.kwargs["headers"]["User-Agent"]
    assert get.call_args.kwargs["params"]["countrycodes"] == "br"


def test_geocodificar_nada():
    with patch("src.localizacao.requests.get", return_value=_resposta([])):
        assert localizacao.geocodificar("lugar que não existe") is None
    assert localizacao.geocodificar("   ") is None


def test_bairro_de():
    end = {"suburb": "Jardim da Penha", "city": "Vitória", "ISO3166-2-lvl4": "BR-ES"}
    with patch("src.localizacao.requests.get", return_value=_resposta({"address": end})):
        assert localizacao.bairro_de(-20.29, -40.29) == "Jardim da Penha, Vitória - ES"
    with patch("src.localizacao.requests.get", return_value=_resposta({"address": {}})):
        assert localizacao.bairro_de(0, 0) is None


ANIMAIS = next(i for i in ITENS if i.tipo == "adotar")
ELEMENTOS = {"elements": [
    {"type": "node", "id": 2, "lat": -20.40, "lon": -40.30, "tags": {"name": "Longe", "shop": "pet"}},
    {"type": "way", "id": 1, "center": {"lat": -20.301, "lon": -40.30}, "tags": {"name": "Perto", "amenity": "animal_shelter"}},
    {"type": "node", "id": 3, "tags": {}},  # sem coordenada: ignorado
]}


def test_overpass_usa_espelho_e_ordena():
    falha = MagicMock(side_effect=requests.ConnectionError("fora do ar"))
    chamadas = []

    def post(url, **kw):
        chamadas.append(url)
        if url == lugares.OVERPASS_URLS[0]:
            falha()
        return _resposta(ELEMENTOS)

    with patch("src.lugares.requests.post", side_effect=post):
        achados = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)
    assert chamadas == lugares.OVERPASS_URLS[:2]
    assert [l["nome"] for l in achados] == ["Perto", "Longe"]


def test_tags_simples():
    assert lugares.tags_simples(ANIMAIS) == ["[amenity=animal_shelter]", "[shop=pet]", "[amenity=veterinary]"]


def test_overpass_fora_usa_nominatim():
    achado = {"osm_type": "node", "osm_id": 9, "lat": "-20.301", "lon": "-40.30",
              "name": "Clínica", "type": "veterinary"}
    longe = {"osm_type": "node", "osm_id": 8, "lat": "-21.0", "lon": "-40.30", "name": "Fora", "type": "pet"}
    with patch("src.lugares.requests.post", side_effect=requests.Timeout("lento")), \
         patch("src.localizacao.requests.get", return_value=_resposta([achado, longe])) as get:
        achados = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30, raio_m=3000)
    assert [l["nome"] for l in achados] == ["Clínica"]  # repetido entre tags e fora do raio: descartados
    assert get.call_args.kwargs["params"]["bounded"] == 1


def test_tudo_fora_do_ar():
    with patch("src.lugares.requests.post", side_effect=requests.Timeout("lento")), \
         patch("src.localizacao.requests.get", side_effect=requests.ConnectionError("fora")):
        with pytest.raises(requests.ConnectionError):
            lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)


def test_overpass_remark_de_erro_tenta_o_proximo():
    lotado = {"elements": [], "remark": "runtime error: Query timed out"}
    respostas = iter([_resposta(lotado), _resposta(ELEMENTOS)])
    with patch("src.lugares.requests.post", side_effect=lambda url, **kw: next(respostas)):
        achados = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)
    assert [l["nome"] for l in achados] == ["Perto", "Longe"]
