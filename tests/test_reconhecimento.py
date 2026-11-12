"""Teste do CLIP: lento (baixa ~600 MB na 1ª vez). Pulado se torch/transformers não estiverem instalados."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from PIL import Image

from src.reconhecimento import reconhecer


def test_reconhecer_top3():
    resultados = reconhecer(Image.new("RGB", (224, 224), "white"), top_k=3)
    assert len(resultados) == 3
    confs = [r.confianca for r in resultados]
    assert confs == sorted(confs, reverse=True) and 0 < sum(confs) <= 1.0001
