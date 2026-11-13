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
