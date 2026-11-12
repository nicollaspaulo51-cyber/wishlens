"""Reconhecimento de imagens com CLIP (modelo aberto) por classificação zero-shot.

O CLIP compara a imagem com frases de texto ("a photo of a dog", "a photo of a pizza"...)
e devolve qual frase combina mais. Não é preciso treinar nada.

Vocabulário: o catálogo curado (src/categorias.py, com prioridade) + ~1.100 objetos do LVIS
em data/vocabulario.csv, com vetores de texto já calculados em data/vocabulario_clip.npy
(gerados por scripts/gerar_vocabulario.py).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image

from src.categorias import FAIXA_PRECO, ITENS, Item

MODELO = "openai/clip-vit-base-patch32"  # pesos abertos (licença MIT)
DADOS = Path(__file__).resolve().parents[1] / "data"


# Frases extras para itens que o CLIP confunde (o catálogo tem um rótulo por item)
ROTULOS_EXTRAS = {
    "fone de ouvido": ["wireless earbuds", "a white wireless earbuds charging case"],
}
_ROTULOS = [(i, i.rotulo_en) for i in ITENS] + [
    (i, r) for i in ITENS for r in ROTULOS_EXTRAS.get(i.nome, [])
]


def _vocabulario() -> list[tuple[Item, str]]:
    """Objetos do LVIS (data/vocabulario.csv); vazio se o arquivo não existir."""
    arquivo = DADOS / "vocabulario.csv"
    if not arquivo.exists():
        return []
    with open(arquivo, encoding="utf-8") as f:
        return [(Item(l["rotulo_en"], l["nome"], l["categoria"], l["tipo"]), l["rotulo_en"])
                for l in csv.DictReader(f)]


def _vetor(saida):
    # transformers 5 devolve um objeto com o vetor projetado em .pooler_output; o 4.x devolve o tensor
    return getattr(saida, "pooler_output", saida)


@dataclass
class Resultado:
    item: Item
    confianca: float

    @property
    def faixa_preco(self) -> str:
        return FAIXA_PRECO.get(self.item.categoria, "—")


@lru_cache(maxsize=1)
def _carregar():
    import torch
    from transformers import CLIPModel, CLIPProcessor

    modelo = CLIPModel.from_pretrained(MODELO)
    processador = CLIPProcessor.from_pretrained(MODELO)
    modelo.eval()

    # Os textos são sempre os mesmos: calcula os vetores do catálogo curado uma única vez
    textos = [f"a photo of {r}" for _, r in _ROTULOS]
    with torch.no_grad():
        entrada = processador(text=textos, return_tensors="pt", padding=True)
        vet_texto = _vetor(modelo.get_text_features(**entrada))
        vet_texto = vet_texto / vet_texto.norm(dim=-1, keepdim=True)

    # ... e junta os do vocabulário grande, já calculados
    rotulos = list(_ROTULOS)
    vocab = _vocabulario()
    if vocab:
        import numpy as np

        vet_vocab = torch.from_numpy(np.load(DADOS / "vocabulario_clip.npy").astype("float32"))
        assert len(vet_vocab) == len(vocab), "vocabulario.csv e vocabulario_clip.npy fora de sincronia"
        vet_texto = torch.cat([vet_texto, vet_vocab])
        rotulos += vocab
    return modelo, processador, vet_texto, rotulos


def reconhecer(imagem: Image.Image, top_k: int = 3) -> list[Resultado]:
    """Retorna os top_k itens mais prováveis para a imagem."""
    import torch

    modelo, processador, vet_texto, rotulos = _carregar()
    with torch.no_grad():
        entrada = processador(images=imagem.convert("RGB"), return_tensors="pt")
        vet_img = _vetor(modelo.get_image_features(**entrada))
        vet_img = vet_img / vet_img.norm(dim=-1, keepdim=True)
        # Similaridade do cosseno entre a imagem e cada texto -> probabilidades
        logits = modelo.logit_scale.exp() * vet_img @ vet_texto.T
        probs = logits.softmax(dim=-1)[0]

    # Vários rótulos podem levar ao mesmo item (ex.: fone e estojo de fone): soma as chances.
    # O catálogo curado vem primeiro, então o item dele é o que fica.
    por_nome: dict[str, Resultado] = {}
    for (item, _), p in zip(rotulos, probs.tolist()):
        if item.nome in por_nome:
            por_nome[item.nome].confianca += p
        else:
            por_nome[item.nome] = Resultado(item, p)
    return sorted(por_nome.values(), key=lambda r: r.confianca, reverse=True)[:top_k]
