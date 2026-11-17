"""Baixa as fotos de treino do juiz do Open Images V7 (Google): imagens CC BY 2.0, anotações CC BY 4.0.

    python scripts/baixar_fotos_treino.py --saida /caminho/treino

Usa as caixas anotadas à mão dos conjuntos validation e test (~165 mil fotos, só ~100 MB de listas).
Cada foto escolhida tem o objeto PRINCIPAL de um grupo (caixa grande) e nenhum objeto de outro tema:
- os 5 temas do Mapa livre e "nenhum" (o que aparece andando e não vale);
- "brinquedo" (Toy, Teddy bear, Doll) e "desenho" (objetos dos temas marcados IsDepiction: desenho,
  pintura, estátua, impressão) são fotos falsas de verdade, além das geradas em src/falsas.py.
Fotos com rosto de pessoa ficam de fora (privacidade). As fotos são guardadas reduzidas (512 px) e o
fotos.csv leva autor, licença e link de cada uma (a licença CC BY exige o crédito).
"""

from __future__ import annotations

import argparse
import io
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

META = {
    "classes.csv": "https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions-boxable.csv",
    "validation-bbox.csv": "https://storage.googleapis.com/openimages/v5/validation-annotations-bbox.csv",
    "test-bbox.csv": "https://storage.googleapis.com/openimages/v5/test-annotations-bbox.csv",
    "validation-info.csv": "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv",
    "test-info.csv": "https://storage.googleapis.com/openimages/2018_04/test/test-images-with-rotation.csv",
}
FOTO = "https://open-images-dataset.s3.amazonaws.com/{subset}/{id}.jpg"

# grupo -> classes do Open Images
GRUPOS = {
    "carros": ["Car", "Van"],
    "plantas": ["Flower", "Houseplant", "Tree", "Plant"],
    "comidas": ["Fruit", "Banana", "Apple", "Orange", "Strawberry", "Bread", "Fast food", "Vegetable", "Baked goods"],
    "pets": ["Dog", "Cat", "Bird", "Horse", "Butterfly", "Lizard"],
    "pecas": ["Computer monitor", "Computer keyboard", "Computer mouse", "Laptop", "Headphones"],
    "nenhum": ["Footwear", "Chair", "Bench", "Building", "Street light", "Traffic sign", "Bottle", "Door",
               "Mobile phone", "Backpack", "Clock"],
    "brinquedo": ["Toy", "Teddy bear", "Doll"],
}
TEMAS = ("carros", "plantas", "comidas", "pets", "pecas")
QUANTAS = {**{t: 500 for t in TEMAS}, "nenhum": 700, "brinquedo": 300, "desenho": 400}
AREA_PRINCIPAL = 0.12  # a caixa do objeto ocupa pelo menos 12% da foto
AREA_OUTRO = 0.05      # outro tema/brinquedo maior que isto deixa a foto ambígua
LADO = 512


def baixar_meta(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, url in META.items():
        destino = pasta / nome
        if destino.exists():
            continue
        print("baixando", nome, flush=True)
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(str(destino) + ".parcial", "wb") as f:
                for pedaco in r.iter_content(1 << 20):
                    f.write(pedaco)
        Path(str(destino) + ".parcial").rename(destino)


def escolher(pasta: Path, rng: random.Random) -> pd.DataFrame:
    """Uma linha por foto escolhida: id, subset, grupo, classe, real (False para brinquedo/desenho)."""
    classes = pd.read_csv(pasta / "classes.csv", header=None, names=["mid", "nome"])
    mid_de = dict(zip(classes["nome"], classes["mid"]))
    faltam = [c for cs in GRUPOS.values() for c in cs if c not in mid_de]
    if faltam:
        print("classes que não existem no Open Images (ignoradas):", faltam, file=sys.stderr)
    grupo_de = {mid_de[c]: (g, c) for g, cs in GRUPOS.items() for c in cs if c in mid_de}
    rosto = mid_de["Human face"]

    caixas = []
    for subset in ("validation", "test"):
        cx = pd.read_csv(pasta / f"{subset}-bbox.csv",
                         usecols=["ImageID", "LabelName", "XMin", "XMax", "YMin", "YMax", "IsDepiction"])
        cx["subset"] = subset
        caixas.append(cx)
    cx = pd.concat(caixas, ignore_index=True)
    com_rosto = set(cx.loc[cx["LabelName"] == rosto, "ImageID"])
    cx = cx[cx["LabelName"].isin(grupo_de) & ~cx["ImageID"].isin(com_rosto)].copy()
    cx["area"] = (cx["XMax"] - cx["XMin"]) * (cx["YMax"] - cx["YMin"])
    cx["grupo"] = cx["LabelName"].map(lambda m: grupo_de[m][0])
    cx["classe"] = cx["LabelName"].map(lambda m: grupo_de[m][1])
    cx["desenho"] = cx["IsDepiction"].eq(1)

    escolhidas = []
    for (img, subset), d in cx.groupby(["ImageID", "subset"]):
        principal = d.loc[d["area"].idxmax()]
        if principal["area"] < AREA_PRINCIPAL:
            continue
        g = principal["grupo"]
        # temas (ou brinquedo) além do principal deixam a foto ambígua
        outros = d[(d["grupo"] != g) & (d["grupo"] != "nenhum") & (d["area"] >= AREA_OUTRO)]
        if not outros.empty:
            continue
        if g == "nenhum" and (d["grupo"] != "nenhum").any():
            continue
        if bool(principal["desenho"]):
            if g not in TEMAS:
                continue
            g = "desenho"
        elif d.loc[d["grupo"] == principal["grupo"], "desenho"].any():
            continue  # misturou objeto de verdade com desenho: fora
        escolhidas.append({"id": img, "subset": subset, "grupo": g, "classe": principal["classe"],
                           "tema": principal["grupo"] if principal["grupo"] in TEMAS else "nenhum",
                           "real": g not in ("brinquedo", "desenho")})
    todas = pd.DataFrame(escolhidas)

    # Sorteio equilibrado entre as classes de cada grupo (senão "Car" e "Tree" engoliriam o resto)
    saida = []
    for g, n in QUANTAS.items():
        d = todas[todas["grupo"] == g]
        por_classe = {c: list(x["id"]) for c, x in d.groupby("classe")}
        for ids in por_classe.values():
            rng.shuffle(ids)
        pegos: list[str] = []
        while len(pegos) < n and any(por_classe.values()):
            for c in list(por_classe):
                if por_classe[c] and len(pegos) < n:
                    pegos.append(por_classe[c].pop())
        saida.append(d[d["id"].isin(pegos)])
        print(f"{g}: {len(pegos)} fotos ({len(d)} disponíveis)", flush=True)
    return pd.concat(saida, ignore_index=True)


def baixar_foto(linha: dict, rotacao: float, destino: Path) -> bool:
    if destino.exists():
        return True
    try:
        r = requests.get(FOTO.format(subset=linha["subset"], id=linha["id"]), timeout=60)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if rotacao:
            img = img.rotate(-rotacao, expand=True)
        img.thumbnail((LADO, LADO))
        img.save(destino, "JPEG", quality=90)
        return True
    except Exception as erro:  # foto que sumiu do armazém: segue sem ela
        print("falhou", linha["id"], type(erro).__name__, file=sys.stderr)
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True, type=Path)
    ap.add_argument("--semente", type=int, default=42)
    a = ap.parse_args()
    meta, fotos = a.saida / "meta", a.saida / "fotos"
    baixar_meta(meta)
    fotos.mkdir(parents=True, exist_ok=True)
    lista = escolher(meta, random.Random(a.semente))

    info = pd.concat([pd.read_csv(meta / f"{s}-info.csv",
                                  usecols=["ImageID", "OriginalURL", "License", "Author", "Rotation"])
                      for s in ("validation", "test")]).drop_duplicates("ImageID").set_index("ImageID")
    lista = lista.join(info, on="id")
    with ThreadPoolExecutor(16) as fila:
        ok = list(fila.map(lambda l: baixar_foto(l, float(l["Rotation"] or 0) if pd.notna(l["Rotation"]) else 0.0,
                                                 fotos / f"{l['id']}.jpg"), lista.to_dict("records")))
    lista = lista[ok].rename(columns={"OriginalURL": "url", "License": "licenca", "Author": "autor"})
    lista.drop(columns=["Rotation"]).to_csv(a.saida / "fotos.csv", index=False)
    print(f"pronto: {len(lista)} fotos em {fotos}")


if __name__ == "__main__":
    main()
