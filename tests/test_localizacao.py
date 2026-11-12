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


def test_finalidade_do_local():
    f = lugares.finalidade
    assert f({"shop": "computer"}, "Lan House do Zé") == "jogar"       # marcada como loja, mas é lan house
    assert f({"amenity": "internet_cafe"}, "X") == "jogar"
    assert f({"shop": "electronics"}, "Assistência Técnica X") == "consertar"
    assert f({"craft": "electronics_repair"}, "Y") == "consertar"
    assert f({"amenity": "animal_shelter"}, "Abrigo") == "adotar"
    assert f({"amenity": "veterinary"}, "Clínica") == "cuidar"
    assert f({"amenity": "restaurant"}, "Cantina") == "comer"
    assert f({"shop": "computer"}, "Cyber Informática") == "comprar"   # "cyber" sozinho não é lan house


def test_lugares_trazem_finalidade():
    with patch("src.lugares.requests.post", return_value=_resposta(ELEMENTOS)):
        achados = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)
    assert {l["nome"]: l["finalidade"] for l in achados} == {"Perto": "adotar", "Longe": "comprar"}


def test_filtro_ancorado():
    from src.categorias import ITENS
    carro = next(i for i in ITENS if i.categoria == "veículos")
    q = lugares.montar_consulta(carro, 0, 0, 100)
    assert 'shop~"^(car|motorcycle)$"' in q  # não casa carpet nem car_repair
    assert lugares.tags_simples(carro) == ["[shop=car]", "[shop=motorcycle]"]


def test_detalhes_do_lugar_no_overpass():
    el = {"elements": [{"type": "node", "id": 5, "lat": -20.301, "lon": -40.30, "tags": {
        "name": "Loja X", "shop": "pet", "addr:street": "Rua A", "addr:housenumber": "10",
        "addr:suburb": "Centro", "opening_hours": "Mo-Fr 09:00-18:00", "phone": "+55 27 3333-4444",
        "website": "loja.com.br", "contact:website": "javascript:alert(1)"}}]}
    with patch("src.lugares.requests.post", return_value=_resposta(el)):
        [l] = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)
    assert l["endereco"] == "Rua A 10, Centro"
    assert l["horario"] == "Mo-Fr 09:00-18:00" and l["telefone"] == "+55 27 3333-4444"
    assert l["site"] == "https://loja.com.br"
    assert lugares.horario_legivel(l["horario"]) == "seg–sex 09:00–18:00"


def test_links_perigosos_do_osm_sao_ignorados():
    d = lugares.detalhes_osm({"website": "javascript:alert(1)", "phone": "<b>ligue</b>"})
    assert d["site"] is None and d["telefone"] is None


def test_nominatim_traz_endereco():
    achado = {"osm_type": "node", "osm_id": 9, "lat": "-20.301", "lon": "-40.30", "name": "Clínica",
              "type": "veterinary", "address": {"road": "Av. B", "house_number": "5", "city": "Vitória"},
              "extratags": {"opening_hours": "24/7"}}
    with patch("src.lugares.requests.post", side_effect=requests.Timeout("lento")), \
         patch("src.localizacao.requests.get", return_value=_resposta([achado])) as get:
        [l] = lugares.buscar_proximos(ANIMAIS, -20.30, -40.30)
    assert l["endereco"] == "Av. B 5, Vitória" and l["horario"] == "24/7"
    assert get.call_args.kwargs["params"]["extratags"] == 1


def test_nominatim_responde_vazio_nao_e_erro():
    # uma tag falha e as outras respondem "nada": é "nada por perto", não erro
    respostas = iter([requests.ConnectionError("x"), [], []])

    def get(*a, **kw):
        r = next(respostas)
        if isinstance(r, Exception):
            raise r
        return _resposta(r)

    with patch("src.lugares.requests.post", side_effect=requests.Timeout("lento")), \
         patch("src.localizacao.requests.get", side_effect=get):
        assert lugares.buscar_proximos(ANIMAIS, -20.30, -40.30) == []


def test_lugar_clicado_e_rotas():
    ls = [{"nome": "A", "lat": -20.30, "lon": -40.30}, {"nome": "B", "lat": -20.31, "lon": -40.31}]
    assert lugares.lugar_mais_proximo(ls, -20.310001, -40.30999)["nome"] == "B"
    assert lugares.lugar_mais_proximo(ls, -20.5, -40.5) is None  # clique no marcador "Você"
    assert lugares.lugar_mais_proximo([], 0, 0) is None
    rotas = lugares.como_chegar(-20.3, -40.3)
    assert rotas["Google Maps"].endswith("destination=-20.3,-40.3") and "waze.com" in rotas["Waze"]


def test_coordenada_zero_nao_e_ausente():
    el = {"elements": [{"type": "node", "id": 1, "lat": 0.0, "lon": 0.001, "tags": {"name": "Equador"}}]}
    with patch("src.lugares.requests.post", return_value=_resposta(el)):
        assert [l["nome"] for l in lugares.buscar_proximos(ANIMAIS, 0.0, 0.0)] == ["Equador"]
