"""Servidor do juiz (servidor/app.py), em memória e com um CLIP falso: sem rede e sem baixar o modelo."""

import io
from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from servidor import app as srv  # noqa: E402
from src import jogo  # noqa: E402


def _clip_falso(tema="carros", achado="volkswagen gol", borrada=False, vetor=None):
    def julgar(_imagem, _modo="livre"):
        return {"nitidez": 80.0, "nao_identificou": borrada, "tema": tema, "achado": achado, "foto_real": True,
                "confianca": 0.9, "probs": {tema: 0.9, "tela": 0.02, "nenhum": 0.08},
                "vetor": vetor or [1.0] + [0.0] * 511}
    return julgar


def _jpeg(cor=(200, 30, 30), deslocar=0) -> bytes:
    img = Image.new("RGB", (320, 240), (40, 90, 160))
    ImageDraw.Draw(img).rectangle((60 + deslocar, 110, 260, 180), fill=cor)
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(srv, "SUPABASE", (None, None))
    monkeypatch.setattr(srv, "VISAO", (None, None, ""))
    monkeypatch.setattr(srv, "CLIP_INSTALADO", True)
    monkeypatch.setattr(srv, "_clip", _clip_falso())
    monkeypatch.setattr("src.reconhecimento.aquecer", lambda: None)  # não carrega o CLIP de verdade
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon, modo="livre": [])
    monkeypatch.setattr(srv, "_bairro_seguro", lambda lat, lon: "Centro, Vitória - ES")
    monkeypatch.setattr(srv, "_clima", lambda *a: None)
    srv._memoria.clear()
    srv._ultima_foto.clear()
    with TestClient(srv.app) as c:
        yield c


def _enviar(c, dados=None, apelido="ana", **form):
    return c.post("/julgar", files={"foto": ("f.jpg", dados or _jpeg(), "image/jpeg")},
                  data={k: str(v) for k, v in form.items()}, headers={"X-Apelido": apelido}).json()


def test_foto_aceita_conta_no_placar_no_podio_e_na_colecao(cliente):
    r = _enviar(cliente)
    assert r["status"] == "ok" and r["cartao"]["aceita"] and r["cartao"]["pontos"] > 0
    assert r["cartao"]["tema"]["id"] == "carros" and r["posicao"] == 1
    estado = cliente.get("/estado", headers={"X-Apelido": "ana"}).json()
    assert estado["pontos_hoje"] == r["pontos_hoje"] == r["cartao"]["pontos"]
    podio = cliente.get("/podio", params={"periodo": "hoje"}, headers={"X-Apelido": "ana"}).json()
    assert podio["ranking"][0] == {"posicao": 1, "apelido": "ana", "pontos": r["cartao"]["pontos"],
                                   "achados": 1, "voce": True}
    colecao = cliente.get("/colecao", headers={"X-Apelido": "ana"}).json()
    carros = next(p for p in colecao["album"] if p["tema"]["id"] == "carros")
    assert carros["colados"] == [{"achado": "volkswagen gol", "turma": 1}]


def test_mesmo_objeto_de_novo_nao_vale(cliente):
    _enviar(cliente)
    r = _enviar(cliente, _jpeg(deslocar=30))  # outra foto, mesmo vetor do CLIP
    assert not r["cartao"]["aceita"] and r["cartao"]["pontos"] == 0


def test_foto_borrada_pede_outra_e_nao_salva(cliente, monkeypatch):
    monkeypatch.setattr(srv, "_clip", _clip_falso(borrada=True))
    r = _enviar(cliente)
    assert r["status"] == "borrada" and "borrada" in r["mensagem"]
    assert srv._memoria == []


def test_gps_vira_so_campos_derivados_e_da_mirante(cliente, monkeypatch):
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon: [{"lat": lat, "lon": lon, "tipo": "parking"}])
    r = _enviar(cliente, lat=-20.2976, lon=-40.2958)
    assert any("mirante" in b for b in r["cartao"]["bonus"])
    salvo = srv._memoria[0]
    assert salvo["celula"] == "-20.300,-40.295" and salvo["mirante"] and salvo["cidade"] == "Centro, Vitória - ES"
    assert -20.2976 not in salvo.values()


def test_recusa_entrada_invalida(cliente):
    h = {"X-Apelido": "ana"}
    assert cliente.post("/julgar", files={"foto": ("f.jpg", b"nao e foto", "image/jpeg")}, headers=h).status_code == 400
    assert cliente.post("/julgar", files={"foto": ("f.jpg", _jpeg(), "image/jpeg")}, data={"modo": "x"},
                        headers=h).status_code == 400
    assert cliente.get("/podio", params={"periodo": "ano"}, headers=h).status_code == 400


def test_com_supabase_exige_login(cliente, monkeypatch):
    monkeypatch.setattr(srv, "SUPABASE", ("https://x.supabase.co", "chave"))
    assert cliente.get("/estado").status_code == 401


@pytest.mark.parametrize("supabase", [False, True])
def test_servidor_convidado_sem_bearer_e_sem_competicao(cliente, monkeypatch, supabase):
    monkeypatch.setattr(srv, "SUPABASE", ("configurado", "configurado") if supabase else (None, None))
    monkeypatch.setattr(srv, "CLIP_INSTALADO", False)
    headers = {"X-Apelido": "ana", "X-Convidado": "1"}
    assert cliente.get("/estado", headers=headers).json()["convidado"] is True
    assert cliente.get("/estado", headers={**headers, "X-Apelido": "Jo%C3%A3o"}).json()["apelido"] == "João"
    assert cliente.get("/estado", headers={"X-Convidado": "1"}).status_code == 400
    podio = cliente.get("/podio", headers=headers)
    assert podio.status_code == 403 and podio.json()["detail"] == "Crie uma conta para entrar no pódio."
    julgar = cliente.post("/julgar", headers=headers, data={"modo": "competicao"},
                          files={"foto": ("f.jpg", b"sem imagem", "image/jpeg")})
    assert julgar.status_code == 403
    assert julgar.json()["detail"] == "Crie uma conta para participar das competições."
    assert srv._memoria == []


def test_servidor_captura_convidada_so_conta_para_o_proprio_jogador(cliente):
    headers = {"X-Apelido": "ana", "X-Convidado": "1", "X-Chave": "identificador-do-aparelho"}
    foto = cliente.post("/julgar", headers=headers, files={"foto": ("f.jpg", _jpeg(), "image/jpeg")})
    assert foto.status_code == 200 and foto.json()["cartao"]["aceita"]
    assert srv._memoria[0]["convidado"] is True
    estado = cliente.get("/estado", headers=headers).json()
    assert estado["pontos_hoje"] == foto.json()["pontos_hoje"] > 0
    assert estado["posicao"] is None and foto.json()["posicao"] is None
    album = cliente.get("/colecao", headers=headers).json()["album"]
    carros = next(pagina for pagina in album if pagina["tema"]["id"] == "carros")
    assert carros["colados"] == [{"achado": "volkswagen gol", "turma": 1}]
    assert cliente.get("/estado", headers={**headers, "X-Chave": "outro-aparelho"}).json()["pontos_hoje"] == 0
    assert cliente.get("/podio", headers={"X-Apelido": "ana"}).json()["ranking"] == []
    assert _enviar(cliente, apelido="bia")["cartao"]["aceita"]
    ranking = cliente.get("/podio", headers={"X-Apelido": "ana"}).json()["ranking"]
    assert [linha["apelido"] for linha in ranking] == ["bia"]
    capturas = srv.pd.DataFrame(srv._memoria).assign(celula="quadrado")
    assert srv.jogo.guardioes(capturas.assign(convidado=False))["usuario"].size == 1
    assert srv.jogo.guardioes(capturas).empty
    pontuadas = capturas.assign(aceita=True, pontos=10)
    assert list(srv.jogo.podio(pontuadas)["usuario"]) == ["bia"]


def test_mapa_avisa_quando_o_openstreetmap_nao_respondeu(cliente, monkeypatch):
    h = {"X-Apelido": "ana"}
    pos = {"lat": -20.3, "lon": -40.3}
    assert cliente.post("/mapa", json=pos, headers=h).json()["lugares_ok"] is True  # lista vazia de verdade
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon: None)
    r = cliente.post("/mapa", json=pos, headers=h).json()
    assert r["lugares"] == [] and r["lugares_ok"] is False
    assert _enviar(cliente, lat=-20.3, lon=-40.3)["status"] == "ok"  # a foto vale mesmo sem o Overpass


def test_aviso_de_suporte_vai_para_o_arquivo_com_o_que_o_juiz_disse(cliente, monkeypatch, tmp_path):
    import json
    monkeypatch.setattr(srv, "AVISOS", tmp_path / "avisos.jsonl")
    srv._avisos_recentes.clear()
    foto = _enviar(cliente, lat=-20.3, lon=-40.3)
    h = {"X-Apelido": "ana"}
    r = cliente.post("/aviso", json={"tipo": "juiz", "texto": "Era um fone, não um mouse", "captura": foto["id"],
                                     "aparelho": "android"}, headers=h)
    assert r.json() == {"ok": True}
    aviso = json.loads((tmp_path / "avisos.jsonl").read_text(encoding="utf-8"))
    assert aviso["apelido"] == "ana" and aviso["texto"] == "Era um fone, não um mouse"
    assert aviso["juiz_disse"]["tema"] == "carros" and "celula" not in aviso["juiz_disse"]
    assert "-20.3" not in json.dumps(aviso)  # nada da localização
    assert cliente.post("/aviso", json={"tipo": "x", "texto": "abc"}, headers=h).status_code == 400
    assert cliente.post("/aviso", json={"tipo": "app", "texto": "a" * 501}, headers=h).status_code == 422
    for _ in range(4):
        assert cliente.post("/aviso", json={"tipo": "app", "texto": "travou"}, headers=h).status_code == 200
    assert cliente.post("/aviso", json={"tipo": "app", "texto": "travou"}, headers=h).status_code == 429


# ---------------------------------------------------------------- abas Paisagens, Treino e Academias
def _lugar(tipo, dlat=0.0):
    return lambda lat, lon, modo="livre": [{"lat": lat + dlat, "lon": lon, "tipo": tipo}]


def test_paisagem_pontua_so_na_sua_aba_e_nao_mexe_no_mapa_livre(cliente, monkeypatch):
    monkeypatch.setattr(srv, "_clip", _clip_falso(tema="paisagens", achado="pôr do sol"))
    r = _enviar(cliente, modo="paisagens")
    assert r["cartao"]["aceita"] and r["cartao"]["tema"]["id"] == "paisagens" and r["modo"] == "paisagens"
    h = {"X-Apelido": "ana"}
    assert cliente.get("/podio", params={"modo": "paisagens"}, headers=h).json()["ranking"][0]["apelido"] == "ana"
    assert cliente.get("/podio", headers=h).json()["ranking"] == []      # o pódio do Mapa livre não vê
    assert cliente.get("/estado", headers=h).json()["pontos_hoje"] == 0


def test_aba_errada_diz_onde_a_foto_vale(cliente, monkeypatch):
    def arvore(_imagem, _modo="livre"):
        return {**_clip_falso(tema=None, achado="")(_imagem), "tema": None, "outra_aba": "livre"}
    monkeypatch.setattr(srv, "_clip", arvore)
    r = _enviar(cliente, modo="paisagens")
    assert not r["cartao"]["aceita"] and "Mapa livre" in r["cartao"]["motivo"]


def test_treino_e_academia_exigem_estar_no_lugar(cliente, monkeypatch):
    monkeypatch.setattr(srv, "_clip", _clip_falso(tema="treino", achado="barra fixa"))
    sem_gps = _enviar(cliente, modo="treino")
    assert sem_gps["status"] == "borrada" and "localização" in sem_gps["titulo"] and srv._memoria == []
    monkeypatch.setattr(srv, "lugares_perto", _lugar("fitness_station", dlat=0.01))  # ~1 km
    longe = _enviar(cliente, modo="treino", lat=-20.3, lon=-40.3)
    assert not longe["cartao"]["aceita"] and "praça" in longe["cartao"]["motivo"]
    monkeypatch.setattr(srv, "lugares_perto", _lugar("fitness_station"))
    monkeypatch.setattr(srv, "_clip", _clip_falso(tema="treino", achado="barra fixa", vetor=[0.0, 1.0] + [0.0] * 510))
    perto = _enviar(cliente, _jpeg(deslocar=40), modo="treino", lat=-20.3, lon=-40.3)
    assert perto["cartao"]["aceita"] and any("praça nova" in b for b in perto["cartao"]["bonus"])
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon, modo="livre": None)
    assert _enviar(cliente, modo="treino", lat=-20.3, lon=-40.3)["titulo"] == "Lugar não confirmado"


def test_dono_da_academia_aparece_com_duas_pessoas(cliente, monkeypatch):
    monkeypatch.setattr(srv, "lugares_perto", _lugar("fitness_centre"))
    for apelido, aparelhos in (("ana", ["supino", "esteira"]), ("bia", ["supino"])):
        for i, a in enumerate(aparelhos):
            monkeypatch.setattr(srv, "_clip", _clip_falso(tema="academia", achado=a, vetor=[0.0] * i + [1.0] + [0.0] * (511 - i)))
            assert _enviar(cliente, _jpeg(deslocar=10 * i + (50 if apelido == "bia" else 0)), apelido=apelido,
                           modo="academia", lat=-20.3, lon=-40.3)["cartao"]["aceita"]
    podio = cliente.get("/podio", params={"modo": "academia"}, headers={"X-Apelido": "ana"}).json()
    assert podio["donos"] == [{"apelido": "ana", "quadrados": 1}] and podio["guardioes"] == []
    assert podio["ranking"][0]["apelido"] == "ana"


def test_competicao_espera_15_minutos_e_vitoria_vale_mais(cliente, monkeypatch):
    chamadas = []
    def clip(tema, achado):
        falso = _clip_falso(tema=tema, achado=achado)
        return lambda img, modo="livre": (chamadas.append(1), falso(img, modo))[1]
    monkeypatch.setattr(srv, "_clip", clip(None, ""))
    assert not _enviar(cliente, modo="competicao")["cartao"]["aceita"]  # não é tela de jogo: não trava a espera
    monkeypatch.setattr(srv, "_clip", clip("competicao", "vitória"))
    venceu = _enviar(cliente, _jpeg(deslocar=30), modo="competicao")
    assert venceu["cartao"]["aceita"] and venceu["cartao"]["pontos"] == jogo.VITORIA
    antes = len(chamadas)
    espera = _enviar(cliente, _jpeg(deslocar=60), modo="competicao")
    assert espera["status"] == "borrada" and "Espere" in espera["titulo"] and len(chamadas) == antes  # nem chama o CLIP
    assert cliente.get("/estado", headers={"X-Apelido": "ana"}).json()["espera_competicao"] > 14 * 60
    for linha in srv._memoria:  # 16 minutos depois
        linha["criado_em"] = linha["criado_em"] - timedelta(minutes=16)
    monkeypatch.setattr(srv, "_clip", clip("competicao", "derrota"))
    perdeu = _enviar(cliente, _jpeg(deslocar=90), modo="competicao")
    assert perdeu["cartao"]["aceita"] and perdeu["cartao"]["pontos"] == jogo.DERROTA


def test_abas_procuram_mais_longe_quando_tem_pouco_lugar(monkeypatch):
    raios = []
    def busca(temas, lat, lon, raio_m=2000, por_tema=15):
        raios.append(raio_m)
        return [{"tema": temas[0].id}] * (0 if raio_m < 10000 else 4)
    monkeypatch.setattr(srv, "buscar_pontos_temas", busca)
    srv._lugares.cache_clear()
    assert len(srv.lugares_perto(-20.3, -40.3, "academia")) == 4 and raios == [2000, 5000, 10000]
    raios.clear()
    srv.lugares_perto(-20.3, -40.3, "livre")
    assert raios == [2000]
    srv._lugares.cache_clear()


def test_ia_barra_foto_falsa_em_outra_aba_mas_nao_troca_o_tema(cliente, monkeypatch):
    monkeypatch.setattr(srv, "VISAO", ("http://ia", None, "m"))
    monkeypatch.setattr(srv, "_clip", _clip_falso(tema="paisagens", achado="pôr do sol"))
    from src import visao
    monkeypatch.setattr(visao, "identificar_captura", lambda *a: visao.Captura("carros", "gol", False, 0.9))
    r = _enviar(cliente, modo="paisagens")
    assert not r["cartao"]["aceita"] and r["cartao"]["tema"]["id"] == "paisagens"
    assert "não é foto real" in r["cartao"]["motivo"]


def test_competicao_nao_chama_a_ia(cliente, monkeypatch):
    monkeypatch.setattr(srv, "VISAO", ("http://ia", None, "m"))
    from src import visao
    def nao_chama(*a):
        raise AssertionError("a IA não deve julgar a Competição")
    monkeypatch.setattr(visao, "identificar_captura", nao_chama)
    monkeypatch.setattr(srv, "_clip", _clip_falso(tema="competicao", achado="vitória"))
    assert _enviar(cliente, modo="competicao")["status"] == "ok"


def test_lugares_guardados_quando_o_mapa_nao_responde(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "RESERVA_LUGARES", tmp_path / "lugares.json")
    monkeypatch.setattr(srv, "_reserva", None)
    parque = [{"tema": "plantas", "nome": "Parque", "lat": -20.3, "lon": -40.3, "distancia_km": 0.1}]
    srv._lugares.cache_clear()
    monkeypatch.setattr(srv, "buscar_pontos_temas", lambda *a, **k: parque)
    assert srv.lugares_perto(-20.301, -40.301) == parque
    srv._lugares.cache_clear()

    def fora(*a, **k):
        raise RuntimeError("Overpass fora")
    monkeypatch.setattr(srv, "buscar_pontos_temas", fora)
    assert srv.lugares_perto(-20.302, -40.299) == parque          # mesmo quadrado: usa o guardado
    srv._lugares.cache_clear()
    assert srv.lugares_perto(-20.31, -40.30) == parque            # quadrado vizinho também
    srv._lugares.cache_clear()
    monkeypatch.setattr(srv, "buscar_pontos_temas", lambda *a, **k: [])
    assert srv.lugares_perto(-20.301, -40.301) == parque          # Overpass vazio não apaga os ícones
    monkeypatch.setattr(srv, "_reserva", None)                     # reinício do servidor: lê do disco
    srv._lugares.cache_clear()
    assert srv.lugares_perto(-20.301, -40.301) == parque
    assert srv.lugares_perto(-23.5, -46.6) == []                  # lugar novo e vazio: nada a mostrar
    srv._lugares.cache_clear()


def test_clip_treinado_decide_e_ia_so_barra_quando_ele_desconfia(cliente, monkeypatch):
    import numpy as np

    from src import treino_juiz as tj, visao

    s = tj.Sonda(np.zeros((6, 512)), np.zeros(6), np.zeros(512), 0.0, 1.0, 1.0, 0.75, "t", limiar_ia=0.6, tema_da_ia=False)
    monkeypatch.setattr("src.reconhecimento.sonda", lambda: s)
    monkeypatch.setattr(srv, "VISAO", ("http://ia", None, "m"))
    monkeypatch.setattr(visao, "identificar_captura", lambda *a: visao.Captura("carros", "fiat uno", False, 0.9))

    def clip(tela):
        def julgar(_imagem, _modo="livre"):
            return {"nitidez": 80.0, "nao_identificou": False, "tema": "carros", "achado": "carro", "foto_real": True,
                    "confianca": 0.9, "treinado": True, "vetor": [1.0] + [0.0] * 511,
                    "probs": {"carros": 0.9 - tela, "nenhum": 0.1, "tela": tela}}
        return julgar
    monkeypatch.setattr(srv, "_clip", clip(0.05))   # IA diz falsa, CLIP treinado está tranquilo: vale
    r = _enviar(cliente)
    assert r["cartao"]["aceita"] and r["cartao"]["achado"] == "fiat uno"
    monkeypatch.setattr(srv, "_clip", clip(0.65))   # CLIP também desconfia: a IA derruba
    r = _enviar(cliente, _jpeg(cor=(10, 200, 10)), apelido="bia")
    assert not r["cartao"]["aceita"] and "não é foto real" in r["cartao"]["motivo"]


def test_sessao_do_supabase_monta_com_cliente_usuario_e_apelido():
    from src import banco
    s = banco.Sessao(object(), "uid-1", "ana")  # o servidor monta assim depois de ler o perfil
    assert (s.usuario_id, s.apelido, s.convidado) == ("uid-1", "ana", False)
