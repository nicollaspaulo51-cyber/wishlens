"""Lugares próximos via OpenStreetMap (Overpass API, dados abertos ODbL)."""

from __future__ import annotations

import math
import re

import requests

from src.categorias import Item

# Servidores públicos do Overpass, tentados em ordem (o primeiro às vezes fica sobrecarregado)
OVERPASS_URLS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
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


def _ancorado(filtro: str) -> str:
    """shop~"car|motorcycle" casaria carpet e car_repair: o valor tem de ser exatamente um da lista."""
    chave, sep, valores = re.split(r"([~=])", filtro, maxsplit=1)
    return f'{chave}~"^({valores.strip(chr(34))})$"' if sep == "~" else filtro


# Para que serve o local (ícone e texto no mapa). A 1ª regra que bater vence.
_NOME_JOGAR = re.compile(r"lan ?house|cyber ?caf", re.I)
_NOME_CONSERTAR = re.compile(r"assist[eê]ncia|conserto|manuten[cç][aã]o", re.I)


def finalidade(tags: dict, nome: str = "") -> str:
    """comprar, jogar, consertar, adotar, cuidar (veterinário) ou comer, pelas tags do OSM e pelo nome.

    O nome conta porque lan houses e assistências costumam estar marcadas no OSM como shop=computer.
    """
    amenity, shop = tags.get("amenity", ""), tags.get("shop", "")
    if amenity == "internet_cafe" or tags.get("leisure") == "amusement_arcade" or _NOME_JOGAR.search(nome):
        return "jogar"
    if amenity in {"restaurant", "fast_food", "food_court", "cafe", "bar", "ice_cream"}:
        return "comer"  # antes de "consertar": pontos mistos ("Subway;Praia Tech") são achados buscando comida
    if "repair" in tags.get("craft", "") or "repair" in shop or _NOME_CONSERTAR.search(nome):
        return "consertar"
    if amenity == "animal_shelter":
        return "adotar"
    if amenity == "veterinary":
        return "cuidar"
    return "comprar"


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


def _endereco_nominatim(end: dict) -> str | None:
    rua = end.get("road")
    numero = end.get("house_number")
    bairro = end.get("suburb") or end.get("neighbourhood")
    cidade = end.get("city") or end.get("town") or end.get("village")
    partes = [" ".join(y for y in (rua, numero) if y) if rua else None, bairro, cidade]
    return ", ".join(x for x in partes if x) or None


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


def montar_consulta(item: Item, lat: float, lon: float, raio_m: int) -> str:
    filtros = [_ancorado(f) for f in TAGS_POR_CATEGORIA.get(item.categoria, [])]
    partes = "".join(f"nwr[{f}](around:{raio_m},{lat},{lon});" for f in filtros)
    return f"[out:json][timeout:25];({partes});out center 50;"


def tags_simples(item: Item) -> list[str]:
    """Filtros do Overpass como tags "[chave=valor]" (sintaxe que o Nominatim entende)."""
    tags = []
    for f in TAGS_POR_CATEGORIA.get(item.categoria, []):
        chave, valores = re.split(r"[~=]", f, maxsplit=1)
        tags += [f"[{chave}={v}]" for v in valores.strip('"').split("|")]
    return tags


def _buscar_nominatim(item: Item, lat: float, lon: float, raio_m: int) -> list[dict]:
    """Reserva quando o Overpass está fora do ar: uma busca no Nominatim por tag, dentro do raio."""
    from src.localizacao import _get  # import aqui: localizacao importa USER_AGENT deste módulo

    dlat = raio_m / 111_000
    dlon = dlat / max(math.cos(math.radians(lat)), 0.01)
    caixa = f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"
    vistos, lugares, erro, alguma_ok = set(), [], None, False
    for tag in tags_simples(item):
        try:
            achados = _get("/search", {"q": tag, "viewbox": caixa, "bounded": 1, "limit": 20,
                                       "addressdetails": 1, "extratags": 1})
        except requests.RequestException as e:  # uma tag falhou: segue com as outras
            erro = e
            continue
        alguma_ok = True
        for a in achados:
            chave = (a["osm_type"], a["osm_id"])
            la, lo = float(a["lat"]), float(a["lon"])
            dist = distancia_km(lat, lon, la, lo)
            if chave in vistos or dist * 1000 > raio_m:
                continue
            vistos.add(chave)
            nome = a.get("name") or "(sem nome no mapa)"
            detalhes = detalhes_osm(a.get("extratags") or {})
            detalhes["endereco"] = detalhes["endereco"] or _endereco_nominatim(a.get("address") or {})
            lugares.append({
                "nome": nome,
                "tipo": a.get("type"),
                "finalidade": finalidade({a.get("category", ""): a.get("type", "")}, nome),
                "lat": la,
                "lon": lo,
                "distancia_km": round(dist, 2),
                "mapa": f"https://www.openstreetmap.org/{a['osm_type']}/{a['osm_id']}",
                **detalhes,
            })
    if erro is not None and not alguma_ok:  # todas as tags falharam: não é "nada por perto"
        raise erro
    return lugares


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


def buscar_proximos(item: Item, lat: float, lon: float, raio_m: int = 3000, limite: int = 10) -> list[dict]:
    """Retorna até `limite` lugares do OSM ordenados pela distância (Overpass; reserva: Nominatim)."""
    dados = _overpass(montar_consulta(item, lat, lon, raio_m))

    if dados is None:
        lugares = _buscar_nominatim(item, lat, lon, raio_m)
        lugares.sort(key=lambda x: x["distancia_km"])
        return lugares[:limite]

    lugares = []
    for el in dados.get("elements", []):
        tags = el.get("tags", {})
        centro = el.get("center", {})
        la = el["lat"] if "lat" in el else centro.get("lat")
        lo = el["lon"] if "lon" in el else centro.get("lon")
        if la is None or lo is None:
            continue
        lugares.append({
            "nome": tags.get("name", "(sem nome no mapa)"),
            "tipo": tags.get("shop") or tags.get("amenity"),
            "finalidade": finalidade(tags, tags.get("name", "")),
            "lat": la,
            "lon": lo,
            "distancia_km": round(distancia_km(lat, lon, la, lo), 2),
            "mapa": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
            **detalhes_osm(tags),
        })
    lugares.sort(key=lambda x: x["distancia_km"])
    return lugares[:limite]


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
