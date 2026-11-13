"""Juiz principal do jogo: Gemma (pesos abertos do Google) pela API do Google AI Studio.

Diz o tema, o achado (modelo do carro, espécie, raça, peça) e se a foto é real (não é tela/impressão).
Só roda com GEMINI_API_KEY em .streamlit/secrets.toml (chave gratuita em aistudio.google.com).
Sem chave, ou se a chamada falhar, o CLIP julga sozinho (src/reconhecimento.py).

Por que Gemma: o projeto pede stack aberto. Gemma tem pesos abertos (licença Gemma, não é OSI),
mas é grande demais para rodar no Streamlit Cloud gratuito (~1 GB de RAM, sem GPU); por isso é
chamado pela API. O modelo pode ser trocado em GEMMA_MODELO (secrets).

Privacidade: a foto enviada é a de fotos.preparar_para_salvar (sem EXIF/GPS, no máximo 1024 px).
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

import requests

from src.categorias import nome_valido
from src.temas import TEMAS

API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELO_PADRAO = "gemma-3-27b-it"
TIMEOUT = 20

class ErroVisao(Exception):
    """Falha ao consultar o Gemma (rede, chave, cota ou resposta fora do formato)."""


def _extrair_json(texto: str) -> dict:
    """O Gemma não tem modo JSON na API: tira ```json ... ``` e pega o 1º objeto do texto."""
    achado = re.search(r"\{.*\}", texto, re.S)
    if not achado:
        raise ErroVisao("resposta sem JSON")
    try:
        dados = json.loads(achado.group(0))
    except json.JSONDecodeError as e:
        raise ErroVisao("JSON inválido na resposta") from e
    if not isinstance(dados, dict):
        raise ErroVisao("JSON inesperado")
    return dados


def _numero(valor) -> float | None:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    return v if 0 <= v < 10_000_000 else None


def _texto(valor, limite: int = 40) -> str:
    """Nome/marca/modelo: limpa e só aceita o que nome_valido aceita (vão para HTML)."""
    v = re.sub(r"\s+", " ", str(valor or "")).strip()[:limite]
    return v if v and nome_valido(v) else ""


def _chamar(jpeg: bytes, chave: str, modelo: str, prompt: str) -> str:
    """Envia texto + foto ao modelo e devolve o texto da resposta. Lança ErroVisao em falha."""
    corpo = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
        ]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300},
    }
    try:
        resp = requests.post(API.format(modelo=modelo), json=corpo, timeout=TIMEOUT,
                             headers={"x-goog-api-key": chave})
    except requests.RequestException as e:
        raise ErroVisao(f"sem conexão com a API ({type(e).__name__})") from e
    if resp.status_code != 200:
        try:
            motivo = resp.json()["error"]["message"][:200]
        except Exception:
            motivo = resp.text[:200]
        raise ErroVisao(f"API respondeu {resp.status_code}: {motivo}")
    try:
        partes = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in partes)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ErroVisao("resposta vazia (a foto pode ter sido bloqueada pelo filtro)") from e


# ---------------------------------------------------------------- jogo: captura de um tema
PROMPT_CAPTURA = """Você é o juiz de um jogo de fotos. A pessoa deve fotografar, na vida real, algo de um destes temas:
""" + "\n".join(f"- {t.id}: {t.nome}. Conta: {t.conta}. Achado = {t.achado}" for t in TEMAS) + """
Responda SOMENTE com um objeto JSON, sem texto antes ou depois:
{"tema": "id do tema (um dos acima) ou \\"nenhum\\"",
 "achado": "o achado no formato pedido para o tema, em português; vazio se tema = nenhum",
 "foto_real": true ou false,
 "certeza": número de 0 a 1}
Regras do tema:
- Olhe o objeto PRINCIPAL da foto. Se ele se encaixa no "Conta" de algum tema, use esse tema.
- Na dúvida entre um tema e "nenhum", escolha o tema. Use "nenhum" só se claramente não for de nenhum.
- Exemplo: um mouse, um teclado ou um monitor em cima da mesa são do tema "pecas".
Regras de foto_real (é a regra mais importante: o jogo é sobre achar coisas na vida real):
- false se a foto mostra uma IMAGEM do objeto em outra tela (foto de um pássaro aberta no celular ou no monitor),
  uma imagem impressa, um desenho, um brinquedo/miniatura ou a figura numa embalagem.
- Sinais de foto de tela: borda ou moldura de monitor/celular/TV, padrão de pixels ou listras onduladas (moiré),
  reflexo ou brilho da tela, cores lavadas ou "chapadas", imagem plana sem profundidade, barras ou bordas de
  janela, de navegador ou de aplicativo. Se houver QUALQUER um desses sinais, foto_real = false.
- true se o próprio objeto está na frente da câmera. Um monitor, notebook ou celular fotografado como objeto
  (tema pecas) é foto real, mesmo com a tela ligada.
Não invente: se não der para ver o modelo, a espécie ou a raça, use o nome genérico (ex.: "carro", "planta", "pássaro", "mouse")."""


@dataclass
class Captura:
    tema: str | None        # id do tema, ou None se não é de nenhum
    achado: str
    foto_real: bool
    confianca: float | None


def interpretar_captura(dados: dict) -> Captura:
    ids = {t.id for t in TEMAS}
    tema = str(dados.get("tema", "")).strip().lower()
    tema = tema if tema in ids else None
    achado = _texto(dados.get("achado"), limite=60) if tema else ""
    real = dados.get("foto_real")
    real = real if isinstance(real, bool) else str(real).strip().lower() in {"true", "sim", "1"}
    certeza = _numero(dados.get("certeza"))
    return Captura(tema, achado, real, min(certeza, 1.0) if certeza is not None else None)


def identificar_captura(jpeg: bytes, chave: str, modelo: str = MODELO_PADRAO) -> Captura:
    """Tema, achado (marca/modelo, espécie, raça ou peça) e se é foto real. Lança ErroVisao em falha."""
    return interpretar_captura(_extrair_json(_chamar(jpeg, chave, modelo, PROMPT_CAPTURA)))
