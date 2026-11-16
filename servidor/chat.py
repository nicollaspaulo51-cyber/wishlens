"""Chat com amigos: pedidos de amizade, conversas com texto, foto e cartão de achado, bloquear, apagar e denunciar.

Fica num SQLite no volume do Docker (DADOS_DIR, padrão /home/user/dados), junto com as fotos (fotos/<id>.jpg).
As fotos são gravadas de novo em JPEG sem EXIF nem GPS e só quem mandou e quem recebeu as vê.

Sem o Supabase o apelido não tem senha. Para ninguém ler o chat de outra pessoa, cada aparelho manda uma chave
aleatória (X-Chave): o primeiro aparelho que usa o apelido no chat fica com ele.
shortcut: trocar de celular perde o acesso ao chat do apelido; com o Supabase o login resolve.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from servidor.app import (ABAS, FOTO_MAX, SessaoMemoria, TODOS, _capturas, _pontuadas, _pontuadas_aba, gravar_aviso,
                          sessao)
from src.categorias import nome_valido
from src.fotos import preparar_para_salvar
from src.temas import agora

router = APIRouter()
DADOS = Path(os.environ.get("DADOS_DIR", "/home/user/dados"))
MENSAGENS_POR_MINUTO = 30
HISTORICO = 100  # mensagens que a conversa mostra (as mais novas)

_trava = threading.Lock()
_enviadas: dict[str, list[float]] = {}

TABELAS = """
create table if not exists chaves (apelido text primary key, hash text not null);
create table if not exists amizades (de text not null, para text not null, estado text not null,
                                     criado_em text not null, primary key (de, para));
create table if not exists bloqueios (de text not null, para text not null, primary key (de, para));
create table if not exists mensagens (id integer primary key autoincrement, de text not null, para text not null,
    texto text not null default '', foto text, cartao text, criado_em text not null,
    lida integer not null default 0, apagada integer not null default 0, sistema integer not null default 0);
create index if not exists mensagens_par on mensagens (de, para);
"""


@contextmanager
def _db():
    DADOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DADOS / "chat.db", timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(TABELAS)
        yield con
        con.commit()
    finally:
        con.close()


def eu(s=Depends(sessao), x_chave: str | None = Header(None)) -> str:
    """O apelido de quem chama. Sem o Supabase, confere a chave do aparelho."""
    if isinstance(s, SessaoMemoria):
        if not x_chave or not 16 <= len(x_chave) <= 128:
            raise HTTPException(401, "Atualize o app para usar o chat.")
        h = hashlib.sha256(x_chave.encode()).hexdigest()
        with _db() as db:
            dono = db.execute("select hash from chaves where apelido = ?", (s.apelido,)).fetchone()
            if dono is None:
                db.execute("insert into chaves values (?, ?)", (s.apelido, h))
            elif dono["hash"] != h:
                raise HTTPException(403, "Este apelido já usa o chat em outro aparelho.")
    return s.apelido


def _outro(apelido: str, mim: str) -> str:
    apelido = apelido.strip()
    if not nome_valido(apelido) or apelido == mim:
        raise HTTPException(400, "Apelido inválido.")
    return apelido


def _amigos(db, a: str, b: str) -> bool:
    return db.execute("select 1 from amizades where estado = 'aceita' and ((de = ? and para = ?) or (de = ? and para = ?))",
                      (a, b, b, a)).fetchone() is not None


def _bloqueado(db, a: str, b: str) -> bool:
    return db.execute("select 1 from bloqueios where (de = ? and para = ?) or (de = ? and para = ?)",
                      (a, b, b, a)).fetchone() is not None


def _limite(mim: str) -> None:
    instante = time.time()
    with _trava:
        recentes = [t for t in _enviadas.get(mim, []) if instante - t < 60]
        if len(recentes) >= MENSAGENS_POR_MINUTO:
            raise HTTPException(429, "Muitas mensagens seguidas. Espere um pouco.")
        _enviadas[mim] = [*recentes, instante]


def _agora() -> str:
    return agora().isoformat(timespec="seconds")


def _mensagem(r, mim: str) -> dict:
    return {"id": r["id"], "de": r["de"], "minha": r["de"] == mim, "texto": r["texto"], "sistema": bool(r["sistema"]),
            "foto": f"/foto/{r['foto']}" if r["foto"] else None,
            "cartao": json.loads(r["cartao"]) if r["cartao"] else None, "criado_em": r["criado_em"]}


def _resumo(r) -> str:
    if r["texto"]:
        return r["texto"]
    return "🃏 Cartão de achado" if r["cartao"] else "📷 Foto"


# ---------------------------------------------------------------- amigos
class Pedido(BaseModel):
    apelido: str = Field(max_length=30)


class Resposta(Pedido):
    aceitar: bool


@router.get("/amigos")
def amigos(mim: str = Depends(eu)):
    with _db() as db:
        linhas = db.execute("select * from amizades where de = ? or para = ?", (mim, mim)).fetchall()
        lista = []
        for r in linhas:
            if r["estado"] != "aceita":
                continue
            outro = r["para"] if r["de"] == mim else r["de"]
            ultima = db.execute("select * from mensagens where apagada = 0 and ((de = ? and para = ?) or (de = ? and para = ?)) "
                                "order by id desc limit 1", (mim, outro, outro, mim)).fetchone()
            nao_lidas = db.execute("select count(*) from mensagens where de = ? and para = ? and lida = 0 and apagada = 0",
                                   (outro, mim)).fetchone()[0]
            lista.append({"apelido": outro, "nao_lidas": nao_lidas,
                          # a mensagem automática ("agora vocês são amigos") não é de ninguém
                          "ultima": {"texto": _resumo(ultima), "minha": ultima["de"] == mim and not ultima["sistema"],
                                     "criado_em": ultima["criado_em"]} if ultima else None})
    lista.sort(key=lambda a: a["ultima"]["criado_em"] if a["ultima"] else "", reverse=True)
    return {"amigos": lista,
            "recebidos": [r["de"] for r in linhas if r["estado"] == "pedido" and r["para"] == mim],
            "enviados": [r["para"] for r in linhas if r["estado"] == "pedido" and r["de"] == mim]}


def _aceitar(db, de: str, para: str) -> None:
    db.execute("update amizades set estado = 'aceita' where de = ? and para = ?", (de, para))
    db.execute("insert into mensagens (de, para, texto, criado_em, sistema) values (?, ?, ?, ?, 1)",
               (para, de, "Agora vocês são amigos. Diga oi!", _agora()))


@router.post("/amigos")
def pedir(p: Pedido, mim: str = Depends(eu)):
    outro = _outro(p.apelido, mim)
    _limite(mim)
    with _db() as db:
        if _bloqueado(db, mim, outro):
            raise HTTPException(403, "Não foi possível mandar o pedido.")
        if _amigos(db, mim, outro):
            return {"estado": "aceita"}
        if db.execute("select 1 from amizades where de = ? and para = ?", (outro, mim)).fetchone():
            _aceitar(db, outro, mim)  # a outra pessoa já tinha pedido: viram amigos na hora
            return {"estado": "aceita"}
        db.execute("insert or ignore into amizades values (?, ?, 'pedido', ?)", (mim, outro, _agora()))
    return {"estado": "pedido"}


@router.post("/amigos/responder")
def responder(r: Resposta, mim: str = Depends(eu)):
    outro = _outro(r.apelido, mim)
    with _db() as db:
        if not db.execute("select 1 from amizades where de = ? and para = ? and estado = 'pedido'", (outro, mim)).fetchone():
            raise HTTPException(404, "Pedido não encontrado.")
        if r.aceitar:
            _aceitar(db, outro, mim)
        else:
            db.execute("delete from amizades where de = ? and para = ?", (outro, mim))
    return {"ok": True}


@router.post("/amigos/remover")
def remover(p: Pedido, mim: str = Depends(eu)):
    outro = _outro(p.apelido, mim)
    with _db() as db:
        db.execute("delete from amizades where (de = ? and para = ?) or (de = ? and para = ?)", (mim, outro, outro, mim))
    return {"ok": True}


@router.post("/bloquear")
def bloquear(p: Pedido, mim: str = Depends(eu)):
    outro = _outro(p.apelido, mim)
    with _db() as db:
        db.execute("insert or ignore into bloqueios values (?, ?)", (mim, outro))
        db.execute("delete from amizades where (de = ? and para = ?) or (de = ? and para = ?)", (mim, outro, outro, mim))
    return {"ok": True}


# ---------------------------------------------------------------- conversa
@router.get("/chat/novas")
def novas(mim: str = Depends(eu)):
    with _db() as db:
        n = db.execute("select count(*) from mensagens m where para = ? and lida = 0 and apagada = 0 and exists "
                       "(select 1 from amizades a where a.estado = 'aceita' and ((a.de = m.de and a.para = m.para) "
                       "or (a.de = m.para and a.para = m.de)))", (mim,)).fetchone()[0]
    return {"nao_lidas": n}


@router.get("/conversa/{apelido}")
def conversa(apelido: str, mim: str = Depends(eu)):
    outro = _outro(apelido, mim)
    with _db() as db:
        if not _amigos(db, mim, outro):
            raise HTTPException(403, "Vocês não são amigos no WishLens.")
        linhas = db.execute("select * from mensagens where apagada = 0 and ((de = ? and para = ?) or (de = ? and para = ?)) "
                            "order by id desc limit ?", (mim, outro, outro, mim, HISTORICO)).fetchall()
        db.execute("update mensagens set lida = 1 where de = ? and para = ? and lida = 0", (outro, mim))
    return {"mensagens": [_mensagem(r, mim) for r in reversed(linhas)]}


def _cartao(s, mim: str, id_captura: str) -> dict:
    """O cartão sai da captura gravada (sua e aceita), nunca do que o app manda: ninguém forja pontos."""
    todas = _capturas(s)
    linha = todas[(todas["id"] == id_captura) & (todas["usuario"] == mim)]
    if linha.empty:
        raise HTTPException(404, "Achado não encontrado.")
    tema = str(linha.iloc[0]["tema"])
    p = _pontuadas_aba(s, tema, todas) if tema in ABAS else _pontuadas(s, todas)
    r = p[p["id"] == id_captura]
    if r.empty or not bool(r.iloc[0]["aceita"]):
        raise HTTPException(400, "Só dá para compartilhar um achado que valeu pontos.")
    t = TODOS[tema]
    return {"tema": t.id, "nome": t.nome, "emoji": t.emoji, "cor": t.cor, "achado": str(r.iloc[0]["achado"]),
            "pontos": int(r.iloc[0]["pontos"]), "aba": tema if tema in ABAS else "livre"}


@router.post("/conversa/{apelido}")
def enviar(apelido: str, texto: str = Form("", max_length=500), captura: str | None = Form(None, max_length=40),
           foto: UploadFile | None = File(None), s=Depends(sessao), mim: str = Depends(eu)):
    outro = _outro(apelido, mim)
    texto = texto.strip()
    if not texto and foto is None and not captura:
        raise HTTPException(400, "Mensagem vazia.")
    with _db() as db:
        if not _amigos(db, mim, outro) or _bloqueado(db, mim, outro):
            raise HTTPException(403, "Vocês não são amigos no WishLens.")
    _limite(mim)
    cartao = json.dumps(_cartao(s, mim, captura), ensure_ascii=False) if captura else None
    nome_foto = None
    if foto is not None:
        dados = foto.file.read(FOTO_MAX + 1)
        if len(dados) > FOTO_MAX:
            raise HTTPException(413, "Foto grande demais (máximo 10 MB).")
        try:
            limpa = preparar_para_salvar(Image.open(io.BytesIO(dados)))  # sem EXIF nem GPS
        except (UnidentifiedImageError, OSError):
            raise HTTPException(400, "Não consegui abrir a foto.")
        nome_foto = uuid.uuid4().hex
        (DADOS / "fotos").mkdir(parents=True, exist_ok=True)
        (DADOS / "fotos" / f"{nome_foto}.jpg").write_bytes(limpa)
    with _db() as db:
        cur = db.execute("insert into mensagens (de, para, texto, foto, cartao, criado_em) values (?, ?, ?, ?, ?, ?)",
                         (mim, outro, texto, nome_foto, cartao, _agora()))
        r = db.execute("select * from mensagens where id = ?", (cur.lastrowid,)).fetchone()
    return _mensagem(r, mim)


@router.delete("/mensagem/{id_mensagem}")
def apagar(id_mensagem: int, mim: str = Depends(eu)):
    with _db() as db:
        r = db.execute("select * from mensagens where id = ? and de = ? and sistema = 0", (id_mensagem, mim)).fetchone()
        if r is None:
            raise HTTPException(404, "Mensagem não encontrada.")
        db.execute("update mensagens set apagada = 1, texto = '', cartao = null, foto = null where id = ?", (id_mensagem,))
    if r["foto"]:
        (DADOS / "fotos" / f"{r['foto']}.jpg").unlink(missing_ok=True)
    return {"ok": True}


class Denuncia(BaseModel):
    id: int
    motivo: str = Field("", max_length=300)


@router.post("/denunciar")
def denunciar(d: Denuncia, mim: str = Depends(eu)):
    with _db() as db:
        r = db.execute("select * from mensagens where id = ? and para = ?", (d.id, mim)).fetchone()
    if r is None:
        raise HTTPException(404, "Mensagem não encontrada.")
    gravar_aviso({"quando": _agora(), "apelido": mim, "tipo": "denuncia", "texto": d.motivo.strip(),
                  "denunciado": r["de"], "mensagem": r["texto"], "foto": r["foto"], "id_mensagem": r["id"]})
    return {"ok": True}


@router.get("/foto/{nome}")
def ver_foto(nome: str, mim: str = Depends(eu)):
    if not nome.isalnum():
        raise HTTPException(404, "Foto não encontrada.")
    with _db() as db:
        ok = db.execute("select 1 from mensagens where foto = ? and apagada = 0 and (de = ? or para = ?)",
                        (nome, mim, mim)).fetchone()
    caminho = DADOS / "fotos" / f"{nome}.jpg"
    if not ok or not caminho.exists():
        raise HTTPException(404, "Foto não encontrada.")
    return FileResponse(caminho, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
