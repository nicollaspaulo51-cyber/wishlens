"""Reconhecimento de imagens com CLIP (modelo aberto) por classificação zero-shot.

O CLIP compara a imagem com frases de texto ("a photo of a dog", "a photo of a pizza"...)
e devolve qual frase combina mais. Não é preciso treinar nada.

Vocabulário: o catálogo curado (src/categorias.py, com prioridade e frases de marcas) + ~950 objetos do LVIS
em data/vocabulario.csv, com vetores de texto já calculados em data/vocabulario_clip.npy
(gerados por scripts/gerar_vocabulario.py).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from PIL import Image

from src.categorias import ITENS, Item, faixa_preco

MODELO = "openai/clip-vit-base-patch32"  # pesos abertos (licença MIT)
DADOS = Path(__file__).resolve().parents[1] / "data"


# Frases extras para itens que o CLIP confunde (o catálogo tem um rótulo por item)
ROTULOS_EXTRAS = {
    "fone de ouvido": ["wireless earbuds", "a white wireless earbuds charging case"],
    # latas e garrafas: sem isso, toda bebida em lata vira "suco"
    "energético": ["a tall black energy drink can"],
    "refrigerante": ["a plastic bottle of soda"],
    "cerveja": ["a bottle of beer", "a glass of beer"],
    "vinho": ["a glass of red wine"],
    "gato": ["a kitten"],
    "cachorro": ["a puppy"],
}

# Marcas que o CLIP costuma reconhecer pelo logo/formato: item -> [(marca, modelo, frase)].
# Quando a frase de uma marca leva a maior parte da chance do item, o resultado sai com a marca.
MARCAS: dict[str, list[tuple[str, str, str]]] = {
    "tênis": [("Nike", "", "Nike sneakers with the swoosh logo"), ("Adidas", "", "Adidas sneakers with three stripes"),
              ("Converse", "All Star", "Converse All Star sneakers"), ("Vans", "", "Vans skate sneakers"),
              ("Puma", "", "Puma sneakers"), ("New Balance", "", "New Balance sneakers with the N logo")],
    "sandália/chinelo": [("Havaianas", "", "Havaianas flip-flops")],
    "camiseta": [("Nike", "", "a Nike t-shirt"), ("Adidas", "", "an Adidas t-shirt")],
    "boné/chapéu": [("New Era", "", "a New Era baseball cap")],
    "celular": [("Apple", "iPhone", "an Apple iPhone"), ("Samsung", "Galaxy", "a Samsung Galaxy smartphone"),
                ("Motorola", "", "a Motorola smartphone"), ("Xiaomi", "", "a Xiaomi smartphone")],
    "notebook": [("Apple", "MacBook", "an Apple MacBook laptop"), ("Dell", "", "a Dell laptop"),
                 ("Lenovo", "", "a Lenovo laptop")],
    "tablet": [("Apple", "iPad", "an Apple iPad")],
    "smartwatch": [("Apple", "Apple Watch", "an Apple Watch")],
    "fone de ouvido": [("Apple", "AirPods", "Apple AirPods"), ("JBL", "", "JBL headphones")],
    "caixa de som": [("JBL", "", "a JBL bluetooth speaker")],
    "mouse": [("Logitech", "", "a Logitech computer mouse")],
    "teclado": [("Logitech", "", "a Logitech keyboard")],
    "videogame": [("Sony", "PlayStation 5", "a Sony PlayStation 5 console"),
                  ("Microsoft", "Xbox", "a Microsoft Xbox console"),
                  ("Nintendo", "Switch", "a Nintendo Switch console")],
    "controle de videogame": [("Sony", "DualSense", "a PlayStation DualSense controller"),
                              ("Microsoft", "", "an Xbox controller")],
    "energético": [("Monster", "", "a Monster energy drink can"), ("Red Bull", "", "a Red Bull energy drink can")],
    "refrigerante": [("Coca-Cola", "", "a Coca-Cola can"), ("Guaraná Antarctica", "", "a Guarana Antarctica soda can"),
                     ("Pepsi", "", "a Pepsi can"), ("Fanta", "", "a Fanta orange soda can"),
                     ("Sprite", "", "a Sprite can")],
    "cerveja": [("Heineken", "", "a green Heineken beer"), ("Brahma", "", "a Brahma beer can"),
                ("Skol", "", "a Skol beer can"), ("Budweiser", "", "a Budweiser beer"),
                ("Corona", "", "a Corona beer bottle")],
    "chocolate": [("Lacta", "", "a Lacta chocolate bar"), ("Nestlé", "KitKat", "a KitKat chocolate bar")],
}

# Várias frases por rótulo do catálogo; o vetor do rótulo é a média (prompt ensembling)
MODELOS_FRASE = ["a photo of {}", "a close-up photo of {}", "a product photo of {}"]

# O catálogo curado tem as coisas que as pessoas mais fotografam: pesa mais que os ~950 do LVIS,
# senão "aeronave" ou "caminhão" ganham de "carro" só por serem muitos rótulos parecidos.
PESO_CATALOGO = 1.7
MARCA_MINIMA = 0.5  # a marca entra se as frases dela somam ao menos metade da chance do item

# (item, frase, (marca, modelo)) do catálogo curado
_ROTULOS: list[tuple[Item, str, tuple[str, str]]] = (
    [(i, i.rotulo_en, ("", "")) for i in ITENS]
    + [(i, r, ("", "")) for i in ITENS for r in ROTULOS_EXTRAS.get(i.nome, [])]
    + [(i, frase, (marca, modelo)) for i in ITENS for marca, modelo, frase in MARCAS.get(i.nome, [])]
)


def _vocabulario() -> list[tuple[Item, str, tuple[str, str]]]:
    """Objetos do LVIS (data/vocabulario.csv); vazio se o arquivo não existir."""
    arquivo = DADOS / "vocabulario.csv"
    if not arquivo.exists():
        return []
    with open(arquivo, encoding="utf-8") as f:
        return [(Item(l["rotulo_en"], l["nome"], l["categoria"], l["tipo"]), l["rotulo_en"], ("", ""))
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
        return faixa_preco(self.item)


@lru_cache(maxsize=1)
def _carregar():
    import torch
    from transformers import CLIPModel, CLIPProcessor

    modelo = CLIPModel.from_pretrained(MODELO)
    processador = CLIPProcessor.from_pretrained(MODELO)
    modelo.eval()

    # Os textos são sempre os mesmos: calcula os vetores do catálogo curado uma única vez,
    # cada rótulo como a média das frases de MODELOS_FRASE
    textos = [m.format(r) for _, r, _ in _ROTULOS for m in MODELOS_FRASE]
    with torch.no_grad():
        entrada = processador(text=textos, return_tensors="pt", padding=True)
        vet = _vetor(modelo.get_text_features(**entrada))
        vet = vet / vet.norm(dim=-1, keepdim=True)
        vet_texto = vet.reshape(len(_ROTULOS), len(MODELOS_FRASE), -1).mean(dim=1)
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

    return agrupar(rotulos, probs.tolist(), n_curados=len(_ROTULOS), top_k=top_k)


def agrupar(rotulos: list[tuple[Item, str, tuple[str, str]]], probs: list[float],
            n_curados: int, top_k: int = 3) -> list[Resultado]:
    """Probabilidade por rótulo -> top_k itens (sem torch, para poder testar).

    - os n_curados primeiros rótulos (catálogo) pesam PESO_CATALOGO vezes mais; depois renormaliza;
    - vários rótulos do mesmo item somam (ex.: fone e estojo de fone); a chave inclui a categoria,
      porque "taco" (comida) e "taco" (sinuca) são coisas diferentes; o item do catálogo vem primeiro e fica;
    - das frases de marca, só a marca mais forte entra na soma do item;
    - se essa marca tem ao menos MARCA_MINIMA da chance do item, ele sai com a marca.
    """
    pesos = [p * (PESO_CATALOGO if k < n_curados else 1.0) for k, p in enumerate(probs)]
    por_item: dict[tuple[str, str], Resultado] = {}
    por_marca: dict[tuple[str, str], dict[tuple[str, str], float]] = {}
    for (item, _, marca), p in zip(rotulos, pesos):
        chave = (item.nome, item.categoria)
        if chave not in por_item:
            por_item[chave] = Resultado(item, 0.0)
        if marca[0]:  # frases de marca: guardadas à parte (ver abaixo)
            m = por_marca.setdefault(chave, {})
            m[marca] = m.get(marca, 0.0) + p
        else:
            por_item[chave].confianca += p
    # Do item, só conta a marca mais forte: somar todas daria vantagem a quem tem mais marcas na lista
    # (refrigerante com 5 latas de marca ganharia de energético com 2 só por ter mais frases).
    for chave, marcas in por_marca.items():
        (marca, modelo), p = max(marcas.items(), key=lambda kv: kv[1])
        r = por_item[chave]
        r.confianca += p
        if p >= MARCA_MINIMA * r.confianca:
            r.item = replace(r.item, marca=marca, modelo=modelo)
    total = sum(r.confianca for r in por_item.values()) or 1.0
    for r in por_item.values():
        r.confianca /= total
    return sorted(por_item.values(), key=lambda r: r.confianca, reverse=True)[:top_k]
