"""Treina a camada do juiz em cima do CLIP e mede o acerto (CRISP-DM: modelagem e avaliação).

    python scripts/treinar_juiz.py --dados /caminho/treino               # vetores + treino + medição
    python scripts/treinar_juiz.py --dados /caminho/treino --com-ia 500  # + o Qwen numa amostra (placa de vídeo)

Antes: scripts/baixar_fotos_treino.py. Saídas: modelos/juiz_clip.npz (vai para o juiz) e
modelos/juiz_clip_metricas.json (números para o notebook 06). A IA é chamada com folga entre as fotos para
não deixar a placa no máximo (a ponte da placa pausa a IA se ela passar de 85% por um minuto).
"""

from __future__ import annotations

import argparse
from dataclasses import replace
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


def _juncao(d: pd.DataFrame, sonda) -> tuple[list, list]:
    """A regra nova do servidor (tj.juntar) + o veto de tema do CLIP (jogo.veto_clip), linha a linha."""
    clip = tj.decisoes(d, sonda)
    temas, reais = [], []
    for (_, r), ct, cr, p in zip(d.iterrows(), clip["tema"], clip["real"], clip["chances"]):
        ia_tema = r.ia_tema if isinstance(r.ia_tema, str) and r.ia_tema != "nenhum" else None
        ct = ct if isinstance(ct, str) else None  # o pandas 3 guarda o None da coluna de texto como NaN
        tema, real = tj.juntar(ia_tema, bool(r.ia_real), ct, cr, p["tela"], sonda)
        if tema and real and jogo.veto_clip(tema, "ia+clip", ct, p.get(tema, 0.0), p["tela"], jogo.posicao(p, tema), cr):
            real = False
        temas.append(tema)
        reais.append(real)
    return temas, reais


def calibrar_juncao(df: pd.DataFrame, ia: pd.DataFrame, sonda):
    """Escolhe na validação quando a IA pode derrubar o "é real" e de quem vem o tema."""
    from dataclasses import replace

    d = df[df["parte"] == "validacao"].merge(ia, on=["id", "variante"])
    opcoes = []
    for limiar_ia in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.01):
        for tema_da_ia in (True, False):
            s = replace(sonda, limiar_ia=limiar_ia, tema_da_ia=tema_da_ia)
            r = tj.resumo(d, *_juncao(d, s))
            opcoes.append((r["foto_real_recusada"] <= 0.05, r["acerto_geral"], -r["foto_real_recusada"], s, r))
    melhor = max(opcoes, key=lambda o: o[:3])
    print("junção escolhida:", melhor[3].limiar_ia, "tema da IA" if melhor[3].tema_da_ia else "tema do CLIP", melhor[4], flush=True)
    return melhor[3]


def regras_com_ia(df: pd.DataFrame, ia: pd.DataFrame, sonda) -> dict:
    """Regra antiga do servidor (a IA decide no Mapa livre e o CLIP pode vetar) x a junção nova."""
    d = df.merge(ia, on=["id", "variante"])
    res = {"ia+clip_juncao_nova": tj.resumo(d, *_juncao(d, sonda))}
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


def medir_objetos(teste: pd.DataFrame, sonda) -> dict:
    """Qual OBJETO é, dentro do tema (teclado x mouse x monitor...), nas fotos reais do teste: CLIP sem treino x treinado."""
    import torch

    from src.reconhecimento import _carregar, _vetores_captura, achado_do_tema

    modelo, _ = _carregar()
    vet_texto, frases = _vetores_captura("livre")
    escala = float(modelo.logit_scale.exp())
    res = {}
    for tema, classes in tj.OBJETOS.items():
        d = teste[(teste["tema"] == tema) & teste["real"] & teste["classe"].isin(classes)]
        if d.empty or tema not in sonda.objetos:
            continue
        verdade = d["classe"].to_numpy()
        obj = [tj.objeto(v, tema, sonda) for v in d["vetor"]]
        prev = np.array([o["classe"] for o in obj])
        confiante = np.array([o["conf"] >= tj.LIMIAR_OBJETO for o in obj])
        r = {"n": int(len(d)), "treinado": round(float((prev == verdade).mean()), 3),
             "cobertura_confiante": round(float(confiante.mean()), 3),
             "treinado_quando_confiante": round(float((prev == verdade)[confiante].mean()), 3) if confiante.any() else None,
             "confusao": pd.crosstab(pd.Series(verdade, name="era"), pd.Series(prev, name="disse")).to_dict()}
        if all(palavras for _, palavras in classes.values()):  # dá para ligar o nome do zero-shot a uma classe
            with torch.no_grad():
                chances = (escala * torch.tensor(np.stack(d["vetor"].to_numpy())) @ vet_texto.T).softmax(dim=-1).tolist()
            zs = np.array([tj.classe_do_nome(tema, achado_do_tema(frases, p, tema)) for p in chances], dtype=object)
            r["zero_shot"] = round(float((zs == verdade).mean()), 3)
        res[tema] = r
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True, type=Path)
    ap.add_argument("--com-ia", type=int, default=0)
    ap.add_argument("--turma", type=Path, default=None, help="pasta do volume treino (rotulos.csv e fotos da turma)")
    a = ap.parse_args()
    random.seed(0)
    np.random.seed(0)

    df = tj.extrair(a.dados, a.dados / "vetores.pkl")
    print(f"{len(df)} exemplos ({df['id'].nunique()} fotos)", flush=True)
    sonda, info = tj.treinar(df, versao=f"{date.today()} {df['id'].nunique()} fotos Open Images")
    # fotos da turma com o modelo marcado no app (pasta do volume "treino", se existir): ensinam Gol x Onix etc.
    if a.turma and (a.turma / "rotulos.csv").exists():
        turma = tj.carregar_turma(a.turma, a.dados / "turma.pkl")
        modelos, rel_modelos = tj.treinar_modelos(turma)
        sonda = replace(sonda, modelos=modelos)
        info["modelos"] = rel_modelos
        print("modelos da turma:", json.dumps(rel_modelos, ensure_ascii=False), flush=True)
    ia = com_ia(df, a.dados, a.com_ia, a.dados / "respostas_ia.csv") if a.com_ia else None
    if ia is not None:
        sonda = calibrar_juncao(df, ia, sonda)
        info |= {"limiar_ia": sonda.limiar_ia, "tema_da_ia": sonda.tema_da_ia}
    tj.salvar(sonda)
    teste = df[df["parte"] == "teste"]
    metricas = {"treino": info, "fotos": int(df["id"].nunique()), "exemplos": int(len(df)),
                "por_parte": df.groupby("parte").size().to_dict(),
                "teste": {"clip_zero_shot": tj.resumo(teste, *tj.decisoes(teste, None)[["tema", "real"]].T.to_numpy()),
                          "clip_treinado": tj.resumo(teste, *tj.decisoes(teste, sonda)[["tema", "real"]].T.to_numpy())}}
    metricas["objetos_teste"] = medir_objetos(teste[teste["variante"].isin(["original", "celular"])], sonda)
    # previsões do teste, linha a linha, para o notebook 06 (matriz de confusão, erros com miniatura)
    zs, tr = tj.decisoes(teste, None), tj.decisoes(teste, sonda)
    prev = teste[["id", "grupo", "classe", "tema", "variante", "real"]].assign(
        zs_tema=zs["tema"].fillna("nenhum"), zs_real=zs["real"], tr_tema=tr["tema"].fillna("nenhum"), tr_real=tr["real"],
        tr_falsa=[c["tela"] for c in tr["chances"]])
    if ia is not None:
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
