"""Temas do jogo e tema do dia.

Todos os temas valem sempre; o tema do dia vale o dobro de pontos.
O tema do dia sai só da data (rodízio), igual para todo mundo e sem servidor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Horário de Brasília (sem horário de verão desde 2019): o dia vira à meia-noite daqui
FUSO = timezone(timedelta(hours=-3), "BRT")


@dataclass(frozen=True)
class Tema:
    id: str
    nome: str
    emoji: str
    generico: str              # achado genérico (sem detalhe): vale só a pontuação base
    achado: str                # o que a IA deve dizer como "achado" (vai no prompt do Gemma)
    frases_clip: tuple[str, ...]  # reserva sem chave: o CLIP decide o tema por estas frases
    tags_osm: tuple[str, ...]  # onde procurar no mapa (filtros do Overpass)
    onde: str                  # texto curto: onde costuma ter
    categoria: str | None      # categoria do catálogo para "Onde encontrar" (None: não se compra)


TEMAS: list[Tema] = [
    Tema("carros", "Carros", "🚗", "carro",
         "marca e modelo do carro (ex.: Volkswagen Gol, Fiat Mobi, Toyota Corolla); se não der, só a marca",
         ("a photo of a car", "a photo of a car parked on the street"),
         ('amenity="parking"', 'shop="car"', 'amenity="fuel"'),
         "estacionamentos, concessionárias e postos", "veículos"),
    Tema("plantas", "Plantas e flores", "🌿", "planta",
         "nome popular da planta ou flor em português (ex.: ipê-amarelo, girassol, costela-de-adão)",
         ("a photo of a plant", "a photo of a flower", "a photo of a tree"),
         ('leisure~"park|garden"', 'shop="florist"', 'landuse="forest"'),
         "parques, praças, jardins e floriculturas", "casa e decoração"),
    Tema("passaros", "Pássaros", "🐦", "pássaro",
         "nome popular do pássaro em português (ex.: bem-te-vi, sabiá-laranjeira, pombo, quero-quero)",
         ("a photo of a bird", "a photo of a bird on a tree branch"),
         ('leisure="park"', 'natural~"wood|water|beach"'),
         "parques, matas, lagoas e praias", None),
    Tema("pets", "Cachorros e gatos", "🐶", "cachorro ou gato",
         "espécie e raça em português (ex.: cachorro vira-lata caramelo, gato siamês, cachorro shih-tzu)",
         ("a photo of a dog", "a photo of a cat"),
         ('leisure="dog_park"', 'shop="pet"', 'amenity="veterinary"'),
         "parcões, pet shops e veterinários", "animais"),
    Tema("pecas", "Peças de computador", "🖥️", "peça de computador",
         "nome da peça em português (ex.: placa de vídeo, memória RAM, processador, placa-mãe, SSD, fonte)",
         ("a photo of a computer part", "a photo of a graphics card", "a photo of a computer motherboard"),
         ('shop~"computer|electronics"', 'craft="electronics_repair"'),
         "lojas de informática e assistências técnicas", "eletrônicos"),
]
POR_ID = {t.id: t for t in TEMAS}

# Reserva sem chave: frases de "não vale" (foto de tela/impressão) e de "nenhum tema"
FRASES_TELA = ("a photo of a computer screen showing a picture", "a photo of a phone screen showing a picture",
               "a printed photo on paper", "a drawing or cartoon", "a toy model")
FRASES_NENHUM = ("a photo of a person", "a photo of a room", "a photo of food", "a photo of a building",
                 "a photo of an everyday object")


def agora() -> datetime:
    return datetime.now(FUSO)


def dia_de(momento: datetime | None) -> date:
    """Data no horário de Brasília (datetime sem fuso é tratado como já estando nele)."""
    if momento is None:
        return agora().date()
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO)
    return momento.date()


def tema_do_dia(dia: date | None = None) -> Tema:
    dia = dia or agora().date()
    return TEMAS[dia.toordinal() % len(TEMAS)]


def item_do_achado(tema: Tema, achado: str):
    """Achado do jogo -> Item do catálogo, para a página "Onde encontrar" (None se não se compra/adota)."""
    from src.categorias import Item, tipo_da_categoria

    if not tema.categoria or not achado:
        return None
    return Item(achado, achado, tema.categoria, tipo_da_categoria(tema.categoria))
