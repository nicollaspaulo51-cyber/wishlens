"""Gera o vocabulário grande do reconhecimento: data/vocabulario.csv + data/vocabulario_clip.npy.

Fontes (abertas):
- LVIS v1 (1.203 categorias de objetos, CC BY 4.0), via a lista do detectron2 (Apache-2.0);
- Open Multilingual Wordnet 2.0 / OpenWN-PT (CC BY-SA) para os nomes em português.

Regras de categoria:
- comida / bebidas: a categoria do LVIS descende de food / beverage no WordNet;
- animais: só animais domésticos (domestic_animal); animais selvagens ficam de fora (nada para adotar);
- produtos: pela hierarquia do WordNet (roupa, calçado, veículo, móvel...);
- o que sobrar: a categoria de produto do item curado mais parecido pelo CLIP (texto x texto).
Itens iguais aos do catálogo curado (src/categorias.py) são fundidos neles (mesmo nome).

Rodar de novo só se mudar o modelo, as regras ou o catálogo curado:
    pip install nltk && python scripts/gerar_vocabulario.py
"""

from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path

import nltk
import numpy as np
import requests
import torch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.categorias import FAIXA_PRECO, ITENS, tipo_da_categoria  # noqa: E402
from src.reconhecimento import MODELO, _vetor  # noqa: E402
from scripts.correcoes_vocabulario import aplicar as aplicar_correcoes  # noqa: E402

LVIS_URL = ("https://raw.githubusercontent.com/facebookresearch/detectron2/main/"
            "detectron2/data/datasets/lvis_v1_categories.py")

# Categoria pela hierarquia do WordNet (a 1ª que bater vence; ordem importa: sapato antes de roupa)
POR_WORDNET = [
    ("calçados", ["footwear.n.01", "footwear.n.02"]),
    ("vestuário", ["clothing.n.01", "jewelry.n.01", "bag.n.04", "headdress.n.01"]),
    ("veículos", ["vehicle.n.01", "craft.n.02"]),
    ("brinquedos e games", ["toy.n.01", "plaything.n.01", "game_equipment.n.01"]),
    ("esporte e lazer", ["sports_equipment.n.01", "sporting_goods.n.01", "musical_instrument.n.01"]),
    ("beleza", ["toiletry.n.01", "cosmetic.n.01", "makeup.n.01"]),
    ("livros e papelaria", ["publication.n.01", "writing_implement.n.01", "stationery.n.01", "paper.n.01"]),
    ("eletrônicos", ["electronic_equipment.n.01", "electronic_device.n.01", "computer.n.01",
                     "telephone.n.01", "camera.n.01"]),
    ("casa e decoração", ["furniture.n.01", "furnishing.n.02", "home_appliance.n.01", "kitchen_utensil.n.01",
                          "tableware.n.01", "bedclothes.n.01", "decoration.n.01", "lamp.n.01",
                          "bag.n.01", "container.n.01"]),
]
SIMILAR_AO_CURADO = 0.93  # acima disso, o rótulo do LVIS é o mesmo item do catálogo curado


def carregar_lvis() -> list[dict]:
    src = requests.get(LVIS_URL, timeout=60).text
    i = src.index("LVIS_CATEGORIES = [") + len("LVIS_CATEGORIES = ")
    return ast.literal_eval(src[i:src.index("]  # noqa", i) + 1])


def nome_pt(synset) -> str | None:
    lemas = [l for l in synset.lemma_names("por") if l.islower()] or synset.lemma_names("por")
    return lemas[0].replace("_", " ") if lemas else None


def descende(synset, *raizes: str) -> bool:
    alvos = {wn.synset(r) for r in raizes}
    return any(alvos & set(caminho) for caminho in synset.hypernym_paths())


def textos_para_vetores(modelo, processador, textos: list[str]) -> torch.Tensor:
    with torch.no_grad():
        partes = []
        for i in range(0, len(textos), 256):
            entrada = processador(text=textos[i:i + 256], return_tensors="pt", padding=True)
            partes.append(_vetor(modelo.get_text_features(**entrada)))
        v = torch.cat(partes)
    return v / v.norm(dim=-1, keepdim=True)


if __name__ == "__main__":
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-2.0", quiet=True)
    from nltk.corpus import wordnet as wn
    from transformers import CLIPModel, CLIPProcessor

    modelo = CLIPModel.from_pretrained(MODELO).eval()
    processador = CLIPProcessor.from_pretrained(MODELO)

    linhas = []
    for c in carregar_lvis():
        try:
            s = wn.synset(c["synset"])
        except nltk.corpus.reader.wordnet.WordNetError:  # poucos synsets do LVIS não existem no WordNet 3.0
            s = None
        rotulo = re.sub(r"\s+", " ", c["synonyms"][0].replace("_", " ")).strip()
        if re.search(r"\b(beer|wine|soda|juice)\b", rotulo):  # garrafa/lata de bebida: o WordNet chama de recipiente
            categoria = "bebidas"
        elif s is None:
            categoria = None
        elif descende(s, "animal.n.01"):
            if not descende(s, "domestic_animal.n.01"):
                continue
            categoria = "animais"
        elif descende(s, "beverage.n.01"):
            categoria = "bebidas"
        elif descende(s, "food.n.01", "food.n.02"):
            categoria = "comida"
        else:  # decidida pelo WordNet ou, se nada bater, pelo CLIP abaixo
            categoria = next((cat for cat, raizes in POR_WORDNET if descende(s, *raizes)), None)
        linhas.append({"rotulo_en": rotulo, "nome": (s and nome_pt(s)) or rotulo,
                       "categoria": categoria, "synset": c["synset"]})

    prompts = [f"a photo of {l['rotulo_en']}" for l in linhas]
    v_lvis = textos_para_vetores(modelo, processador, prompts)
    v_cur = textos_para_vetores(modelo, processador, [f"a photo of {i.rotulo_en}" for i in ITENS])

    sim = v_lvis @ v_cur.T
    sim_cur, idx_cur = sim.max(dim=1)
    so_produtos = sim.clone()
    # o vizinho do CLIP só escolhe entre categorias de produto (comida/animal só pelo WordNet)
    so_produtos[:, [k for k, i in enumerate(ITENS) if i.tipo != "comprar"]] = -1
    vizinho = so_produtos.argmax(dim=1).tolist()
    fundidos = 0
    for l, k, s, j in zip(linhas, vizinho, sim_cur.tolist(), idx_cur.tolist()):
        if s >= SIMILAR_AO_CURADO and l["categoria"] in (None, ITENS[j].categoria):
            # mesmo objeto do catálogo curado: herda nome e categoria (nunca contra o que o WordNet disse)
            l["nome"], l["categoria"] = ITENS[j].nome, ITENS[j].categoria
            fundidos += 1
        elif l["categoria"] is None:
            l["categoria"] = ITENS[k].categoria
        l["tipo"] = tipo_da_categoria(l["categoria"])
        assert l["categoria"] in FAIXA_PRECO

    linhas, manter = aplicar_correcoes(linhas)  # correções manuais (scripts/correcoes_vocabulario.py)
    v_lvis = v_lvis[manter]

    destino = RAIZ / "data"
    with open(destino / "vocabulario.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rotulo_en", "nome", "categoria", "tipo", "synset"], lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    np.save(destino / "vocabulario_clip.npy", v_lvis.numpy().astype(np.float16))
    print(f"{len(linhas)} rótulos ({fundidos} fundidos ao catálogo curado) -> data/vocabulario.csv")
