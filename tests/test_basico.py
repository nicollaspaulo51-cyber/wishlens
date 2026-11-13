"""Testes básicos: foto sem EXIF, distância, perfil, nomes digitados e imports do app."""

import ast
import importlib
import importlib.util
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from src.fotos import ler_metadados, preparar_para_salvar
from src.lugares import distancia_km

RAIZ = Path(__file__).resolve().parents[1]


def test_foto_sem_exif_e_reduzida():
    img = Image.new("RGB", (4000, 3000), "red")
    exif = img.getexif()
    exif[0x0132] = "2026:11:05 12:00:00"  # DateTime
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    original = Image.open(io.BytesIO(buf.getvalue()))
    assert ler_metadados(original)["data_hora"].year == 2026

    limpa = Image.open(io.BytesIO(preparar_para_salvar(original)))
    assert max(limpa.size) == 1024
    assert len(limpa.getexif()) == 0


def test_distancia():
    # Vitória -> Vila Velha: poucos km
    d = distancia_km(-20.3155, -40.3128, -20.3297, -40.2925)
    assert 1 < d < 10


def test_similaridade_cosseno():
    import pandas as pd
    from src.perfil import similaridade_cosseno, vetor_perfil
    a = vetor_perfil(pd.DataFrame({"categoria": ["comida", "comida", "animais"]}))
    b = vetor_perfil(pd.DataFrame({"categoria": ["comida", "comida", "animais"] * 3}))
    c = vetor_perfil(pd.DataFrame({"categoria": ["eletrônicos"]}))
    assert abs(similaridade_cosseno(a, b) - 1) < 1e-9   # mesmo perfil -> 100%
    assert similaridade_cosseno(a, c) == 0               # nada em comum -> 0%


def test_nome_digitado():
    from src.categorias import nome_valido
    assert nome_valido("garrafa térmica") and nome_valido("fone JBL (azul)")
    assert not nome_valido("<img src=x>") and not nome_valido('a"b') and not nome_valido("")
    assert not nome_valido("x" * 61)


def test_todos_os_modulos_e_paginas_carregam():
    """Nenhum import quebrado depois de tirar a parte de compras."""
    for arquivo in sorted((RAIZ / "src").glob("*.py")):
        if arquivo.stem != "__init__":
            importlib.import_module(f"src.{arquivo.stem}")
    paginas = [RAIZ / "app" / "Home.py", *sorted((RAIZ / "app" / "pages").glob("*.py"))]
    assert [p.name for p in paginas] == ["Home.py", "1_Pódio.py", "2_Minha_Coleção.py", "3_Avaliação.py"]
    for pagina in paginas:
        arvore = ast.parse(pagina.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.module and no.module.startswith("src"):
                modulo = importlib.import_module(no.module)
                for nome in no.names:
                    assert hasattr(modulo, nome.name), f"{pagina.name}: {no.module}.{nome.name} não existe"
    for removido in ("links", "precos", "feed"):
        assert importlib.util.find_spec(f"src.{removido}") is None
