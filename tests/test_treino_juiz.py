"""Camada treinada do juiz (src/treino_juiz.py) e fotos falsas geradas (src/falsas.py), sem torch nem rede."""

import random

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from src import falsas, treino_juiz as tj


def _sonda(tema=0, falsa=0.0, alfa=1.0, beta=1.0, limiar=0.6):
    """Sonda de brinquedo: o vetor e0 puxa para ORDEM[tema]; w_falsa·v = falsa."""
    w = np.zeros((6, 512), dtype=np.float32)
    w[tema, 0] = 10
    wf = np.zeros(512, dtype=np.float32)
    wf[0] = falsa
    return tj.Sonda(w, np.zeros(6, dtype=np.float32), wf, 0.0, alfa, beta, limiar, "teste")


E0 = np.eye(512, dtype=np.float32)[0]
ZS = {"carros": 0.7, "plantas": 0.05, "comidas": 0.05, "pets": 0.05, "pecas": 0.05, "nenhum": 0.05,
      "outro:paisagens": 0.02, "tela": 0.03}


def test_zero_shot_conta_outras_abas_como_nenhum():
    v = tj.zs_temas(ZS)
    assert abs(v.sum() - 1) < 1e-6 and v[tj.ORDEM.index("carros")] > 0.7
    assert v[-1] > v[1]  # nenhum (0.05 + 0.02) > plantas (0.05)


def test_sonda_decide_tema_e_foto_real():
    chances, tema, real, conf = tj.aplicar_sonda(E0, ZS, _sonda(tema=tj.ORDEM.index("comidas")))
    assert tema == "comidas" and real and conf > 0.9
    assert abs(sum(chances.values()) - 1) < 1e-5 and set(chances) == {*tj.ORDEM, "tela"}
    # sem peso na sonda (alfa 0), vale o zero-shot
    assert tj.aplicar_sonda(E0, ZS, _sonda(tema=2, alfa=0.0))[1] == "carros"
    # nenhum ganhou: tema None
    assert tj.aplicar_sonda(E0, ZS, _sonda(tema=5))[1] is None
    # sonda de falsa forte: não é real
    assert tj.aplicar_sonda(E0, ZS, _sonda(falsa=8.0))[2] is False


def test_salva_e_carrega_e_recusa_outra_ordem(tmp_path):
    s = _sonda(tema=1, falsa=2.0, alfa=0.6, beta=0.4, limiar=0.7)
    caminho = tmp_path / "j.npz"
    tj.salvar(s, caminho)
    lida = tj.carregar(caminho)
    assert lida is not None and lida.alfa == np.float32(0.6) and lida.versao == "teste"
    assert tj.aplicar_sonda(E0, ZS, lida)[1] == tj.aplicar_sonda(E0, ZS, s)[1]
    assert tj.carregar(tmp_path / "nao_existe.npz") is None
    d = dict(np.load(caminho))
    d["ordem"] = np.array(["carros", "passaros"])
    np.savez(tmp_path / "velho.npz", **d)
    assert tj.carregar(tmp_path / "velho.npz") is None  # treinada para outros temas: juiz usa o zero-shot


def test_partes_pela_foto_original():
    ids = [f"foto{i}" for i in range(2000)]
    partes = pd.Series([tj.parte(i) for i in ids]).value_counts(normalize=True)
    assert 0.65 < partes["treino"] < 0.75 and 0.1 < partes["teste"] < 0.2
    assert tj.parte("abc") == tj.parte("abc")  # as versões de uma foto caem juntas


def _foto():
    img = Image.new("RGB", (400, 300), (60, 140, 60))
    ImageDraw.Draw(img).ellipse((120, 80, 280, 220), fill=(220, 40, 40))
    return img


def test_falsas_e_celular_tem_tamanho_certo_e_repetem_com_a_mesma_semente():
    for gerar in (falsas.na_tela, falsas.impressa):
        img = gerar(_foto(), random.Random(1))
        assert max(img.size) <= falsas.LADO and img.mode == "RGB"
        assert np.array_equal(np.asarray(img), np.asarray(gerar(_foto(), random.Random(1))))
    cel = falsas.como_celular(_foto(), random.Random(2))
    assert cel.size[0] <= 400 and cel.mode == "RGB"
    assert np.array_equal(np.asarray(tj.gerar(_foto(), "tela", "x")), np.asarray(tj.gerar(_foto(), "tela", "x")))


def test_acerto_do_jogo():
    df = pd.DataFrame({"tema": ["carros", "nenhum", "pets", "carros"], "real": [True, True, False, True]})
    certo = tj.aceita_certo(df, ["carros", "plantas", "pets", "plantas"], [True, True, True, True])
    # carro certo; nenhum aceito (erro); falsa aceita (erro); tema errado (erro)
    assert certo.tolist() == [True, False, False, False]
    r = tj.resumo(df, ["carros", None, None, "carros"], [True, True, False, True])
    assert r["acerto_geral"] == 1.0 and r["falsa_aceita"] == 0.0
