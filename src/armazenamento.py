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
                   "foto_hash", "cidade", "celula",
                   # o que cada juiz disse (avaliação CLIP x Gemma) e a contestação da pessoa
                   "juiz", "clip_tema", "clip_foto_real", "clip_prob_tema", "clip_prob_tela", "contestada"]
COLUNAS_JUIZES = COLUNAS_CAPTURA[10:]


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
                   foto_hash: str | None, cidade: str | None, celula: str | None, **juizes) -> str:
    """Guarda a captura crua e devolve o id; os pontos são sempre recalculados a partir delas (src/jogo.py).

    `juizes`: juiz, clip_tema, clip_foto_real, clip_prob_tema, clip_prob_tela, contestada (opcionais).
    """
    from src.jogo import agora_naive

    registro = {"id": str(uuid.uuid4()), "criado_em": agora_naive(), "tema": tema or "nenhum",
                "achado": achado or "", "confianca": confianca, "foto_real": bool(foto_real),
                "foto_hash": foto_hash, "cidade": cidade, "celula": celula,
                **{k: juizes.get(k) for k in COLUNAS_JUIZES}}
    b = _banco()
    if b:
        b.salvar_captura(registro)
        st.session_state.pop("_cache_capturas", None)
    else:
        _capturas_memoria().append({"usuario": usuario_atual(), **registro})
    return registro["id"]


def contestar(id_captura: str, tema: str) -> None:
    """A pessoa diz que a foto recusada era de um tema. Não muda os pontos; serve para avaliar os juízes."""
    b = _banco()
    if b:
        b.contestar(id_captura, tema)
        st.session_state.pop("_cache_capturas", None)
        return
    for c in _capturas_memoria():
        if c.get("id") == id_captura:
            c["contestada"] = tema


def adicionar_capturas(registros: list[dict]) -> None:
    """Só para dados de exemplo: ficam sempre na memória."""
    _capturas_memoria().extend(registros)


CACHE_SEGUNDOS = 30


def _capturas_banco(b) -> list[dict]:
    """Capturas do Supabase, guardadas por 30 s na sessão (cada clique no Streamlit roda a página de novo)."""
    import time

    guardado = st.session_state.get("_cache_capturas")
    if guardado and time.monotonic() - guardado[0] < CACHE_SEGUNDOS:
        return guardado[1]
    linhas = b.capturas_todas()
    st.session_state["_cache_capturas"] = (time.monotonic(), linhas)
    return linhas


def capturas() -> pd.DataFrame:
    """Todas as capturas (memória + Supabase). criado_em fica no horário de Brasília, sem fuso."""
    from src.banco import para_brasilia

    linhas = list(_capturas_memoria())
    b = _banco()
    if b:
        linhas += _capturas_banco(b)
    df = pd.DataFrame(linhas, columns=COLUNAS_CAPTURA)
    if not df.empty:
        df["criado_em"] = pd.to_datetime([para_brasilia(x) for x in df["criado_em"]])
    return df


def manchas() -> pd.DataFrame:
    """Onde a turma achou coisas, por quadrado de ~500 m e tema, sem dizer quem: celula, tema, n, achados."""
    colunas = ["celula", "tema", "n", "achados"]
    linhas = []
    mem = pd.DataFrame(_capturas_memoria(), columns=COLUNAS_CAPTURA)
    mem = mem[mem["celula"].notna() & mem["foto_real"].astype(bool) & (mem["tema"] != "nenhum")]
    for (celula, tema), g in mem.groupby(["celula", "tema"]):
        linhas.append({"celula": celula, "tema": tema, "n": len(g),
                       "achados": list(g["achado"].value_counts(ascending=True).index[:3])})
    b = _banco()
    if b:
        try:
            linhas += b.manchas()
        except Exception:  # banco criado antes da função manchas_capturas: o mapa fica sem as manchas
            pass
    return pd.DataFrame(linhas, columns=colunas)


def remover_capturas_exemplo() -> None:
    st.session_state.capturas = [c for c in _capturas_memoria() if not str(c["usuario"]).startswith("exemplo:")]
