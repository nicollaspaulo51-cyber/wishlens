"""Tratamento das fotos: ler data/GPS do EXIF, reduzir tamanho e remover metadados.

Privacidade: a foto guardada NUNCA leva o EXIF (que pode conter a localização
exata da casa da pessoa). O GPS é usado só para buscar lugares próximos e para
descobrir cidade/bairro.
"""

from __future__ import annotations

import io
from datetime import datetime

from PIL import ExifTags, Image, ImageOps

LADO_MAXIMO = 1024


def _gps_para_decimal(valor, ref) -> float:
    graus, minutos, segundos = (float(x) for x in valor)
    decimal = graus + minutos / 60 + segundos / 3600
    return -decimal if ref in ("S", "W") else decimal


def ler_metadados(imagem: Image.Image) -> dict:
    """Extrai data/hora e latitude/longitude do EXIF, quando existirem."""
    exif = imagem.getexif()
    resultado: dict = {"data_hora": None, "lat": None, "lon": None}

    sub = exif.get_ifd(ExifTags.IFD.Exif)
    data = sub.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    if data:
        try:
            resultado["data_hora"] = datetime.strptime(str(data), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass

    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    try:
        resultado["lat"] = _gps_para_decimal(gps[2], gps[1])
        resultado["lon"] = _gps_para_decimal(gps[4], gps[3])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        pass
    return resultado


def preparar_para_salvar(imagem: Image.Image) -> bytes:
    """Gira conforme o EXIF, reduz para LADO_MAXIMO px e devolve JPEG SEM metadados."""
    img = ImageOps.exif_transpose(imagem).convert("RGB")
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    limpa = Image.new("RGB", img.size)
    limpa.paste(img)  # copia só os pixels, descartando EXIF/GPS
    buffer = io.BytesIO()
    limpa.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
