"""Treina a camada do juiz em cima do CLIP e mede o acerto (CRISP-DM: modelagem e avaliação).

    python scripts/treinar_juiz.py --dados /caminho/treino               # vetores + treino + medição
    python scripts/treinar_juiz.py --dados /caminho/treino --com-ia 500  # + o Qwen numa amostra (placa de vídeo)

Antes: scripts/baixar_fotos_treino.py. Saídas: modelos/juiz_clip.npz (vai para o juiz) e
modelos/juiz_clip_metricas.json (números para o notebook 06). A IA é chamada com folga entre as fotos para
não deixar a placa no máximo (a ponte da placa pausa a IA se ela passar de 85% por um minuto).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import jogo, treino_juiz as tj  # noqa: E402

METRICAS = tj.CAMINHO.with_name("juiz_clip_metricas.json")
FOLGA_IA = 4.0  # segundos entre fotos na IA: ~5 s de placa + 4 s parada, média bem abaixo de 85%


def com_ia(df: pd.DataFrame, pasta: Path, n: int, cache: Path) -> pd.DataFrame:
    """Resposta do Qwen (tema, foto_real) para uma amostra de validação + teste, guardada em cache."""
    import io

    from PIL import Image

    from src import visao

    url, modelo = os.environ.get("VISAO_URL"), os.environ.get("VISAO_MODELO") or visao.MODELO_PADRAO
    if not url:
        raise SystemExit("VISAO_URL não definida: rode dentro do contêiner do juiz")
    feitas = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["id", "variante", "ia_tema", "ia_real"])
    pronto = set(zip(feitas["id"], feitas["variante"]))
    amostra = df[df["parte"] != "treino"]
    amostra = amostra.sample(min(n, len(amostra)), random_state=7)
    novas = []
    for k, r in enumerate(amostra.itertuples(index=False)):
        if (r.id, r.variante) in pronto:
            continue
        img = tj.gerar(Image.open(pasta / "fotos" / f"{r.id}.jpg"), r.variante, r.id)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        try:
            c = visao.identificar_captura(buf.getvalue(), url, modelo)
            novas.append({"id": r.id, "variante": r.variante, "ia_tema": c.tema or "nenhum", "ia_real": bool(c.foto_real)})
        except visao.ErroVisao as erro:
            print("IA falhou:", erro, flush=True)
            if "pausada" in str(erro):
                time.sleep(60)
        if len(novas) % 25 == 0 and novas:
            pd.concat([feitas, pd.DataFrame(novas)]).to_csv(cache, index=False)
            print(f"IA: {k + 1}/{len(amostra)}", flush=True)
        time.sleep(FOLGA_IA)
    feitas = pd.concat([feitas, pd.DataFrame(novas)], ignore_index=True)
    feitas.to_csv(cache, index=False)
    return feitas


def regras_com_ia(df: pd.DataFrame, ia: pd.DataFrame, sonda) -> dict:
    """Mesma regra do servidor: a IA decide no Mapa livre e o CLIP pode vetar (jogo.veto_clip)."""
    d = df.merge(ia, on=["id", "variante"])
    res = {}
    for nome, s in (("zero_shot", None), ("treinado", sonda)):
        clip = tj.decisoes(d, s)
        probs = clip["chances"] if s is not None else d["probs"]
        temas, reais = [], []
        for (_, r), ct, cr, p in zip(d.iterrows(), clip["tema"], clip["real"], probs):
            tema = None if r.ia_tema == "nenhum" else r.ia_tema
            real = bool(r.ia_real)
            if tema and real and jogo.veto_clip(tema, "ia+clip", ct, p.get(tema, 0.0), p.get("tela", 0.0),
                                                jogo.posicao(p, tema), cr):
                real = False
            temas.append(tema)
            reais.append(real)
        res[f"ia+clip_{nome}"] = tj.resumo(d, temas, reais)
        res[f"clip_{nome}_sozinho"] = tj.resumo(d, clip["tema"], clip["real"])
    res["ia_sozinha"] = tj.resumo(d, [None if t == "nenhum" else t for t in d["ia_tema"]], d["ia_real"])
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True, type=Path)
    ap.add_argument("--com-ia", type=int, default=0)
    a = ap.parse_args()
    random.seed(0)
    np.random.seed(0)

    df = tj.extrair(a.dados, a.dados / "vetores.pkl")
    print(f"{len(df)} exemplos ({df['id'].nunique()} fotos)", flush=True)
    sonda, info = tj.treinar(df, versao=f"{date.today()} {df['id'].nunique()} fotos Open Images")
    tj.salvar(sonda)
    teste = df[df["parte"] == "teste"]
    metricas = {"treino": info, "fotos": int(df["id"].nunique()), "exemplos": int(len(df)),
                "por_parte": df.groupby("parte").size().to_dict(),
                "teste": {"clip_zero_shot": tj.resumo(teste, *tj.decisoes(teste, None)[["tema", "real"]].T.to_numpy()),
                          "clip_treinado": tj.resumo(teste, *tj.decisoes(teste, sonda)[["tema", "real"]].T.to_numpy())}}
    # previsões do teste, linha a linha, para o notebook 06 (matriz de confusão, erros com miniatura)
    zs, tr = tj.decisoes(teste, None), tj.decisoes(teste, sonda)
    prev = teste[["id", "grupo", "classe", "tema", "variante", "real"]].assign(
        zs_tema=zs["tema"].fillna("nenhum"), zs_real=zs["real"], tr_tema=tr["tema"].fillna("nenhum"), tr_real=tr["real"],
        tr_falsa=[c["tela"] for c in tr["chances"]])
    if a.com_ia:
        ia = com_ia(df, a.dados, a.com_ia, a.dados / "respostas_ia.csv")
        metricas["com_ia"] = {p: regras_com_ia(df[df["parte"] == p], ia, sonda) for p in ("validacao", "teste")}
        prev = prev.merge(ia, on=["id", "variante"], how="left")
    fotos = pd.read_csv(a.dados / "fotos.csv")[["id", "autor", "licenca", "url"]]
    prev.merge(fotos, on="id", how="left").to_csv(a.dados / "previsoes_teste.csv", index=False)
    METRICAS.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metricas["teste"], indent=2, ensure_ascii=False))
    if "com_ia" in metricas:
        print(json.dumps(metricas["com_ia"]["teste"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
