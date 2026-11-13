"""Localização (Nominatim) e lugares (Overpass) com a rede mockada."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests

from src import localizacao, lugares
from src.temas import POR_ID


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


PETS = POR_ID["pets"]
ELEMENTOS = {"elements": [
    {"type": "node", "id": 2, "lat": -20.40, "lon": -40.30, "tags": {"name": "Longe", "shop": "pet"}},
    {"type": "way", "id": 1, "center": {"lat": -20.301, "lon": -40.30}, "tags": {"name": "Perto", "leisure": "dog_park"}},
    {"type": "node", "id": 3, "tags": {}},  # sem coordenada: ignorado
]}


def test_overpass_usa_espelho_e_ordena():
    chamadas = []

    def post(url, **kw):
        chamadas.append(url)
        if url == lugares.OVERPASS_URLS[0]:
            raise requests.ConnectionError("fora do ar")
        return _resposta(ELEMENTOS)

    with patch("src.lugares.requests.post", side_effect=post):
        achados = lugares.buscar_pontos_temas([PETS], -20.30, -40.30, raio_m=20000)
    assert chamadas == lugares.OVERPASS_URLS[:2]
    assert [l["nome"] for l in achados] == ["Perto", "Longe"]


def test_overpass_remark_de_erro_tenta_o_proximo():
    lotado = {"elements": [], "remark": "runtime error: Query timed out"}
    respostas = iter([_resposta(lotado), _resposta(ELEMENTOS)])
    with patch("src.lugares.requests.post", side_effect=lambda url, **kw: next(respostas)):
        achados = lugares.buscar_pontos_temas([PETS], -20.30, -40.30, raio_m=20000)
    assert [l["nome"] for l in achados] == ["Perto", "Longe"]


def test_filtro_ancorado():
    assert lugares._ancorado('shop~"car|motorcycle"') == 'shop~"^(car|motorcycle)$"'  # não casa carpet
    assert lugares._ancorado('amenity="parking"') == 'amenity="parking"'


def test_detalhes_do_lugar_e_coordenada_zero():
    el = {"elements": [
        {"type": "node", "id": 5, "lat": -20.301, "lon": -40.30, "tags": {
            "name": "Pet X", "shop": "pet", "addr:street": "Rua A", "addr:housenumber": "10",
            "addr:suburb": "Centro", "opening_hours": "Mo-Fr 09:00-18:00", "phone": "+55 27 3333-4444",
            "website": "loja.com.br"}},
        {"type": "node", "id": 6, "lat": 0.0, "lon": 0.001, "tags": {"name": "Equador", "shop": "pet"}},
    ]}
    with patch("src.lugares.requests.post", return_value=_resposta(el)):
        perto = lugares.buscar_pontos_temas([PETS], -20.30, -40.30)
        zero = lugares.buscar_pontos_temas([PETS], 0.0, 0.0)
    l = next(x for x in perto if x["nome"] == "Pet X")
    assert l["endereco"] == "Rua A 10, Centro" and l["telefone"] == "+55 27 3333-4444"
    assert l["site"] == "https://loja.com.br"
    assert lugares.horario_legivel(l["horario"]) == "seg–sex 09:00–18:00"
    assert "Equador" in {x["nome"] for x in zero}  # latitude 0 não é "sem coordenada"


def test_links_perigosos_do_osm_sao_ignorados():
    d = lugares.detalhes_osm({"website": "javascript:alert(1)", "phone": "<b>ligue</b>"})
    assert d["site"] is None and d["telefone"] is None


def test_lugar_clicado_e_rotas():
    ls = [{"nome": "A", "lat": -20.30, "lon": -40.30}, {"nome": "B", "lat": -20.31, "lon": -40.31}]
    assert lugares.lugar_mais_proximo(ls, -20.310001, -40.30999)["nome"] == "B"
    assert lugares.lugar_mais_proximo(ls, -20.5, -40.5) is None  # clique no marcador "Você"
    assert lugares.lugar_mais_proximo([], 0, 0) is None
    rotas = lugares.como_chegar(-20.3, -40.3)
    assert rotas["Google Maps"].endswith("destination=-20.3,-40.3") and "waze.com" in rotas["Waze"]


def test_pontos_por_tema_numa_consulta_so():
    from src.temas import POR_ID
    el = {"elements": [
        {"type": "way", "id": 1, "center": {"lat": -20.301, "lon": -40.30}, "tags": {"leisure": "park", "name": "Parque"}},
        {"type": "node", "id": 2, "lat": -20.302, "lon": -40.30, "tags": {"amenity": "parking"}},
        {"type": "node", "id": 3, "lat": -20.303, "lon": -40.30, "tags": {"shop": "car_repair"}},  # não é shop=car
    ]}
    temas = [POR_ID["carros"], POR_ID["passaros"], POR_ID["plantas"]]
    with patch("src.lugares.requests.post", return_value=_resposta(el)) as post:
        pontos = lugares.buscar_pontos_temas(temas, -20.30, -40.30, raio_m=1000)
    assert post.call_count == 1
    por = {(p["tema"], p["nome"]) for p in pontos}
    assert por == {("passaros", "Parque"), ("plantas", "Parque"), ("carros", "Estacionamentos")}
    with patch("src.lugares.requests.post", side_effect=requests.Timeout("x")):
        with pytest.raises(RuntimeError):
            lugares.buscar_pontos_temas(temas, 0, 0)
