"""Acesso ao Supabase (banco PostgreSQL + login). Usado por src/armazenamento.py.

Nada aqui é obrigatório: sem as chaves em `.streamlit/secrets.toml` ou sem o pacote
`supabase` instalado, o app continua funcionando em memória.

Estrutura das tabelas: supabase/schema.sql. Passo a passo: docs/SUPABASE.md.

ATENÇÃO: este módulo ainda não foi testado contra um projeto Supabase real.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from datetime import datetime

import streamlit as st

_CHAVE_SESSAO = "_wl_supabase"


# Colunas com a opinião de cada juiz (CLIP x Gemma); bancos antigos não as têm
COLUNAS_JUIZES_BANCO = ("juiz", "clip_tema", "clip_foto_real", "clip_prob_tema", "clip_prob_tela", "contestada")


def para_brasilia(valor) -> datetime:
    """Texto ISO do banco (com fuso) -> datetime no horário de Brasília, sem fuso."""
    from src.temas import FUSO

    momento = valor if isinstance(valor, datetime) else datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO).replace(tzinfo=None)
    return momento


def _segredos() -> tuple[str, str] | None:
    try:
        url, chave = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    except (KeyError, FileNotFoundError, AttributeError):
        return None
    except Exception:  # st.secrets lança erros próprios quando não há secrets.toml
        return None
    return (url, chave) if url and chave else None


def configurado() -> bool:
    return _segredos() is not None and importlib.util.find_spec("supabase") is not None


def _novo_cliente():
    from supabase import create_client
    url, chave = _segredos()
    return create_client(url, chave)


@dataclass
class Sessao:
    cliente: object
    usuario_id: str
    apelido: str

    # ------------------------------------------------ desejos
    def salvar_desejo(self, registro: dict) -> None:
        dados = {**registro, "usuario_id": self.usuario_id,
                 "criado_em": registro["criado_em"].isoformat()}
        try:
            self.cliente.table("desejos").insert(dados).execute()
        except Exception as erro:
            # banco criado antes da coluna "marca" (supabase/schema.sql): salva sem ela
            if "marca" not in str(erro):
                raise
            dados.pop("marca", None)
            self.cliente.table("desejos").insert(dados).execute()

    def desejos_visiveis(self) -> list[dict]:
        """Os próprios desejos + os de conexões aceitas (a RLS do banco garante isso)."""
        resp = (self.cliente.table("desejos")
                .select("id, criado_em, item, categoria, tipo, faixa_preco, confianca, cidade, acao, perfis(apelido)")
                .order("criado_em", desc=True).limit(5000).execute())
        linhas = []
        for r in resp.data or []:
            apelido = (r.pop("perfis", None) or {}).get("apelido", "?")
            linhas.append({**r, "usuario": apelido})
        return linhas

    # ------------------------------------------------ capturas do jogo
    def salvar_captura(self, registro: dict) -> None:
        from src.temas import FUSO
        criado = registro["criado_em"].replace(tzinfo=FUSO)  # horário de Brasília -> com fuso
        dados = {**registro, "usuario_id": self.usuario_id, "criado_em": criado.isoformat()}
        # returning="minimal": a API não pode devolver a linha, porque bairro e célula não são legíveis
        try:
            self.cliente.table("capturas").insert(dados, returning="minimal").execute()
        except Exception as erro:
            # banco criado antes das colunas dos juízes (supabase/schema.sql): salva sem elas
            if not any(c in str(erro) for c in COLUNAS_JUIZES_BANCO):
                raise
            for c in COLUNAS_JUIZES_BANCO:
                dados.pop(c, None)
            self.cliente.table("capturas").insert(dados, returning="minimal").execute()

    def capturas_todas(self) -> list[dict]:
        """Capturas de todos os jogadores (pódio e raridade), sem bairro nem célula (privacidade).

        O Supabase devolve no máximo 1.000 linhas por pedido: busca em páginas até acabar.
        criado_em sai no horário de Brasília sem fuso, igual às capturas em memória.
        """
        colunas = "id, criado_em, tema, achado, confianca, foto_real, foto_hash, " + ", ".join(COLUNAS_JUIZES_BANCO)
        linhas, inicio, pagina = [], 0, 1000
        while True:
            try:
                resp = (self.cliente.table("capturas").select(f"{colunas}, perfis(apelido)")
                        .order("criado_em").range(inicio, inicio + pagina - 1).execute())
            except Exception as erro:
                if colunas.endswith("foto_hash") or not any(c in str(erro) for c in COLUNAS_JUIZES_BANCO):
                    raise
                colunas = "id, criado_em, tema, achado, confianca, foto_real, foto_hash"  # banco antigo
                continue
            dados = resp.data or []
            for r in dados:
                apelido = (r.pop("perfis", None) or {}).get("apelido", "?")
                linhas.append({**r, "usuario": apelido, "criado_em": para_brasilia(r["criado_em"])})
            if len(dados) < pagina:
                return linhas
            inicio += pagina

    def contestar(self, id_captura: str, tema: str) -> None:
        """Só a coluna "contestada" da própria captura pode ser alterada (RLS + grant no schema)."""
        (self.cliente.table("capturas").update({"contestada": tema}, returning="minimal")
         .eq("id", id_captura).execute())

    def manchas(self) -> list[dict]:
        """Onde a turma achou coisas: por quadrado de ~500 m e tema, sem dizer quem (função no banco)."""
        return self.cliente.rpc("manchas_capturas", {}).execute().data or []

    # ------------------------------------------------ conexões (comparar)
    def pedir_conexao(self, apelido: str) -> None:
        alvo = self.cliente.table("perfis").select("id").eq("apelido", apelido).single().execute()
        self.cliente.table("conexoes").insert(
            {"solicitante": self.usuario_id, "destinatario": alvo.data["id"]}).execute()

    def aceitar_conexao(self, solicitante_id: str) -> None:
        (self.cliente.table("conexoes").update({"aceito": True})
         .eq("solicitante", solicitante_id).eq("destinatario", self.usuario_id).execute())

    def pedidos_pendentes(self) -> list[dict]:
        resp = (self.cliente.table("conexoes").select("solicitante, perfis!conexoes_solicitante_fkey(apelido)")
                .eq("destinatario", self.usuario_id).eq("aceito", False).execute())
        return resp.data or []


def sessao_atual() -> Sessao | None:
    return st.session_state.get(_CHAVE_SESSAO)


def entrar(email: str, senha: str) -> Sessao:
    cliente = _novo_cliente()
    auth = cliente.auth.sign_in_with_password({"email": email, "password": senha})
    uid = auth.user.id
    perfil = cliente.table("perfis").select("apelido").eq("id", uid).single().execute()
    sessao = Sessao(cliente, uid, perfil.data["apelido"])
    st.session_state[_CHAVE_SESSAO] = sessao
    return sessao


def cadastrar(email: str, senha: str, apelido: str) -> None:
    """Cria a conta. O perfil (apelido) é criado no banco por um gatilho (ver schema.sql)."""
    cliente = _novo_cliente()
    auth = cliente.auth.sign_up({"email": email, "password": senha,
                                 "options": {"data": {"apelido": apelido}}})
    if auth.user is None:
        raise RuntimeError("Não foi possível criar a conta.")


def sair() -> None:
    sessao = st.session_state.pop(_CHAVE_SESSAO, None)
    if sessao:
        sessao.cliente.auth.sign_out()
