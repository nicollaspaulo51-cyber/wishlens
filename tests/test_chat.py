"""Chat com amigos (servidor/chat.py), em memória, com o SQLite numa pasta temporária e um CLIP falso."""

import io
import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from servidor import app as srv  # noqa: E402
from servidor import chat  # noqa: E402


def _h(apelido):
    return {"X-Apelido": apelido, "X-Chave": f"chave-do-aparelho-de-{apelido}"}


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "SUPABASE", (None, None))
    monkeypatch.setattr(srv, "VISAO", (None, None, ""))
    monkeypatch.setattr(srv, "CLIP_INSTALADO", True)
    monkeypatch.setattr("src.reconhecimento.aquecer", lambda: None)
    monkeypatch.setattr(srv, "lugares_perto", lambda lat, lon, modo="livre": [])
    monkeypatch.setattr(srv, "AVISOS", tmp_path / "avisos.jsonl")
    monkeypatch.setattr(chat, "DADOS", tmp_path / "dados")
    srv._memoria.clear()
    chat._enviadas.clear()
    with TestClient(srv.app) as cliente:
        yield cliente


def _amigos(c, a="ana", b="bia"):
    assert c.post("/amigos", json={"apelido": b}, headers=_h(a)).json()["estado"] == "pedido"
    assert c.get("/amigos", headers=_h(b)).json()["recebidos"] == [a]
    assert c.post("/amigos/responder", json={"apelido": a, "aceitar": True}, headers=_h(b)).status_code == 200


def _jpeg_com_gps() -> bytes:
    img = Image.new("RGB", (64, 48), (200, 30, 30))
    exif = Image.Exif()
    exif[0x8825] = {1: "S", 2: (20.0, 18.0, 0.0)}  # GPSInfo com latitude
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    assert Image.open(io.BytesIO(buf.getvalue())).getexif().get_ifd(0x8825)  # a foto de teste tem GPS mesmo
    return buf.getvalue()


def test_pedido_aceite_e_conversa(c):
    _amigos(c)
    assert not c.get("/amigos", headers=_h("bia")).json()["amigos"][0]["ultima"]["minha"]  # a automática não é "Você:"
    r = c.post("/conversa/bia", data={"texto": "oi, achei um ipê!"}, headers=_h("ana")).json()
    assert r["minha"] and r["texto"] == "oi, achei um ipê!"
    assert c.get("/chat/novas", headers=_h("bia")).json()["nao_lidas"] == 1  # o "agora vocês são amigos" é da bia
    msgs = c.get("/conversa/ana", headers=_h("bia")).json()["mensagens"]
    assert [m["texto"] for m in msgs][-1] == "oi, achei um ipê!" and msgs[0]["sistema"]
    assert c.get("/chat/novas", headers=_h("bia")).json()["nao_lidas"] == 0
    amigos = c.get("/amigos", headers=_h("ana")).json()["amigos"]
    assert amigos[0]["apelido"] == "bia" and amigos[0]["ultima"]["minha"]


def test_chat_e_amigos_recusam_convidados(c):
    headers = {**_h("ana"), "X-Convidado": "1"}
    respostas = [c.get(rota, headers=headers) for rota in ("/amigos", "/chat/novas", "/conversa/bia")]
    respostas.append(c.post("/amigos", json={"apelido": "bia"}, headers=headers))
    for resposta in respostas:
        assert resposta.status_code == 403
        assert resposta.json()["detail"] == "Crie uma conta para adicionar amigos e conversar."


def test_pedido_cruzado_vira_amizade_e_recusa_apaga(c):
    c.post("/amigos", json={"apelido": "bia"}, headers=_h("ana"))
    assert c.post("/amigos", json={"apelido": "ana"}, headers=_h("bia")).json()["estado"] == "aceita"
    c.post("/amigos", json={"apelido": "caio"}, headers=_h("ana"))
    c.post("/amigos/responder", json={"apelido": "ana", "aceitar": False}, headers=_h("caio"))
    assert c.get("/amigos", headers=_h("ana")).json()["enviados"] == []


def test_so_amigos_conversam_e_bloqueio_vale_para_os_dois(c):
    assert c.post("/conversa/bia", data={"texto": "oi"}, headers=_h("ana")).status_code == 403
    _amigos(c)
    c.post("/bloquear", json={"apelido": "ana"}, headers=_h("bia"))
    assert c.post("/conversa/bia", data={"texto": "oi"}, headers=_h("ana")).status_code == 403
    assert c.post("/amigos", json={"apelido": "bia"}, headers=_h("ana")).status_code == 403


def test_chave_do_aparelho_protege_o_apelido(c):
    assert c.get("/amigos", headers={"X-Apelido": "ana"}).status_code == 401
    assert c.get("/amigos", headers=_h("ana")).status_code == 200
    outro = {"X-Apelido": "ana", "X-Chave": "outra-chave-qualquer-123"}
    assert c.get("/amigos", headers=outro).status_code == 403


def test_foto_sem_gps_so_para_os_dois_e_apagar_remove(c):
    _amigos(c)
    r = c.post("/conversa/bia", files={"foto": ("f.jpg", _jpeg_com_gps(), "image/jpeg")}, headers=_h("ana")).json()
    caminho = r["foto"]
    foto = c.get(caminho, headers=_h("bia"))
    assert foto.status_code == 200 and not Image.open(io.BytesIO(foto.content)).getexif()
    sem_assinatura = caminho.split("?")[0]
    assert c.get(sem_assinatura).status_code == 404 and c.get(sem_assinatura + "?t=" + "0" * 32).status_code == 404
    assert c.delete(f"/mensagem/{r['id']}", headers=_h("bia")).status_code == 404  # só quem mandou apaga
    assert c.delete(f"/mensagem/{r['id']}", headers=_h("ana")).status_code == 200
    assert c.get(caminho, headers=_h("bia")).status_code == 404
    assert not list((chat.DADOS / "fotos").iterdir())


def test_denuncia_vai_para_os_avisos(c):
    _amigos(c)
    r = c.post("/conversa/bia", data={"texto": "mensagem chata"}, headers=_h("ana")).json()
    assert c.post("/denunciar", json={"id": r["id"], "motivo": "ofensa"}, headers=_h("ana")).status_code == 404
    assert c.post("/denunciar", json={"id": r["id"], "motivo": "ofensa"}, headers=_h("bia")).status_code == 200
    linha = json.loads(srv.AVISOS.read_text(encoding="utf-8").splitlines()[-1])
    assert linha["tipo"] == "denuncia" and linha["denunciado"] == "ana" and linha["mensagem"] == "mensagem chata"


def test_cartao_so_de_achado_proprio_e_aceito(c, monkeypatch):
    def clip(_imagem, _modo="livre"):
        return {"nitidez": 80.0, "nao_identificou": False, "tema": "carros", "achado": "fiat uno", "foto_real": True,
                "confianca": 0.9, "probs": {"carros": 0.9, "tela": 0.02, "nenhum": 0.08}, "vetor": [1.0] + [0.0] * 511}
    monkeypatch.setattr(srv, "_clip", clip)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 120, 40)).save(buf, "JPEG")
    julgada = c.post("/julgar", files={"foto": ("f.jpg", buf.getvalue(), "image/jpeg")}, headers=_h("ana")).json()
    _amigos(c)
    r = c.post("/conversa/bia", data={"captura": julgada["id"]}, headers=_h("ana")).json()
    assert r["cartao"]["achado"] == "fiat uno" and r["cartao"]["pontos"] == julgada["cartao"]["pontos"]
    assert c.post("/conversa/ana", data={"captura": julgada["id"]}, headers=_h("bia")).status_code == 404


def test_limite_de_mensagens_por_minuto(c, monkeypatch):
    monkeypatch.setattr(chat, "MENSAGENS_POR_MINUTO", 3)
    _amigos(c)
    codigos = [c.post("/conversa/bia", data={"texto": f"oi {i}"}, headers=_h("ana")).status_code for i in range(3)]
    assert codigos == [200, 200, 429]  # o pedido de amizade também contou


def test_placar_dos_amigos(c, monkeypatch):
    def clip(_imagem, _modo="livre"):
        return {"nitidez": 80.0, "nao_identificou": False, "tema": "carros", "achado": "fiat uno", "foto_real": True,
                "confianca": 0.9, "probs": {"carros": 0.9, "tela": 0.02, "nenhum": 0.08}, "vetor": [1.0] + [0.0] * 511}
    monkeypatch.setattr(srv, "_clip", clip)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 120, 40)).save(buf, "JPEG")
    r = c.post("/julgar", files={"foto": ("f.jpg", buf.getvalue(), "image/jpeg")}, headers=_h("bia")).json()
    assert r["cartao"]["aceita"], r
    c.post("/julgar", files={"foto": ("f.jpg", buf.getvalue(), "image/jpeg")}, headers=_h("caio"))  # caio não é amigo da ana
    _amigos(c)
    r = c.get("/amigos/placar", headers=_h("ana")).json()["ranking"]
    assert [(x["apelido"], x["posicao"], x["voce"]) for x in r] == [("bia", 1, False), ("ana", 2, True)]
    assert r[0]["pontos"] > 0 and r[1]["pontos"] == 0
    assert c.get("/amigos/placar?modo=paisagens", headers=_h("ana")).json()["ranking"][0]["pontos"] == 0
    assert c.get("/amigos/placar?periodo=ano", headers=_h("ana")).status_code == 400


def test_estatisticas_so_com_amigos(c, monkeypatch):
    def clip(_imagem, _modo="livre"):
        return {"nitidez": 80.0, "nao_identificou": False, "tema": "carros", "achado": "fiat uno", "foto_real": True,
                "confianca": 0.9, "probs": {"carros": 0.9, "tela": 0.02, "nenhum": 0.08}, "vetor": [1.0] + [0.0] * 511}
    monkeypatch.setattr(srv, "_clip", clip)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 120, 40)).save(buf, "JPEG")
    assert c.post("/julgar", files={"foto": ("f.jpg", buf.getvalue(), "image/jpeg")}, headers=_h("bia")).json()["cartao"]["aceita"]
    assert c.get("/amigos/estatisticas?com=bia", headers=_h("ana")).status_code == 403  # ainda não são amigos
    _amigos(c)
    r = c.get("/amigos/estatisticas?com=bia", headers=_h("ana")).json()
    assert r["eu"]["resumo"]["fotos"] == 0 and r["amigo"]["resumo"]["fotos"] == 1
    assert r["amigo"]["resumo"]["pontos"] > 0 and r["amigo"]["por_dia"][-1]["valor"] == r["amigo"]["resumo"]["pontos"]
    assert {"cidade", "celula", "tipo_lugar"}.isdisjoint(json.dumps(r).split('"'))
    assert c.get("/amigos/estatisticas", headers=_h("ana")).json()["amigo"] is None
