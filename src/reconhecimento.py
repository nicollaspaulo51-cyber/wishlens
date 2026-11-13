"""Segundo juiz do jogo: CLIP da OpenAI (modelo aberto) por classificação zero-shot.

O CLIP compara a foto com frases de texto ("a photo of a computer mouse", "a photo of a computer
screen showing a bird"...) e diz qual combina mais. Não é preciso treinar nada.

Grupos de frases: os 5 temas (src/temas.py), "tela" (foto de tela, impressão, desenho ou brinquedo,
com frases gêmeas de cada objeto dos temas) e "nenhum" (pessoa, comida, quarto...).
"""

from __future__ import annotations

import threading
from functools import lru_cache

from PIL import Image

MODELO = "openai/clip-vit-base-patch32"  # pesos abertos (licença MIT)


def _vetor(saida):
    # transformers 5 devolve um objeto com o vetor projetado em .pooler_output; o 4.x devolve o tensor
    return getattr(saida, "pooler_output", saida)


_trava = threading.Lock()
_aquecimento: threading.Thread | None = None


@lru_cache(maxsize=1)
def _carregar_uma_vez():
    from transformers import CLIPModel, CLIPProcessor

    modelo = CLIPModel.from_pretrained(MODELO)
    processador = CLIPProcessor.from_pretrained(MODELO)
    modelo.eval()
    return modelo, processador


def _carregar():
    """Modelo e processador do CLIP, uma vez por processo (~600 MB baixados na 1ª vez, ~12 s para carregar).
    A trava evita carregar duas vezes quando a foto chega antes de o aquecimento terminar."""
    with _trava:
        return _carregar_uma_vez()


def aquecer() -> None:
    """Carrega o CLIP numa thread assim que a tela abre: a 1ª foto não espera o carregamento."""
    global _aquecimento
    if _aquecimento is None:
        _aquecimento = threading.Thread(target=_vetores_captura, daemon=True, name="aquecer-clip")
        _aquecimento.start()


def frases_captura() -> list[tuple[str, str, str]]:
    """(grupo, frase, nome em português): grupo = id do tema, "tela" (não vale) ou "nenhum"."""
    from src.temas import FRASES_NENHUM, FRASES_TELA, TEMAS
    return ([(t.id, f"a photo of {o}", nome) for t in TEMAS for o, nome in t.objetos_clip]
            + [("tela", f, "") for f in FRASES_TELA] + [("nenhum", f, "") for f in FRASES_NENHUM])


@lru_cache(maxsize=1)
def _vetores_captura():
    import torch

    modelo, processador = _carregar()
    frases = frases_captura()
    with torch.no_grad():
        entrada = processador(text=[f for _, f, _ in frases], return_tensors="pt", padding=True)
        vet = _vetor(modelo.get_text_features(**entrada))
    return vet / vet.norm(dim=-1, keepdim=True), frases


def probs_por_grupo(grupos: list[str], probs: list[float]) -> dict[str, float]:
    """Chance de cada grupo = a da sua MELHOR frase, renormalizada (soma 1).

    Somar as frases favorecia o grupo com mais frases; a média afogava a frase certa
    (um mouse só bate com "a computer mouse", não com as outras 10 frases de peças).
    """
    melhor: dict[str, float] = {}
    for g, p in zip(grupos, probs):
        melhor[g] = max(melhor.get(g, 0.0), p)
    total = sum(melhor.values()) or 1.0
    return {g: p / total for g, p in melhor.items()}


def decidir_captura(grupos: list[str], probs: list[float]) -> tuple[str | None, bool, float]:
    """Chance por grupo -> (tema ou None, foto_real, confiança do tema). Sem torch, para testar.

    foto_real = falso quando "tela" é o 1º palpite (o CLIP é "confiante demais" para usar um limite
    de chance). Exceção: peças de computador, porque monitor e notebook ligados são peças.
    """
    por_grupo = probs_por_grupo(grupos, probs)
    temas = {g: p for g, p in por_grupo.items() if g not in ("tela", "nenhum")}
    melhor = max(temas, key=temas.get)
    tela, nenhum = por_grupo.get("tela", 0.0), por_grupo.get("nenhum", 0.0)
    if melhor != "pecas" and tela >= max(temas[melhor], nenhum):
        return melhor, False, temas[melhor]
    if nenhum > temas[melhor]:
        return None, True, nenhum
    return melhor, True, temas[melhor]


def achado_do_tema(frases: list[tuple[str, str, str]], probs: list[float], tema: str) -> str:
    """Nome em português da frase do tema que mais combinou (ex.: "mouse", "teclado", "flor")."""
    candidatas = [(p, nome) for (g, _, nome), p in zip(frases, probs) if g == tema]
    return max(candidatas)[1] if candidatas else ""


def julgar_clip(imagem: Image.Image) -> dict:
    """Opinião do CLIP: tema (ou None), achado, foto_real, confiança, a chance de cada grupo e o vetor da foto
    (512 números normalizados: o "retrato" usado para saber se o mesmo objeto já foi fotografado)."""
    import torch

    modelo, processador = _carregar()
    vet_texto, frases = _vetores_captura()
    with torch.no_grad():
        entrada = processador(images=imagem.convert("RGB"), return_tensors="pt")
        vet_img = _vetor(modelo.get_image_features(**entrada))
        vet_img = vet_img / vet_img.norm(dim=-1, keepdim=True)
        probs = (modelo.logit_scale.exp() * vet_img @ vet_texto.T).softmax(dim=-1)[0].tolist()
    grupos = [g for g, _, _ in frases]
    tema, real, conf = decidir_captura(grupos, probs)
    return {"tema": tema, "achado": achado_do_tema(frases, probs, tema) if tema else "",
            "foto_real": real, "confianca": conf, "probs": probs_por_grupo(grupos, probs),
            "vetor": [round(x, 4) for x in vet_img[0].tolist()]}


def capturar(imagem: Image.Image):
    """Reserva do jogo sem a IA (juiz principal): o CLIP decide sozinho (achado = o objeto que mais combinou)."""
    from src.visao import Captura

    j = julgar_clip(imagem)
    return Captura(j["tema"], j["achado"], j["foto_real"], j["confianca"])
