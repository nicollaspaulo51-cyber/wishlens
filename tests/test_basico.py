"""Testes que rodam sem internet: python -m pytest tests/"""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from src.categorias import FAIXA_PRECO, ITENS
from src.fotos import ler_metadados, preparar_para_salvar
from src.links import links_para
from src.lugares import TAGS_POR_CATEGORIA, distancia_km, montar_consulta


def test_catalogo_consistente():
    assert len({i.rotulo_en for i in ITENS}) == len(ITENS)
    for i in ITENS:
        assert i.tipo in {"comprar", "receita", "adotar"}
        assert i.categoria in FAIXA_PRECO
        assert i.categoria in TAGS_POR_CATEGORIA
        assert links_para(i)


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


def test_distancia_e_consulta():
    # Vitória -> Vila Velha: poucos km
    d = distancia_km(-20.3155, -40.3128, -20.3297, -40.2925)
    assert 1 < d < 10
    q = montar_consulta(ITENS[-1], -20.3, -40.3, 2000)
    assert "animal_shelter" in q or "pet" in q


def test_similaridade_cosseno():
    import pandas as pd
    from src.perfil import similaridade_cosseno, vetor_perfil
    a = vetor_perfil(pd.DataFrame({"categoria": ["comida", "comida", "animais"]}))
    b = vetor_perfil(pd.DataFrame({"categoria": ["comida", "comida", "animais"] * 3}))
    c = vetor_perfil(pd.DataFrame({"categoria": ["eletrônicos"]}))
    assert abs(similaridade_cosseno(a, b) - 1) < 1e-9   # mesmo perfil -> 100%
    assert similaridade_cosseno(a, c) == 0               # nada em comum -> 0%
