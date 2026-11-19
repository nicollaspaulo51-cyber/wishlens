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


def test_juntar_ia_so_derruba_com_o_clip_desconfiado():
    s = _sonda()
    s = tj.Sonda(s.w_tema, s.b_tema, s.w_falsa, s.b_falsa, 1, 1, 0.75, "t", limiar_ia=0.6, tema_da_ia=False)
    assert tj.juntar("pets", False, "carros", True, 0.1, s) == ("carros", True)
    assert tj.juntar("pets", False, "carros", True, 0.7, s) == ("carros", False)
    assert tj.juntar("pets", True, "carros", False, 0.9, s) == ("carros", False)  # o CLIP sozinho já barra


def test_nome_diz_qual_objeto_e():
    assert tj.classe_do_nome("pecas", "teclado mecânico") == "Computer keyboard"
    assert tj.classe_do_nome("pecas", "Teclados") == "Computer keyboard"
    assert tj.classe_do_nome("pecas", "Notebook Dell") == "Laptop"
    assert tj.classe_do_nome("pets", "cachorro vira-lata caramelo") == "Dog"
    assert tj.classe_do_nome("comidas", "macarrão") is None      # "maca" não é "maçã"
    assert tj.classe_do_nome("pecas", "placa de vídeo") is None  # peça sem classe própria: o nome da IA vale
    assert tj.classe_do_nome("carros", "Volkswagen Gol") is None  # modelo de carro nunca é trocado


def _com_objetos(tema, classes, conf):
    """Sonda de brinquedo: o vetor e0 aponta para classes[0] com a força `conf`."""
    w = np.zeros((len(classes), 512), dtype=np.float32)
    w[0, 0] = conf
    base = _sonda()
    return tj.Sonda(base.w_tema, base.b_tema, base.w_falsa, base.b_falsa, 1, 1, 0.75, "t",
                    objetos={tema: (w, np.zeros(len(classes), dtype=np.float32), tuple(classes))})


def test_achado_so_troca_quando_a_ia_diz_outro_objeto_e_o_classificador_tem_certeza():
    classes = ["Computer keyboard", "Computer monitor", "Computer mouse"]
    forte = tj.objeto(E0, "pecas", _com_objetos("pecas", classes, 12.0))
    assert forte["classe"] == "Computer keyboard" and forte["nome"] == "teclado" and forte["conf"] > 0.9
    assert tj.objeto(E0, "plantas", _com_objetos("pecas", classes, 12.0)) is None  # tema sem classificador
    assert tj.escolher_achado("mouse", "pecas", forte) == "teclado"                # a IA disse outro objeto
    assert tj.escolher_achado("teclado mecânico", "pecas", forte) == "teclado mecânico"  # concorda: fica o detalhe
    assert tj.escolher_achado("Logitech MX Keys", "pecas", forte) == "Logitech MX Keys"  # nada a contradizer
    assert tj.escolher_achado("", "pecas", forte) == "teclado"
    fraco = tj.objeto(E0, "pecas", _com_objetos("pecas", classes, 0.1))
    assert fraco["conf"] < tj.LIMIAR_OBJETO and tj.escolher_achado("mouse", "pecas", fraco) == "mouse"


def test_treina_objetos_com_duas_classes_e_guarda(tmp_path):
    rng = np.random.default_rng(0)
    linhas = []
    for i in range(80):
        classe = "Car" if i % 2 else "Van"
        v = rng.normal(0, 0.05, 512).astype(np.float32)
        v[0 if classe == "Car" else 1] += 1.0
        linhas.append({"tema": "carros", "real": True, "classe": classe, "vetor": v,
                       "parte": "treino" if i < 56 else "validacao" if i < 68 else "teste"})
    saida, rel = tj.treinar_objetos(pd.DataFrame(linhas))
    w, b, classes = saida["carros"]
    assert w.shape == (2, 512) and classes == ("Car", "Van") and rel["carros"]["acerto_validacao"] > 0.9
    base = _sonda()
    s = tj.Sonda(base.w_tema, base.b_tema, base.w_falsa, base.b_falsa, 1, 1, 0.75, "t", objetos=saida)
    caminho = tmp_path / "j.npz"
    tj.salvar(s, caminho)
    lida = tj.carregar(caminho)
    assert tj.objeto(np.eye(512, dtype=np.float32)[0], "carros", lida)["classe"] == "Car"
    assert tj.objeto(np.eye(512, dtype=np.float32)[1], "carros", lida)["classe"] == "Van"
