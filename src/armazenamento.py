"""Ponto único de acesso aos desejos. O app só importa este módulo.

Escolhe o backend automaticamente:
- **Supabase** (src/banco.py), quando `.streamlit/secrets.toml` tem SUPABASE_URL e SUPABASE_KEY,
  o pacote `supabase` está instalado e a pessoa fez login;
- **memória da sessão**, nos outros casos (some ao fechar o navegador).

Os dados de exemplo (usuários "exemplo:...") ficam sempre só na memória e nunca vão para o banco.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from src.categorias import Item, faixa_preco

COLUNAS = ["id", "usuario", "criado_em", "item", "categoria", "tipo",
           "faixa_preco", "confianca", "cidade", "acao", "marca"]
COLUNAS_CAPTURA = ["id", "usuario", "criado_em", "tema", "achado", "confianca", "foto_real",
                   "foto_hash", "cidade", "celula"]


# ---------------------------------------------------------------- backend
def _banco():
    """Retorna o cliente Supabase logado, ou None."""
    from src import banco
    return banco.sessao_atual()


def supabase_configurado() -> bool:
    from src import banco
    return banco.configurado()


def descricao_backend() -> str:
    if _banco():
        return "Supabase (salvo na nuvem)"
    if supabase_configurado():
        return "Supabase configurado: entre na sua conta para salvar"
    return "memória desta sessão (protótipo)"


# ---------------------------------------------------------------- memória
def _memoria() -> list[dict]:
    if "desejos" not in st.session_state:
        st.session_state.desejos = []
    return st.session_state.desejos


# ---------------------------------------------------------------- API usada pelo app
def usuario_atual() -> str:
    b = _banco()
    if b:
        return b.apelido
    return st.session_state.get("usuario", "eu")


def salvar_desejo(item: Item, confianca: float | None, criado_em: datetime | None,
                  cidade: str | None, acao: str = "salvou", faixa: str | None = None) -> None:
    registro = {
        "criado_em": criado_em or datetime.now(),
        "item": item.nome,
        "categoria": item.categoria,
        "tipo": item.tipo,
        "faixa_preco": faixa or faixa_preco(item),
        "confianca": confianca,
        "cidade": cidade,
        "acao": acao,
        "marca": item.marca or None,
    }
    b = _banco()
    if b:
        b.salvar_desejo(registro)
    else:
        _memoria().append({"id": str(uuid.uuid4()), "usuario": usuario_atual(), **registro})


def adicionar_varios(registros: list[dict]) -> None:
    """Só para dados de exemplo: ficam sempre na memória."""
    _memoria().extend(registros)


def todos() -> pd.DataFrame:
    linhas = list(_memoria())
    b = _banco()
    if b:
        linhas += b.desejos_visiveis()
    df = pd.DataFrame(linhas, columns=COLUNAS)
    if not df.empty:
        df["criado_em"] = pd.to_datetime(df["criado_em"], utc=True, format="mixed").dt.tz_convert(None)
    return df


def do_usuario(usuario: str) -> pd.DataFrame:
    df = todos()
    return df[df["usuario"] == usuario]


def remover_exemplos() -> None:
    st.session_state.desejos = [d for d in _memoria() if not str(d["usuario"]).startswith("exemplo:")]


# ---------------------------------------------------------------- capturas do jogo
def _capturas_memoria() -> list[dict]:
    if "capturas" not in st.session_state:
        st.session_state.capturas = []
    return st.session_state.capturas


def salvar_captura(tema: str | None, achado: str, confianca: float | None, foto_real: bool,
                   foto_hash: str | None, cidade: str | None, celula: str | None) -> None:
    """Guarda a captura crua; os pontos são sempre recalculados a partir delas (src/jogo.py)."""
    from src.jogo import agora_naive

    registro = {"criado_em": agora_naive(), "tema": tema or "nenhum", "achado": achado or "",
                "confianca": confianca, "foto_real": bool(foto_real), "foto_hash": foto_hash,
                "cidade": cidade, "celula": celula}
    b = _banco()
    if b:
        b.salvar_captura(registro)
    else:
        _capturas_memoria().append({"id": str(uuid.uuid4()), "usuario": usuario_atual(), **registro})


def adicionar_capturas(registros: list[dict]) -> None:
    """Só para dados de exemplo: ficam sempre na memória."""
    _capturas_memoria().extend(registros)


def capturas() -> pd.DataFrame:
    """Todas as capturas (memória + Supabase). criado_em fica no horário de Brasília, sem fuso."""
    from src.temas import FUSO

    linhas = list(_capturas_memoria())
    b = _banco()
    if b:
        linhas += b.capturas_todas()
    df = pd.DataFrame(linhas, columns=COLUNAS_CAPTURA)
    if not df.empty:
        datas = pd.to_datetime(df["criado_em"], format="mixed")
        if datas.dt.tz is None:  # memória: já está em Brasília
            df["criado_em"] = datas
        else:
            df["criado_em"] = datas.dt.tz_convert(FUSO).dt.tz_localize(None)
    return df


def remover_capturas_exemplo() -> None:
    st.session_state.capturas = [c for c in _capturas_memoria() if not str(c["usuario"]).startswith("exemplo:")]
