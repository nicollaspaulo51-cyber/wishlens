"""Onde procurar cada tema do jogo: lugares do OpenStreetMap (Overpass API, dados abertos ODbL)."""

from __future__ import annotations

import math
import re

import requests

# Servidores públicos do Overpass, tentados em ordem (o primeiro às vezes fica sobrecarregado)
OVERPASS_URLS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "WishLens/0.1 (projeto academico de Ciencia de Dados)"

def distancia_km(lat1, lon1, lat2, lon2) -> float:
    """Distância em linha reta (fórmula de Haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _ancorado(filtro: str) -> str:
    """shop~"car|motorcycle" casaria carpet e car_repair: o valor tem de ser exatamente um da lista."""
    chave, sep, valores = re.split(r"([~=])", filtro, maxsplit=1)
    return f'{chave}~"^({valores.strip(chr(34))})$"' if sep == "~" else filtro


def _site(url: str | None) -> str | None:
    """Só aceita http(s): o valor vem do OSM, que qualquer pessoa edita."""
    if not url:
        return None
    url = url.strip().split(";")[0].strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url if re.fullmatch(r"[\w.-]+\.[a-z]{2,}(/\S*)?", url, re.I) else ""
    return url or None


def _telefone(valor: str | None) -> str | None:
    if not valor:
        return None
    valor = valor.split(";")[0].strip()
    return valor if re.fullmatch(r"[+\d ()./-]{6,25}", valor) else None


def detalhes_osm(tags: dict) -> dict:
    """Endereço, horário, telefone e site a partir das tags do OSM (Overpass ou extratags do Nominatim)."""
    rua = tags.get("addr:street")
    numero = tags.get("addr:housenumber")
    bairro = tags.get("addr:suburb") or tags.get("addr:neighbourhood")
    cidade = tags.get("addr:city")
    endereco = ", ".join(x for x in (" ".join(y for y in (rua, numero) if y) if rua else None, bairro, cidade) if x)
    return {
        "endereco": endereco or None,
        "horario": tags.get("opening_hours"),
        "telefone": _telefone(tags.get("phone") or tags.get("contact:phone")),
        "site": _site(tags.get("website") or tags.get("contact:website")),
    }


_DIAS = {"Mo": "seg", "Tu": "ter", "We": "qua", "Th": "qui", "Fr": "sex", "Sa": "sáb", "Su": "dom",
         "PH": "feriados"}


def horario_legivel(horario: str | None) -> str | None:
    """"Mo-Fr 09:00-18:00; Sa 09:00-13:00" -> "seg–sex 09:00–18:00 · sáb 09:00–13:00"."""
    if not horario:
        return None
    if horario.strip() == "24/7":
        return "24 horas, todos os dias"
    texto = re.sub(r"\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b", lambda m: _DIAS[m.group(1)], horario)
    texto = re.sub(r"\boff\b|\bclosed\b", "fechado", texto)
    texto = re.sub(r"(\d)-(\d)", r"\1–\2", texto).replace("-", "–")
    return " · ".join(p.strip() for p in texto.split(";") if p.strip())


def lugar_mais_proximo(lugares: list[dict], lat: float, lon: float, tolerancia: float = 1e-4) -> dict | None:
    """O lugar clicado no mapa (o folium devolve só a coordenada do marcador)."""
    if not lugares or lat is None or lon is None:
        return None
    melhor = min(lugares, key=lambda l: (l["lat"] - lat) ** 2 + (l["lon"] - lon) ** 2)
    perto = abs(melhor["lat"] - lat) <= tolerancia and abs(melhor["lon"] - lon) <= tolerancia
    return melhor if perto else None


def como_chegar(lat: float, lon: float) -> dict[str, str]:
    """Links de rota até o lugar (abrem o app instalado no celular)."""
    return {
        "Google Maps": f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}",
        "Waze": f"https://waze.com/ul?ll={lat},{lon}&navigate=yes",
        "OpenStreetMap": f"https://www.openstreetmap.org/directions?to={lat},{lon}",
    }


def _overpass(consulta: str) -> dict | None:
    """Tenta os servidores do Overpass em ordem; None se todos falharem."""
    for url in OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": consulta},
                                 headers={"User-Agent": USER_AGENT}, timeout=8)
            resp.raise_for_status()
            dados = resp.json()
        except requests.RequestException:  # inclui JSON inválido (página de erro com status 200)
            continue
        # Servidor lotado às vezes responde 200 com "remark" de erro e lista vazia: não é "nada por perto"
        if "remark" in dados and not dados.get("elements"):
            continue
        return dados
    return None


# ---------------------------------------------------------------- jogo: onde procurar cada tema
def _casa(filtro: str, tags: dict) -> bool:
    """O elemento do OSM bate com o filtro do Overpass (ex.: 'leisure~"park|garden"')?"""
    chave, sep, valores = re.split(r"([~=])", filtro, maxsplit=1)
    valor = tags.get(chave)
    if valor is None:
        return False
    opcoes = valores.strip('"').split("|")
    return valor in opcoes


def buscar_pontos_temas(temas, lat: float, lon: float, raio_m: int = 2000, por_tema: int = 15) -> list[dict]:
    """Onde procurar cada tema (uma consulta só no Overpass). Lança RuntimeError se o Overpass estiver fora."""
    filtros = sorted({f for t in temas for f in t.tags_osm})
    partes = "".join(f"nwr[{_ancorado(f)}](around:{raio_m},{lat},{lon});" for f in filtros)
    dados = _overpass(f"[out:json][timeout:25];({partes});out center 300;")
    if dados is None:
        raise RuntimeError("OpenStreetMap (Overpass) fora do ar")
    pontos: dict[str, list[dict]] = {t.id: [] for t in temas}
    for el in dados.get("elements", []):
        tags = el.get("tags", {})
        centro = el.get("center", {})
        la = el["lat"] if "lat" in el else centro.get("lat")
        lo = el["lon"] if "lon" in el else centro.get("lon")
        if la is None or lo is None:
            continue
        for t in temas:
            if any(_casa(f, tags) for f in t.tags_osm):
                pontos[t.id].append({
                    "tema": t.id, "nome": tags.get("name") or t.onde.split(",")[0].capitalize(),
                    "tipo": next((tags[k] for k in ("leisure", "shop", "amenity", "natural", "landuse") if k in tags), None),
                    "lat": la, "lon": lo, "distancia_km": round(distancia_km(lat, lon, la, lo), 2),
                    "mapa": f"https://www.openstreetmap.org/{el['type']}/{el['id']}", **detalhes_osm(tags),
                })
    saida = []
    for lista in pontos.values():
        saida += sorted(lista, key=lambda p: p["distancia_km"])[:por_tema]
    return saida
