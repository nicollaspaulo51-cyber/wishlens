"""Gemma (src/visao.py) com a rede mockada: formato da resposta, validação e erros."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests

from src import visao


def _api(texto: str, status: int = 200):
    r = MagicMock(status_code=status)
    r.json.return_value = {"candidates": [{"content": {"parts": [{"text": texto}]}}]}
    return r


TENIS = {"nome": "tênis", "marca": "Nike", "modelo": "Air Max 90", "categoria": "calçados",
         "preco_min": 600, "preco_max": 1000, "certeza": 0.9}


def test_identifica_com_marca_e_preco():
    texto = "```json\n" + json.dumps(TENIS, ensure_ascii=False) + "\n```"
    with patch("src.visao.requests.post", return_value=_api(texto)) as post:
        r = visao.identificar(b"jpeg", "chave", "gemma-3-27b-it")
    assert (r.item.nome, r.item.marca, r.item.modelo, r.item.tipo) == ("tênis", "Nike", "Air Max 90", "comprar")
    assert (r.preco_min, r.preco_max, r.confianca) == (600, 1000, 0.9)
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "chave"  # chave no cabeçalho, não na URL
    assert "chave" not in post.call_args.args[0]
    assert "gemma-3-27b-it" in post.call_args.args[0]
    parte_imagem = post.call_args.kwargs["json"]["contents"][0]["parts"][1]
    assert parte_imagem["inline_data"]["mime_type"] == "image/jpeg"


def test_categoria_fora_da_lista_e_erro():
    with pytest.raises(visao.ErroVisao):
        visao.interpretar({**TENIS, "categoria": "foguetes"})


def test_textos_perigosos_sao_descartados():
    r = visao.interpretar({**TENIS, "marca": "<script>alert(1)</script>", "modelo": "Nike"})
    assert r.item.marca == "" and r.item.modelo == "Nike"
    r = visao.interpretar({**TENIS, "modelo": "nike"})
    assert r.item.modelo == ""  # modelo igual à marca não repete


def test_preco_invertido_ou_invalido():
    r = visao.interpretar({**TENIS, "preco_min": 900, "preco_max": 300})
    assert (r.preco_min, r.preco_max) == (300, 900)
    r = visao.interpretar({**TENIS, "preco_min": "caro", "preco_max": 300})
    assert (r.preco_min, r.preco_max) == (None, None)
    r = visao.interpretar({**TENIS, "categoria": "animais", "preco_min": 0, "preco_max": 0})
    assert r.preco_min is None and r.item.tipo == "adotar"


def test_erros_viram_errovisao():
    with patch("src.visao.requests.post", side_effect=requests.Timeout("lento")):
        with pytest.raises(visao.ErroVisao, match="sem conexão"):
            visao.identificar(b"x", "k")
    ruim = MagicMock(status_code=403)
    ruim.json.return_value = {"error": {"message": "API key not valid"}}
    with patch("src.visao.requests.post", return_value=ruim):
        with pytest.raises(visao.ErroVisao, match="403: API key not valid"):
            visao.identificar(b"x", "k")
    with patch("src.visao.requests.post", return_value=_api("não sei o que é")):
        with pytest.raises(visao.ErroVisao, match="sem JSON"):
            visao.identificar(b"x", "k")
    vazio = MagicMock(status_code=200)
    vazio.json.return_value = {"candidates": []}
    with patch("src.visao.requests.post", return_value=vazio):
        with pytest.raises(visao.ErroVisao, match="vazia"):
            visao.identificar(b"x", "k")


def test_captura_do_jogo():
    r = visao.interpretar_captura({"tema": "carros", "achado": "Volkswagen Gol", "foto_real": True, "certeza": 0.8})
    assert (r.tema, r.achado, r.foto_real, r.confianca) == ("carros", "Volkswagen Gol", True, 0.8)
    r = visao.interpretar_captura({"tema": "nenhum", "achado": "geladeira", "foto_real": True})
    assert r.tema is None and r.achado == ""
    r = visao.interpretar_captura({"tema": "pets", "achado": "gato <b>", "foto_real": "false"})
    assert r.foto_real is False and r.achado == ""  # texto perigoso descartado
    texto = '{"tema": "passaros", "achado": "bem-te-vi", "foto_real": false, "certeza": 0.9}'
    with patch("src.visao.requests.post", return_value=_api(texto)) as post:
        r = visao.identificar_captura(b"jpeg", "k")
    assert r.tema == "passaros" and r.foto_real is False
    prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
    assert "IMAGEM" in prompt
    for periferico in ("mouse", "teclado", "monitor"):  # periféricos contam como peças
        assert periferico in prompt
    r = visao.interpretar_captura({"tema": "pecas", "achado": "mouse", "foto_real": True, "certeza": 0.9})
    assert (r.tema, r.achado) == ("pecas", "mouse")
