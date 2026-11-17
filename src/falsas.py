"""Fotos falsas e "fotos de celular" geradas por programa, para treinar o juiz (src/treino_juiz.py).

- na_tela: a foto aparecendo num celular, monitor ou TV (moldura, cores lavadas, moiré, reflexo, perspectiva);
- impressa: a foto num papel (retícula de impressão, margem, sombra, dobra, perspectiva);
- como_celular: o que a câmera do celular faz com uma foto real (recorte, giro, borrão leve, luz, JPEG).

Imperfeito de propósito: o objetivo é ensinar os sinais que separam "o objeto na frente da câmera" de
"uma imagem do objeto", não imitar um aparelho exato. Só PIL + numpy, com sorteio controlado (rng).
"""

from __future__ import annotations

import io
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

LADO = 512


def _fundo(rng: random.Random, tamanho: tuple[int, int]) -> Image.Image:
    """Mesa, parede ou sala desfocada: um degradê com ruído (o que aparece em volta da tela ou do papel)."""
    w, h = tamanho
    a = np.array([rng.randint(20, 200) for _ in range(3)], dtype=np.float32)
    b = np.clip(a + np.array([rng.randint(-60, 60) for _ in range(3)]), 0, 255)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    img = a * (1 - t) + b * t + np.random.default_rng(rng.randint(0, 2**31)).normal(0, 6, (h, w, 3))
    return Image.fromarray(np.clip(np.broadcast_to(img, (h, w, 3)), 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(3))


def _perspectiva(img: Image.Image, rng: random.Random, forca: float = 0.12) -> Image.Image:
    """Inclina como se a câmera estivesse de lado: cada canto anda um pouco."""
    w, h = img.size
    d = lambda n: rng.uniform(-forca, forca) * n  # noqa: E731
    origem = [(d(w), d(h)), (w + d(w), d(h)), (w + d(w), h + d(h)), (d(w), h + d(h))]
    destino = [(0, 0), (w, 0), (w, h), (0, h)]
    # coeficientes da transformação de perspectiva que leva destino -> origem
    m = []
    for (x, y), (u, v) in zip(destino, origem):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    coef = np.linalg.solve(np.array(m, dtype=np.float64), np.array([c for p in origem for c in p], dtype=np.float64))
    return img.transform((w, h), Image.Transform.PERSPECTIVE, tuple(coef), Image.Resampling.BICUBIC)


def _moire(tamanho: tuple[int, int], rng: random.Random) -> np.ndarray:
    """Listras onduladas que aparecem ao fotografar a grade de pixels de uma tela."""
    w, h = tamanho
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = rng.uniform(0, np.pi)
    freq = rng.uniform(0.15, 0.6)
    onda = np.sin((x * np.cos(ang) + y * np.sin(ang)) * freq + 3 * np.sin(y * rng.uniform(0.01, 0.04)))
    return 1 + rng.uniform(0.04, 0.12) * onda[..., None]


def na_tela(foto: Image.Image, rng: random.Random) -> Image.Image:
    foto = foto.convert("RGB")
    tipo = rng.choice(["celular", "monitor", "tv"])
    tela_w = LADO if tipo != "celular" else int(LADO * 0.55)
    tela_h = int(tela_w * (0.62 if tipo != "celular" else 2.0))
    if tipo == "celular":
        tela_h = min(tela_h, int(LADO * 0.95))
    conteudo = foto.copy()
    conteudo.thumbnail((tela_w, tela_h))
    tela = Image.new("RGB", (tela_w, tela_h), (0, 0, 0))
    tela.paste(conteudo, ((tela_w - conteudo.width) // 2, (tela_h - conteudo.height) // 2))
    if rng.random() < 0.5:  # barra de aplicativo/navegador em cima
        ImageDraw.Draw(tela).rectangle((0, 0, tela_w, int(tela_h * rng.uniform(0.04, 0.09))),
                                       fill=tuple(rng.randint(200, 255) for _ in range(3)))
    # tela fotografada: cores lavadas, preto vira cinza, puxado para o azul
    arr = np.asarray(tela, dtype=np.float32) / 255
    arr = 0.08 + 0.84 * arr ** rng.uniform(0.8, 1.1)
    arr *= np.array([rng.uniform(0.9, 1.0), rng.uniform(0.95, 1.02), rng.uniform(1.0, 1.1)])
    arr *= _moire((tela_w, tela_h), rng)
    # reflexo de luz
    y, x = np.mgrid[0:tela_h, 0:tela_w].astype(np.float32)
    cx, cy = rng.uniform(0, tela_w), rng.uniform(0, tela_h)
    arr += rng.uniform(0.05, 0.35) * np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (2 * (tela_w * rng.uniform(0.15, 0.4)) ** 2)))[..., None]
    tela = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))

    borda = rng.randint(8, 22) if tipo == "celular" else rng.randint(10, 30)
    aparelho = Image.new("RGB", (tela_w + 2 * borda, tela_h + 2 * borda), tuple([rng.randint(5, 40)] * 3))
    aparelho.paste(tela, (borda, borda))
    cena = _fundo(rng, (int(aparelho.width * rng.uniform(1.05, 1.4)), int(aparelho.height * rng.uniform(1.05, 1.4))))
    cena.paste(aparelho, ((cena.width - aparelho.width) // 2, (cena.height - aparelho.height) // 2))
    if rng.random() < 0.4:  # foto de perto: só um pedaço da tela, sem a moldura
        m = rng.uniform(0.2, 0.35)
        cena = cena.crop((int(cena.width * m), int(cena.height * m), int(cena.width * (1 - m)), int(cena.height * (1 - m))))
    cena.thumbnail((LADO, LADO))
    return _perspectiva(cena, rng)


def impressa(foto: Image.Image, rng: random.Random) -> Image.Image:
    foto = foto.convert("RGB")
    foto.thumbnail((int(LADO * 0.8), int(LADO * 0.8)))
    # retícula de impressão: pontinhos regulares e menos saturação
    arr = np.asarray(ImageEnhance.Color(foto).enhance(rng.uniform(0.6, 0.9)), dtype=np.float32) / 255
    y, x = np.mgrid[0:foto.height, 0:foto.width].astype(np.float32)
    passo = rng.uniform(2.5, 4.5)
    pontos = (np.sin(x * 2 * np.pi / passo) * np.sin(y * 2 * np.pi / passo))[..., None]
    arr = np.clip(arr + 0.06 * pontos, 0, 1)
    arr = 0.06 + 0.86 * arr  # papel não tem preto nem branco puros
    impressao = Image.fromarray((arr * 255).astype(np.uint8))
    margem = rng.randint(10, 40)
    papel = Image.new("RGB", (impressao.width + 2 * margem, impressao.height + 2 * margem),
                      (rng.randint(225, 250), rng.randint(220, 245), rng.randint(205, 235)))
    papel.paste(impressao, (margem, margem))
    if rng.random() < 0.5:  # texto de revista/livro embaixo
        d = ImageDraw.Draw(papel)
        for k in range(rng.randint(1, 3)):
            yy = papel.height - margem // 2 - 6 * k
            d.line((margem, yy, papel.width - margem - rng.randint(0, 60), yy), fill=(60, 60, 60), width=2)
    # sombra de luz e dobra
    pa = np.asarray(papel, dtype=np.float32)
    t = np.linspace(rng.uniform(0.7, 1.0), rng.uniform(0.85, 1.05), papel.width, dtype=np.float32)[None, :, None]
    pa *= t
    if rng.random() < 0.5:
        col = rng.randint(papel.width // 4, 3 * papel.width // 4)
        pa[:, col:col + 3] *= 0.8
    papel = Image.fromarray(np.clip(pa, 0, 255).astype(np.uint8))
    cena = _fundo(rng, (int(papel.width * rng.uniform(1.05, 1.3)), int(papel.height * rng.uniform(1.05, 1.3))))
    cena.paste(papel, ((cena.width - papel.width) // 2, (cena.height - papel.height) // 2))
    cena.thumbnail((LADO, LADO))
    return _perspectiva(cena, rng, 0.08)


def como_celular(foto: Image.Image, rng: random.Random) -> Image.Image:
    """Recorte, giro, luz, borrão leve e JPEG: a mesma foto como sairia de câmeras diferentes."""
    img = foto.convert("RGB")
    w, h = img.size
    f = rng.uniform(0.7, 1.0)
    x0, y0 = rng.uniform(0, w * (1 - f)), rng.uniform(0, h * (1 - f))
    img = img.crop((int(x0), int(y0), int(x0 + w * f), int(y0 + h * f)))
    img = img.rotate(rng.uniform(-12, 12), resample=Image.Resampling.BICUBIC, expand=False)
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.75, 1.25))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.2))
    if rng.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.2)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=rng.randint(50, 92))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
