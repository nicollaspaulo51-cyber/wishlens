"""Juiz principal do jogo: um modelo de visão open source (licença OSI) por API compatível com a da OpenAI.

Diz o tema, o achado (modelo do carro, espécie, raça, peça) e se a foto é real (não é tela/impressão).
Só roda com VISAO_URL em .streamlit/secrets.toml. Sem ela, ou se a chamada falhar, o CLIP julga
sozinho (src/reconhecimento.py).

Open source: só modelos com licença aprovada pela OSI (Apache 2.0, MIT). O Gemma saiu porque a licença
dele não é OSI. O mesmo código fala com:
- Ollama no próprio computador (MIT): VISAO_URL = "http://localhost:11434/v1", modelo qwen2.5vl:7b (Apache 2.0);
- um provedor na nuvem, para o Streamlit Cloud (que não tem RAM para rodar o modelo): ex. a API da Mistral
  com o Mistral Small (Apache 2.0), VISAO_URL = "https://api.mistral.ai/v1" + VISAO_CHAVE + VISAO_MODELO.
Atenção ao trocar de modelo: o Qwen2.5-VL 3B e o 72B NÃO são Apache 2.0; o 7B e o 32B são.

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

MODELO_PADRAO = "qwen2.5vl:7b"
TIMEOUT = 90  # no Ollama sem GPU um modelo de 7B leva dezenas de segundos por foto

class ErroVisao(Exception):
    """Falha ao consultar o modelo (rede, chave, cota, modelo inexistente ou resposta fora do formato)."""


def _extrair_json(texto: str) -> dict:
    """Tolera ```json ... ``` e texto em volta (nem todo provedor respeita o modo JSON): pega o 1º objeto."""
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


def _chamar(jpeg: bytes, url: str, modelo: str, prompt: str, chave: str | None = None) -> str:
    """Envia texto + foto a /chat/completions e devolve o texto da resposta. Lança ErroVisao em falha."""
    imagem = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    corpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": imagem}},
        ]}],
        "temperature": 0.1,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }
    cabecalhos = {"Authorization": f"Bearer {chave}"} if chave else {}
    try:
        resp = requests.post(url.rstrip("/") + "/chat/completions", json=corpo, timeout=TIMEOUT, headers=cabecalhos)
    except requests.RequestException as e:
        raise ErroVisao(f"sem conexão com a API ({type(e).__name__})") from e
    if resp.status_code != 200:
        try:
            erro = resp.json().get("error") or resp.json().get("message")
            motivo = str(erro.get("message", erro) if isinstance(erro, dict) else erro)[:200]
        except Exception:
            motivo = resp.text[:200]
        raise ErroVisao(f"API respondeu {resp.status_code}: {motivo}")
    try:
        texto = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ErroVisao("resposta vazia do modelo") from e
    if not texto:
        raise ErroVisao("resposta vazia do modelo")
    return texto


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


def identificar_captura(jpeg: bytes, url: str, modelo: str = MODELO_PADRAO, chave: str | None = None) -> Captura:
    """Tema, achado (marca/modelo, espécie, raça ou peça) e se é foto real. Lança ErroVisao em falha."""
    return interpretar_captura(_extrair_json(_chamar(jpeg, url, modelo, PROMPT_CAPTURA, chave)))
