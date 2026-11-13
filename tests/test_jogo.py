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


# ---------------------------------------------------------------- segundo juiz (CLIP)
def test_veto_do_clip():
    v = jogo.veto_clip
    assert "tela" in v("carros", "gemma+clip", "carros", 0.8, 0.6)
    assert "discordaram" in v("carros", "gemma+clip", "plantas", 0.05, 0.1)
    assert "CLIP: plantas" in v("carros", "gemma+clip", "plantas", 0.05, 0.1)
    assert v("carros", "gemma+clip", "plantas", 0.3, 0.1) is None    # discorda pouco: passa
    assert v("pecas", "gemma+clip", "pecas", 0.4, 0.7) is None       # monitor ligado é peça
    assert v("carros", "clip", "carros", 0.01, 0.9) is None          # só um juiz: sem veto
    assert v("carros", None, None, None, None) is None
    assert v("carros", "gemma+clip", None, float("nan"), float("nan")) is None


def test_foto_vetada_nao_conta_para_raridade():
    vetada = {**cap("ana", "Fiat Mobi", hora=8), "juiz": "gemma+clip", "clip_tema": "plantas",
              "clip_prob_tema": 0.03, "clip_prob_tela": 0.05}
    ok = {**cap("bia", "Fiat Mobi", hora=9), "juiz": "gemma+clip", "clip_tema": OUTRO,
          "clip_prob_tema": 0.6, "clip_prob_tela": 0.05}
    r = pts(vetada, ok)
    assert not r.loc[0, "aceita"] and "discordaram" in r.loc[0, "motivo"]
    assert r.loc[1, "raridade"] == 20  # a vetada não contou como "já achado"


def test_avaliacao_dos_juizes():
    base = {"juiz": "gemma+clip", "clip_prob_tela": 0.05}
    r = pts({**cap("ana", "Gol", tema="carros", hora=8), **base, "clip_tema": "carros", "clip_prob_tema": 0.7},
            {**cap("bia", "Uno", tema="carros", hora=9), **base, "clip_tema": "plantas", "clip_prob_tema": 0.05},
            {**cap("caio", "mouse", tema="pecas", hora=10), **base, "clip_tema": "pecas", "clip_prob_tema": 0.5},
            {**cap("davi", "", tema="nenhum", hora=11), **base, "clip_tema": "pecas", "contestada": "pecas"},
            {**cap("eva", "carro", tema="carros", hora=12), "juiz": "clip", "clip_tema": "carros"})
    a = jogo.avaliar_juizes(r)
    assert a["comparadas"] == 4 and a["concordancia"] == 0.5
    assert a["matriz"].loc["Carros", "Plantas e flores"] == 1 and a["matriz"].loc["nenhum", "Peças e periféricos de computador"] == 1
    assert a["vetos"].to_dict() == {"os juízes discordaram do tema": 1}
    assert a["especificos"] == 1.0
    assert a["contestadas"].iloc[0]["contestada"] == "Peças e periféricos de computador"
    assert jogo.avaliar_juizes(pd.DataFrame())["comparadas"] == 0


def test_exemplos_tem_opiniao_do_clip_e_discordancias():
    from src.exemplo import gerar_capturas
    a = jogo.avaliar_juizes(jogo.calcular_pontos(pd.DataFrame(gerar_capturas())))
    assert a["comparadas"] > 100 and 0.6 < a["concordancia"] < 0.98
    assert len(a["vetos"]) and not a["contestadas"].empty


def test_contestar_em_memoria(monkeypatch):
    import streamlit as st
    from src import armazenamento

    class Sessao(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    monkeypatch.setattr(st, "session_state", Sessao({"capturas": []}))
    monkeypatch.setattr(armazenamento, "_banco", lambda: None)
    i = armazenamento.salvar_captura(None, "", 0.5, True, None, None, None, juiz="gemma+clip", clip_tema="pecas")
    armazenamento.contestar(i, "pecas")
    df = armazenamento.capturas()
    assert df.loc[0, "contestada"] == "pecas" and df.loc[0, "juiz"] == "gemma+clip"


def test_banco_antigo_salva_sem_colunas_dos_juizes():
    from src import banco

    chamadas = []

    class Tabela:
        def insert(self, dados, returning=None):
            chamadas.append(dict(dados))
            if "juiz" in dados:
                raise RuntimeError("Could not find the 'juiz' column of 'capturas'")
            return self

        def execute(self):
            return None

    class Cliente:
        def table(self, nome):
            return Tabela()

    s = banco.Sessao.__new__(banco.Sessao)
    s.cliente, s.usuario_id = Cliente(), "u1"
    s.salvar_captura({"criado_em": datetime(2026, 11, 12, 10), "tema": "carros", "juiz": "gemma+clip",
                      "clip_tema": "carros"})
    assert len(chamadas) == 2 and "juiz" not in chamadas[1] and chamadas[1]["tema"] == "carros"


def test_veto_por_posicao_nao_barra_o_mouse():
    """Com a escala do CLIP (~100), um mouse um pouco mais parecido com "um quarto" dá 95% x 5%.
    A regra por posição não pode vetar isso: o tema do Gemma é o 2º palpite do CLIP."""
    import math
    from src.reconhecimento import probs_por_grupo
    grupos = ["nenhum", "pecas", "carros", "plantas", "passaros", "pets", "tela"]
    sims = [0.30, 0.27, 0.22, 0.21, 0.20, 0.21, 0.23]
    e = [math.exp(100 * s - 30) for s in sims]
    probs = probs_por_grupo(grupos, [x / sum(e) for x in e])
    assert probs["pecas"] < jogo.VETO_TEMA          # pela chance, seria vetado (o bug)
    rank = jogo.posicao(probs, "pecas")
    assert rank == 2
    assert jogo.veto_clip("pecas", "gemma+clip", None, probs["pecas"], probs["tela"], rank) is None
    assert "discordaram" in jogo.veto_clip("pecas", "gemma+clip", "plantas", 0.01, 0.0, 5)


def test_generico_repetido_vale_ate_3_vezes_por_dia():
    r = pts(*[cap("ana", "carro", tema="carros", hora=8 + k, h=f"{(k + 1) * 0x1111111111111111:016x}") for k in range(4)])
    assert list(r["aceita"]) == [True, True, True, False]
    assert set(r["pontos"][:3]) <= {10, 20} and "limite de 3 fotos genéricas" in r.loc[3, "motivo"]
    # achados específicos diferentes no mesmo dia valem todos (mouse, teclado)
    r = pts(cap("ana", "mouse", tema="pecas", hora=8), cap("ana", "teclado", tema="pecas", hora=9))
    assert list(r["aceita"]) == [True, True] and (r["novidade"] == 10).all()


def test_clip_ve_tela_e_barra_mesmo_com_gemma_dizendo_real():
    base = {"juiz": "gemma+clip", "clip_tema": "passaros", "clip_rank_tema": 1, "clip_prob_tela": 0.3}
    r = pts({**cap("ana", "periquito", tema="passaros"), **base, "clip_foto_real": False})
    assert not r.loc[0, "aceita"] and "tela" in r.loc[0, "motivo"]
    r = pts({**cap("ana", "monitor", tema="pecas"), **base, "clip_tema": "pecas", "clip_foto_real": False})
    assert r.loc[0, "aceita"]  # monitor ligado é peça
    r = pts({**cap("ana", "periquito", tema="passaros"), **base, "clip_foto_real": True})
    assert r.loc[0, "aceita"]
