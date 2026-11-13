"""IA open source, juiz principal do jogo (src/visao.py), com a rede mockada: formato da resposta, validação e erros."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests

from src import jogo, visao

URL = "http://localhost:11434/v1"


def _api(texto: str, status: int = 200):
    r = MagicMock(status_code=status)
    r.json.return_value = {"choices": [{"message": {"role": "assistant", "content": texto}}]}
    return r


def test_erros_viram_errovisao():
    with patch("src.visao.requests.post", side_effect=requests.Timeout("lento")):
        with pytest.raises(visao.ErroVisao, match="sem conexão"):
            visao.identificar_captura(b"x", URL)
    ruim = MagicMock(status_code=401)
    ruim.json.return_value = {"error": {"message": "Unauthorized"}}  # formato OpenAI/Mistral
    with patch("src.visao.requests.post", return_value=ruim):
        with pytest.raises(visao.ErroVisao, match="401: Unauthorized"):
            visao.identificar_captura(b"x", URL)
    sem_modelo = MagicMock(status_code=404)
    sem_modelo.json.return_value = {"error": "model 'qwen2.5vl:7b' not found"}  # formato Ollama
    with patch("src.visao.requests.post", return_value=sem_modelo):
        with pytest.raises(visao.ErroVisao, match="404: model"):
            visao.identificar_captura(b"x", URL)
    with patch("src.visao.requests.post", return_value=_api("não sei o que é")):
        with pytest.raises(visao.ErroVisao, match="sem JSON"):
            visao.identificar_captura(b"x", URL)
    vazio = MagicMock(status_code=200)
    vazio.json.return_value = {"choices": []}
    with patch("src.visao.requests.post", return_value=vazio):
        with pytest.raises(visao.ErroVisao, match="vazia"):
            visao.identificar_captura(b"x", URL)


def test_captura_do_jogo():
    r = visao.interpretar_captura({"tema": "carros", "achado": "Volkswagen Gol", "foto_real": True, "certeza": 0.8})
    assert (r.tema, r.achado, r.foto_real, r.confianca) == ("carros", "Volkswagen Gol", True, 0.8)
    r = visao.interpretar_captura({"tema": "nenhum", "achado": "geladeira", "foto_real": True})
    assert r.tema is None and r.achado == ""
    r = visao.interpretar_captura({"tema": "pets", "achado": "gato <b>", "foto_real": "false"})
    assert r.foto_real is False and r.achado == ""  # texto perigoso descartado
    texto = '```json\n{"tema": "passaros", "achado": "bem-te-vi", "foto_real": false, "certeza": 0.9}\n```'
    with patch("src.visao.requests.post", return_value=_api(texto)) as post:
        r = visao.identificar_captura(b"jpeg", URL + "/", "mistral-small-latest", chave="segredo")
    assert r.tema == "passaros" and r.foto_real is False
    assert post.call_args.args[0] == URL + "/chat/completions"
    assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer segredo"}
    corpo = post.call_args.kwargs["json"]
    assert corpo["model"] == "mistral-small-latest"
    texto_parte, imagem_parte = corpo["messages"][0]["content"]
    assert imagem_parte["image_url"]["url"].startswith("data:image/jpeg;base64,")
    prompt = texto_parte["text"]
    assert "IMAGEM" in prompt
    for periferico in ("mouse", "teclado", "monitor"):  # periféricos contam como peças
        assert periferico in prompt
    r = visao.interpretar_captura({"tema": "pecas", "achado": "mouse", "foto_real": True, "certeza": 0.9})
    assert (r.tema, r.achado) == ("pecas", "mouse")


def test_sem_chave_nao_manda_autorizacao():
    with patch("src.visao.requests.post", return_value=_api('{"tema": "pets", "achado": "gato", "foto_real": true}')) as post:
        visao.identificar_captura(b"jpeg", URL)  # Ollama local não usa chave
    assert post.call_args.kwargs["headers"] == {}
    assert post.call_args.kwargs["json"]["model"] == visao.MODELO_PADRAO


def test_prompt_cita_sinais_de_foto_de_tela():
    for sinal in ("moiré", "borda", "reflexo", "QUALQUER"):
        assert sinal in visao.PROMPT_CAPTURA


def test_capturas_antigas_do_gemma_continuam_valendo():
    """O juiz principal era o Gemma: o que foi gravado como "gemma+clip" é lido como "ia+clip"."""
    assert jogo.normalizar_juiz("gemma+clip") == "ia+clip" and jogo.normalizar_juiz("gemma") == "ia"
    assert jogo.normalizar_juiz("clip") == "clip" and jogo.normalizar_juiz(None) is None
    for juiz in ("gemma+clip", "ia+clip"):
        assert "discordaram" in jogo.veto_clip("carros", juiz, "plantas", 0.05, 0.1, 5)
