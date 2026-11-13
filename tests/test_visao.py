"""Gemma, juiz do jogo (src/visao.py), com a rede mockada: formato da resposta, validação e erros."""

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


def test_erros_viram_errovisao():
    with patch("src.visao.requests.post", side_effect=requests.Timeout("lento")):
        with pytest.raises(visao.ErroVisao, match="sem conexão"):
            visao.identificar_captura(b"x", "k")
    ruim = MagicMock(status_code=403)
    ruim.json.return_value = {"error": {"message": "API key not valid"}}
    with patch("src.visao.requests.post", return_value=ruim):
        with pytest.raises(visao.ErroVisao, match="403: API key not valid"):
            visao.identificar_captura(b"x", "k")
    with patch("src.visao.requests.post", return_value=_api("não sei o que é")):
        with pytest.raises(visao.ErroVisao, match="sem JSON"):
            visao.identificar_captura(b"x", "k")
    vazio = MagicMock(status_code=200)
    vazio.json.return_value = {"candidates": []}
    with patch("src.visao.requests.post", return_value=vazio):
        with pytest.raises(visao.ErroVisao, match="vazia"):
            visao.identificar_captura(b"x", "k")


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


def test_prompt_cita_sinais_de_foto_de_tela():
    for sinal in ("moiré", "borda", "reflexo", "QUALQUER"):
        assert sinal in visao.PROMPT_CAPTURA
