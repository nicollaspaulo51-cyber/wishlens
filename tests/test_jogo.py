"""Regras do jogo: hash de foto, pontos, motivos de recusa e pódio."""

import io
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from PIL import Image, ImageDraw

from src import jogo
from src.temas import TEMAS, tema_do_dia

DIA = date(2026, 11, 10)
DO_DIA = tema_do_dia(DIA).id
OUTRO = next(t.id for t in TEMAS if t.id != DO_DIA)


def cap(usuario, achado, tema=OUTRO, hora=10, dia=DIA, real=True, h=None):
    return {"usuario": usuario, "criado_em": datetime(dia.year, dia.month, dia.day, hora),
            "tema": tema, "achado": achado, "foto_real": real, "foto_hash": h}


def pts(*capturas):
    return jogo.calcular_pontos(pd.DataFrame(capturas))


def _imagem(semente: int) -> Image.Image:
    img = Image.new("RGB", (400, 300), "white")
    d = ImageDraw.Draw(img)
    for k in range(6):
        x = (semente * 37 + k * 61) % 350
        d.rectangle((x, k * 45, x + 40 + semente % 30, k * 45 + 30), fill=(semente * 40 % 255, 80, 160))
    return img


def test_hash_pega_mesma_foto_reduzida_e_recomprimida():
    a = _imagem(1)
    buf = io.BytesIO()
    a.resize((200, 150)).save(buf, "JPEG", quality=40)
    b = Image.open(io.BytesIO(buf.getvalue()))
    assert jogo.distancia(jogo.hash_foto(a), jogo.hash_foto(b)) <= jogo.LIMITE_HASH
    assert jogo.distancia(jogo.hash_foto(a), jogo.hash_foto(_imagem(4))) > jogo.LIMITE_HASH
    assert len(jogo.hash_foto(a)) == 16


def test_normalizar_apelidos_e_acentos():
    assert jogo.normalizar("VW Gol") == jogo.normalizar("Volkswagen gol") == "volkswagen gol"
    assert jogo.normalizar("Ipê-Amarelo") == "ipe-amarelo"
    assert jogo.normalizar("gmail") == "gmail"  # apelido só como palavra inteira


def test_pontos_base_novidade_raridade():
    r = pts(cap("ana", "Fiat Mobi", hora=8), cap("bia", "fiat mobi", hora=9), cap("caio", "Fiat Mobi", hora=10),
            cap("ana", "Fiat Mobi", hora=11, dia=DIA + timedelta(days=0)))
    assert list(r["raridade"][:3]) == [20, 10, 7]  # quem acha primeiro ganha mais
    assert list(r["pontos"][:3]) == [40, 30, 27]   # base 10 + novidade 10 + raridade
    assert r.loc[3, "motivo"] == "você já achou isso hoje" and r.loc[3, "pontos"] == 0


def test_dia_seguinte_mesmo_achado_vale_sem_novidade():
    r = pts(cap("ana", "Fiat Mobi"), cap("ana", "Fiat Mobi", dia=DIA + timedelta(days=5)))
    linha = r.iloc[1]
    if linha["do_dia"]:
        return  # caiu no tema do dia: coberto em outro teste
    assert (linha["novidade"], linha["raridade"], linha["pontos"]) == (0, 10, 20)


def test_tema_do_dia_dobra():
    r = pts(cap("ana", "bem-te-vi", tema=DO_DIA))
    assert bool(r.loc[0, "do_dia"]) and r.loc[0, "pontos"] == 80


def test_recusas_com_motivo():
    r = pts(cap("ana", "Fiat Mobi", real=False), cap("ana", "geladeira", tema="nenhum"),
            cap("ana", "", hora=12), cap("ana", "Gol", h="ffff0000ffff0000", hora=13),
            cap("bia", "gol", h="ffff0000ffff0001", hora=14))
    assert list(r["aceita"]) == [False, False, False, True, False]
    assert "foto real" in r.loc[0, "motivo"] and "nenhum tema" in r.loc[1, "motivo"]
    assert r.loc[4, "motivo"] == "foto repetida"  # mesma foto enviada por outra pessoa
    assert r["pontos"][[0, 1, 2, 4]].sum() == 0


def test_achado_generico_so_base():
    carro = next(t for t in TEMAS if t.id == "carros")
    r = pts(cap("ana", carro.generico, tema="carros"))
    assert (r.loc[0, "novidade"], r.loc[0, "raridade"]) == (0, 0)
    assert r.loc[0, "pontos"] in (10, 20)


def test_pontuar_nova_e_vezes():
    hist = jogo.calcular_pontos(pd.DataFrame([cap("ana", "Fiat Mobi")]))
    nova = jogo.pontuar_nova(hist, cap("bia", "fiat mobi", hora=11))
    assert nova["raridade"] == 10 and nova["aceita"]
    assert jogo.vezes_achado(hist, OUTRO, "FIAT MOBI") == 1


def test_podio_periodos_e_desempate():
    r = pts(cap("ana", "A", hora=8), cap("bia", "B", hora=9),  # empatam: ana chegou antes
            cap("caio", "C", dia=DIA - timedelta(days=20)))
    hoje = jogo.podio(r, "hoje", hoje=DIA)
    assert list(hoje["usuario"]) == ["ana", "bia"] and list(hoje["posicao"]) == [1, 2]
    assert "caio" in set(jogo.podio(r, "geral", hoje=DIA)["usuario"])
    assert "caio" not in set(jogo.podio(r, "semana", hoje=DIA)["usuario"])
    assert jogo.podio(r, "hoje", tema="pets" if OUTRO != "pets" else "carros", hoje=DIA).empty
    assert jogo.posicao_de(hoje, "bia") == 2 and jogo.posicao_de(hoje, "zé") is None


def test_celula_nao_e_coordenada_exata():
    assert jogo.celula(-20.29051, -40.29302) == "-20.290,-40.295"
    assert jogo.celula(None, 1) is None
    assert jogo.centro_celula("-20.290,-40.295") == (-20.29, -40.295)


def test_estilo_de_jogador_e_exportacao():
    from src.exemplo import gerar_capturas
    from src.exportar import anonimizar
    df = jogo.calcular_pontos(pd.DataFrame(gerar_capturas()))
    assert jogo.estilo_jogador(df, "exemplo:caio") in {
        v for v in jogo.NOMES_ESTILO.values()} | {f"{a} + {b}" for a in jogo.NOMES_ESTILO.values()
                                                  for b in jogo.NOMES_ESTILO.values()}
    assert jogo.estilo_jogador(df, "ninguém") is None
    saida = anonimizar(df)
    assert "foto_hash" not in saida and "celula" not in saida
    assert saida["usuario"].str.match(r"^u\d+$").all()


def test_mesma_foto_so_e_repetida_para_o_mesmo_achado():
    """Dois pássaros contra o céu podem ter hash parecido: achados diferentes não são "repetida"."""
    h = "ffff0000ffff0000"
    r = pts(cap("ana", "bem-te-vi", h=h, hora=8), cap("bia", "sabiá", h=h, hora=9),
            cap("caio", "Bem-te-vi", h=h, hora=10))
    assert list(r["aceita"]) == [True, True, False] and r.loc[2, "motivo"] == "foto repetida"


def test_capturas_misturando_memoria_e_supabase(monkeypatch):
    """Exemplos em memória (sem fuso) + linhas do Supabase (ISO com fuso) não podem quebrar a página."""
    import streamlit as st
    from src import armazenamento
    from src.banco import para_brasilia

    class BancoFalso:
        def capturas_todas(self):
            return [{"id": "1", "usuario": "bia", "criado_em": para_brasilia("2026-11-12T13:00:00+00:00"),
                     "tema": "carros", "achado": "Gol", "confianca": 0.9, "foto_real": True, "foto_hash": None}]

    class Sessao(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    monkeypatch.setattr(st, "session_state", Sessao({"capturas": [
        {"id": "2", "usuario": "exemplo:ana", "criado_em": datetime(2026, 11, 12, 9, 30), "tema": "pets",
         "achado": "gato", "confianca": None, "foto_real": True, "foto_hash": None, "cidade": None, "celula": None}]}))
    monkeypatch.setattr(armazenamento, "_banco", lambda: BancoFalso())
    df = armazenamento.capturas()
    assert df["criado_em"].dt.tz is None
    assert sorted(df["criado_em"].dt.hour) == [9, 10]  # 13h UTC = 10h em Brasília
    assert len(jogo.podio(jogo.calcular_pontos(df), "geral")) == 2


def test_para_brasilia():
    from src.banco import para_brasilia
    assert para_brasilia("2026-11-13T02:30:00Z") == datetime(2026, 11, 12, 23, 30)
    assert para_brasilia(datetime(2026, 1, 1, 8)) == datetime(2026, 1, 1, 8)
