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
    assert len(X) == 13          # 12 pessoas fictícias + "exemplo:eu"
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
    # os 4 estilos fictícios devem virar 4 grupos, cada um com as 3 pessoas do estilo
    from src.exemplo import PESSOAS_EXEMPLO
    rot = r1.set_index("usuario")["cluster"]
    for estilo in set(PESSOAS_EXEMPLO.values()):
        membros = [u for u, e in PESSOAS_EXEMPLO.items() if e == estilo]
        assert rot[membros].nunique() == 1


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
    assert set(anon["usuario"]) == {f"u{i:02d}" for i in range(1, 14)}
    assert not anon["usuario"].str.contains("exemplo").any()
    assert (anon["criado_em"].dt.minute == 0).all()
    assert "Jardim da Penha" not in " ".join(anon["cidade"].dropna())
    assert len(anon) == len(df)


def test_sem_supabase_usa_memoria():
    from src import armazenamento, banco
    assert banco.configurado() is False          # sem secrets.toml nesta máquina
    assert banco.sessao_atual() is None
    assert "memória" in armazenamento.descricao_backend()


def test_feed_recomenda_coisas_novas_e_relacionadas():
    from src.feed import gerar_feed, vizinhos
    df = _df()
    feed = gerar_feed(df, "exemplo:bruno", quantidade=12)
    ja = set(df[df["usuario"] == "exemplo:bruno"]["item"])
    assert len(feed) == 12
    assert not {c.item.nome for c in feed} & ja                       # nada que ele já deseja
    # os itens que ainda faltam nas 2 categorias favoritas dele vêm primeiro
    from src.categorias import ITENS
    restantes = {i.nome for i in ITENS if i.categoria in {"eletrônicos", "brinquedos e games"}} - ja
    assert restantes and restantes <= {c.item.nome for c in feed[:len(restantes) + 1]}
    assert any(c.tipo_motivo == "novo" for c in feed)                  # há exploração
    # os vizinhos de um "tech" são os outros "tech"
    assert {u for u, _ in vizinhos(df, "exemplo:bruno")[:2]} == {"exemplo:diego", "exemplo:enzo"}
    # ocultar tira o item; páginas não se repetem
    oculto = feed[0].item.nome
    assert oculto not in {c.item.nome for c in gerar_feed(df, "exemplo:bruno", ocultos={oculto}, quantidade=50)}
    p0 = {c.item.nome for c in gerar_feed(df, "exemplo:bruno", quantidade=8, pagina=0)}
    p1 = {c.item.nome for c in gerar_feed(df, "exemplo:bruno", quantidade=8, pagina=1)}
    assert not p0 & p1
