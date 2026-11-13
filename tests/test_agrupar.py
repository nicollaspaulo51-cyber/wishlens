"""Decisão do CLIP no jogo (src/reconhecimento), sem torch: probabilidades falsas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_decidir_captura_sem_gemma():
    from src.reconhecimento import decidir_captura
    g = ["carros", "carros", "plantas", "tela", "nenhum"]
    tema, real, conf = decidir_captura(g, [0.4, 0.3, 0.1, 0.1, 0.1])
    assert (tema, real) == ("carros", True) and abs(conf - 0.4 / 0.7) < 1e-9  # melhor frase, não a soma
    assert decidir_captura(g, [0.2, 0.1, 0.0, 0.6, 0.1])[:2] == ("carros", False)  # carro na tela
    assert decidir_captura(g, [0.1, 0.1, 0.1, 0.1, 0.6])[:2] == (None, True)


def test_mais_frases_nao_ganham_por_quantidade():
    """Peças tem 11 frases; um mouse bate forte só em "a computer mouse" e tem de ganhar mesmo assim."""
    from src.reconhecimento import decidir_captura
    g = ["pecas"] * 11 + ["passaros"] * 6 + ["nenhum"]
    probs = [0.30] + [0.01] * 10 + [0.05] * 6 + [0.24]
    assert decidir_captura(g, probs)[0] == "pecas"
    # muitas frases fracas não somam para vencer uma frase forte de outro tema
    probs = [0.04] * 11 + [0.3] + [0.0] * 5 + [0.26]
    assert decidir_captura(g, probs)[0] == "passaros"


def test_monitor_ligado_nao_e_tela_de_trapaca():
    from src.reconhecimento import decidir_captura
    g = ["pecas", "carros", "tela", "nenhum"]
    assert decidir_captura(g, [0.4, 0.05, 0.45, 0.1])[:2] == ("pecas", True)
    assert decidir_captura(g, [0.05, 0.4, 0.45, 0.1])[:2] == ("carros", False)


def test_frases_dos_temas():
    from src.temas import FRASES_NENHUM, POR_ID, TEMAS
    assert all(len(t.frases_clip) >= 6 for t in TEMAS)
    assert any("mouse" in f for f in POR_ID["pecas"].frases_clip)
    assert not any("everyday" in f or "object" in f for f in FRASES_NENHUM)


def test_clip_da_nome_especifico_mouse_e_teclado():
    """Erro do teste no celular: sem Gemma, tudo do computador virava "peça de computador"."""
    from src.reconhecimento import achado_do_tema, frases_captura
    frases = frases_captura()
    def probs_para(objeto):
        return [0.9 if f == f"a photo of {objeto}" else 0.001 for _, f, _ in frases]
    assert achado_do_tema(frases, probs_para("a computer mouse"), "pecas") == "mouse"
    assert achado_do_tema(frases, probs_para("a computer keyboard"), "pecas") == "teclado"
    assert achado_do_tema(frases, probs_para("a flower"), "plantas") == "flor"


def test_frases_gemeas_de_tela():
    """Erro do teste no celular: pássaro na tela do computador foi aceito."""
    from src.reconhecimento import decidir_captura
    from src.temas import FRASES_TELA, TEMAS
    for t in TEMAS:
        if t.id == "pecas":
            continue
        for objeto, _ in t.objetos_clip:
            assert f"a photo of a computer screen showing {objeto}" in FRASES_TELA
    assert not any("computer mouse" in f for f in FRASES_TELA)  # monitor/mouse são peças, não "tela"
    # "pássaro na tela" mais parecido que "pássaro de verdade" -> não é foto real
    g = ["passaros", "tela", "nenhum"]
    assert decidir_captura(g, [0.35, 0.55, 0.10])[:2] == ("passaros", False)
