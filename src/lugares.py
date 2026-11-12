"""Lugares próximos via OpenStreetMap (Overpass API, dados abertos ODbL)."""

from __future__ import annotations

import math

import requests

from src.categorias import Item

# Servidores públicos do Overpass, tentados em ordem (o primeiro às vezes fica sobrecarregado)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "WishLens/0.1 (projeto academico de Ciencia de Dados)"

# Quais tags do OSM procurar para cada categoria
TAGS_POR_CATEGORIA: dict[str, list[str]] = {
    "vestuário": ['shop~"clothes|fashion|bag|watches|optician"'],
    "calçados": ['shop="shoes"', 'shop="sports"'],
    "eletrônicos": ['shop~"electronics|mobile_phone|computer"'],
    "brinquedos e games": ['shop~"toys|video_games|games"'],
    "casa e decoração": ['shop~"furniture|houseware|garden_centre|interior_decoration|appliance"'],
    "esporte e lazer": ['shop~"sports|bicycle|musical_instrument|outdoor"'],
    "beleza": ['shop~"cosmetics|perfumery|beauty"'],
    "livros e papelaria": ['shop~"books|stationery"'],
    "veículos": ['shop~"car|motorcycle"'],
    "comida": ['amenity~"restaurant|fast_food|food_court"'],
    "bebidas": ['amenity~"cafe|bar|ice_cream"'],
    "animais": ['amenity="animal_shelter"', 'shop="pet"', 'amenity="veterinary"'],
}


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    """Distância em linha reta (fórmula de Haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def montar_consulta(item: Item, lat: float, lon: float, raio_m: int) -> str:
    filtros = TAGS_POR_CATEGORIA.get(item.categoria, [])
    partes = "".join(f"nwr[{f}](around:{raio_m},{lat},{lon});" for f in filtros)
    return f"[out:json][timeout:25];({partes});out center 50;"


def buscar_proximos(item: Item, lat: float, lon: float, raio_m: int = 3000, limite: int = 10) -> list[dict]:
    """Retorna até `limite` lugares do OSM ordenados pela distância."""
    consulta = montar_consulta(item, lat, lon, raio_m)
    for i, url in enumerate(OVERPASS_URLS):
        try:
            resp = requests.post(url, data={"data": consulta},
                                 headers={"User-Agent": USER_AGENT}, timeout=20)
            resp.raise_for_status()
            break
        except requests.RequestException:
            if i == len(OVERPASS_URLS) - 1:
                raise

    lugares = []
    for el in resp.json().get("elements", []):
        tags = el.get("tags", {})
        la = el.get("lat") or el.get("center", {}).get("lat")
        lo = el.get("lon") or el.get("center", {}).get("lon")
        if la is None or lo is None:
            continue
        lugares.append({
            "nome": tags.get("name", "(sem nome no mapa)"),
            "tipo": tags.get("shop") or tags.get("amenity"),
            "lat": la,
            "lon": lo,
            "distancia_km": round(distancia_km(lat, lon, la, lo), 2),
            "mapa": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
        })
    lugares.sort(key=lambda x: x["distancia_km"])
    return lugares[:limite]
