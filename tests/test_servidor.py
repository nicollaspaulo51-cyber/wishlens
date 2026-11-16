"""Servidor do juiz (servidor/app.py), em memória e com um CLIP falso: sem rede e sem baixar o modelo."""

import io

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from servidor import app as srv  # noqa: E402


def _clip_falso(tema="carros", achado="volkswagen gol", borrada=False, vetor=None):
    def julgar(_imagem):
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
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon: [])
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
