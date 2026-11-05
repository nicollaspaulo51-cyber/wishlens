"""Perfil de desejos e comparação entre pessoas (similaridade do cosseno)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.categorias import CATEGORIAS


def vetor_perfil(df: pd.DataFrame) -> pd.Series:
    """Proporção de desejos em cada categoria (soma 1). Mesma ordem para todos."""
    contagem = df["categoria"].value_counts().reindex(CATEGORIAS, fill_value=0)
    total = contagem.sum()
    return contagem / total if total else contagem.astype(float)


def similaridade_cosseno(a: pd.Series, b: pd.Series) -> float:
    va, vb = a.to_numpy(float), b.to_numpy(float)
    norma = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(va @ vb / norma) if norma else 0.0


def sugestoes(meu: pd.DataFrame, outro: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Itens que a outra pessoa deseja e eu ainda não."""
    novos = outro[~outro["item"].isin(meu["item"])]
    return (novos.groupby(["item", "categoria", "tipo"]).size()
            .rename("vezes").reset_index()
            .sort_values("vezes", ascending=False).head(n))
