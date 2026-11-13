"""CLIP real: lento (baixa ~600 MB na 1ª vez). Pulado se torch/transformers não estiverem instalados
ou se o modelo não puder ser baixado (ex.: sem internet)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from PIL import Image

from src import reconhecimento


@pytest.fixture(scope="module")
def modelo():
    try:
        return reconhecimento._carregar()
    except OSError as erro:  # sem acesso ao Hugging Face
        pytest.skip(f"modelo do CLIP indisponível: {erro}")


def test_julgar_clip_devolve_probabilidades(modelo):
    j = reconhecimento.julgar_clip(Image.new("RGB", (224, 224), "white"))
    assert abs(sum(j["probs"].values()) - 1) < 1e-6
    assert set(j["probs"]) >= {"tela", "nenhum", "carros", "pecas"}



def test_nitidez_cai_com_o_borrado():
    from PIL import Image, ImageDraw, ImageFilter

    from src.reconhecimento import nitidez

    img = Image.new("RGB", (800, 600), "white")
    d = ImageDraw.Draw(img)
    for k in range(40):
        d.rectangle((k * 20, (k * 37) % 560, k * 20 + 10, (k * 37) % 560 + 30), fill=(k * 6, 90, 200 - k * 4))
    assert nitidez(img) > 3 * nitidez(img.filter(ImageFilter.GaussianBlur(6)))


def test_so_pede_outra_foto_se_borrada_e_em_duvida():
    from src.reconhecimento import nao_identificou

    assert nao_identificou(5, 0.35)
    assert not nao_identificou(5, 0.8)      # borrada, mas o CLIP tem certeza: vale
    assert not nao_identificou(80, 0.35)    # nítida em dúvida: segue a regra normal (ex.: "nenhum tema")
