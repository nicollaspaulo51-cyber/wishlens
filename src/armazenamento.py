"""Onde os desejos ficam guardados.

Por enquanto, na memória da sessão do Streamlit (some ao fechar o navegador).
Na próxima etapa, as mesmas funções passarão a gravar no Supabase.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from src.categorias import FAIXA_PRECO, Item

COLUNAS = ["id", "usuario", "criado_em", "item", "categoria", "tipo",
           "faixa_preco", "confianca", "cidade", "acao"]


def _tabela() -> list[dict]:
    if "desejos" not in st.session_state:
        st.session_state.desejos = []
    return st.session_state.desejos


def usuario_atual() -> str:
    return st.session_state.get("usuario", "eu")


def salvar_desejo(item: Item, confianca: float | None, criado_em: datetime | None,
                  cidade: str | None, acao: str = "salvou") -> None:
    _tabela().append({
        "id": str(uuid.uuid4()),
        "usuario": usuario_atual(),
        "criado_em": criado_em or datetime.now(),
        "item": item.nome,
        "categoria": item.categoria,
        "tipo": item.tipo,
        "faixa_preco": FAIXA_PRECO.get(item.categoria, "—"),
        "confianca": confianca,
        "cidade": cidade,
        "acao": acao,
    })


def adicionar_varios(registros: list[dict]) -> None:
    _tabela().extend(registros)


def todos() -> pd.DataFrame:
    df = pd.DataFrame(_tabela(), columns=COLUNAS)
    if not df.empty:
        df["criado_em"] = pd.to_datetime(df["criado_em"])
    return df


def do_usuario(usuario: str) -> pd.DataFrame:
    df = todos()
    return df[df["usuario"] == usuario]


def remover_exemplos() -> None:
    st.session_state.desejos = [d for d in _tabela() if not d["usuario"].startswith("exemplo:")]
