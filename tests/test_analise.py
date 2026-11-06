"""Testes de clustering, exportação anonimizada e do fallback de armazenamento (sem internet)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.categorias import CATEGORIAS
from src.clustering import agrupar, escolher_k, matriz_perfis, melhor_k, nomear_cluster, perfil_do_usuario
from src.exemplo import gerar_exemplos
from src.exportar import anonimizar


def _df():
    return pd.DataFrame(gerar_exemplos())


def test_matriz_perfis_soma_um():
    X = matriz_perfis(_df())
    assert list(X.columns) == CATEGORIAS
    assert len(X) == 5
    assert ((X.sum(axis=1) - 1).abs() < 1e-9).all()


def test_escolha_de_k_e_rotulos_estaveis():
    X = matriz_perfis(_df())
    tabela = escolher_k(X)
    assert set(tabela.columns) == {"k", "inercia", "silhueta"}
    assert tabela["inercia"].is_monotonic_decreasing
    k = melhor_k(X)
    assert 2 <= k < len(X)
    r1, centros = agrupar(X, k)
    r2, _ = agrupar(X, k)
    assert (r1["cluster"] == r2["cluster"]).all()          # mesma semente -> mesmo resultado
    assert len(centros) == k and centros["perfil"].str.len().gt(0).all()


def test_nomes_de_perfil():
    centro = pd.Series(0.0, index=CATEGORIAS)
    centro["animais"] = 0.7
    centro["comida"] = 0.3
    assert nomear_cluster(centro) == "Pet lover"
    centro["comida"] = 0.65
    assert nomear_cluster(centro) == "Pet lover + Gastronômico"
    assert perfil_do_usuario(_df(), "exemplo:bruno").startswith("Tech & Games")
    assert perfil_do_usuario(_df(), "ninguem") is None


def test_anonimizar_remove_dados_pessoais():
    df = _df()
    df["foto_url"] = "fotos/abc.jpg"
    df.loc[0, "cidade"] = "Jardim da Penha, Vitória - ES"
    anon = anonimizar(df)
    assert not {"id", "foto_url"} & set(anon.columns)
    assert set(anon["usuario"]) == {"u01", "u02", "u03", "u04", "u05"}
    assert not anon["usuario"].str.contains("exemplo").any()
    assert (anon["criado_em"].dt.minute == 0).all()
    assert "Jardim da Penha" not in " ".join(anon["cidade"].dropna())
    assert len(anon) == len(df)


def test_sem_supabase_usa_memoria():
    from src import armazenamento, banco
    assert banco.configurado() is False          # sem secrets.toml nesta máquina
    assert banco.sessao_atual() is None
    assert "memória" in armazenamento.descricao_backend()
