"""Exportação anonimizada dos desejos, para a análise e para versionar no GitHub.

Remove tudo o que identifica alguém: nome de usuário vira código (u01, u02...),
saem o id do registro e o caminho da foto, a hora é arredondada e a localização
fica só no nível de cidade.
"""

from __future__ import annotations

import pandas as pd

REMOVER = ["id", "foto_url", "foto_path", "lat", "lon", "bairro", "usuario_id"]


def anonimizar(df: pd.DataFrame) -> pd.DataFrame:
    saida = df.drop(columns=[c for c in REMOVER if c in df.columns]).copy()
    codigos = {u: f"u{i:02d}" for i, u in enumerate(sorted(saida["usuario"].unique()), start=1)}
    saida["usuario"] = saida["usuario"].map(codigos)
    if "criado_em" in saida:
        saida["criado_em"] = pd.to_datetime(saida["criado_em"]).dt.floor("h")
    if "cidade" in saida:
        # "Jardim da Penha, Vitória - ES" -> "Vitória - ES" (descarta o bairro)
        saida["cidade"] = saida["cidade"].astype("string").str.split(",").str[-1].str.strip()
    return saida.sort_values(["usuario", "criado_em"]).reset_index(drop=True)
