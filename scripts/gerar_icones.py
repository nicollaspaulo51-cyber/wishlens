"""Gera os ícones do app (app_celular/assets): lupa laranja de sinalização sobre tinta, com curvas de nível leves.

Rodar da raiz do repositório: python scripts/gerar_icones.py  (só precisa do Pillow)
"""

from pathlib import Path

from PIL import Image, ImageDraw

TINTA = (25, 29, 27, 255)       # #191D1B (cores.ts, tinta do tema claro)
LARANJA = (226, 88, 11, 255)    # #E2580B
CURVA = (255, 255, 255, 22)     # curvas de nível quase invisíveis
PASTA = Path(__file__).resolve().parents[1] / "app_celular" / "assets"
L = 1024
E = 4  # desenha 4x maior e reduz: bordas suaves


def lupa(d: ImageDraw.ImageDraw, cor, escala: float = 1.0) -> None:
    """Aro + cabo, centrados no quadro de 1024 (em coordenadas já multiplicadas por E)."""
    s = escala * E
    cx, cy, r, w = 455, 455, 210, 70
    c = lambda v, o: (o + (v - o) * escala) * E  # escala em volta do centro do quadro
    x, y = c(cx, 512), c(cy, 512)
    d.ellipse([x - r * s, y - r * s, x + r * s, y + r * s], outline=cor, width=int(w * s))
    # cabo a 45°, saindo do aro
    a = r * 0.7071 * s
    b = (r + 230) * 0.7071 * s
    d.line([x + a, y + a, x + b, y + b], fill=cor, width=int(w * 1.15 * s))
    d.ellipse([x + b - w * 0.575 * s, y + b - w * 0.575 * s, x + b + w * 0.575 * s, y + b + w * 0.575 * s], fill=cor)


def curvas(d: ImageDraw.ImageDraw) -> None:
    for i, r in enumerate(range(140, 1500, 110)):
        cx, cy = 820 * E, 900 * E
        rr = r * E
        d.ellipse([cx - rr * 1.25, cy - rr, cx + rr * 1.25, cy + rr], outline=CURVA, width=6 * E)


def quadro(fundo, *camadas) -> Image.Image:
    """Cada camada é desenhada à parte e misturada por cima (o ImageDraw sozinho não mistura a transparência)."""
    im = Image.new("RGBA", (L * E, L * E), fundo)
    for desenho in camadas:
        camada = Image.new("RGBA", im.size, (0, 0, 0, 0))
        desenho(ImageDraw.Draw(camada))
        im = Image.alpha_composite(im, camada)
    return im.resize((L, L), Image.LANCZOS)


def main() -> None:
    icone = quadro(TINTA, curvas, lambda d: lupa(d, LARANJA))
    icone.convert("RGB").save(PASTA / "icon.png")
    icone.resize((48, 48), Image.LANCZOS).save(PASTA / "favicon.png")
    # Android adaptativo: a área segura é o círculo central de ~66%, então a lupa encolhe
    quadro((0, 0, 0, 0), lambda d: lupa(d, LARANJA, 0.62)).save(PASTA / "android-icon-foreground.png")
    quadro(TINTA, curvas).convert("RGB").save(PASTA / "android-icon-background.png")
    quadro((0, 0, 0, 0), lambda d: lupa(d, (255, 255, 255, 255), 0.62)).save(PASTA / "android-icon-monochrome.png")
    quadro((0, 0, 0, 0), lambda d: lupa(d, LARANJA, 0.8)).save(PASTA / "splash-icon.png")


if __name__ == "__main__":
    main()
