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
    conta: str = ""            # o que conta como este tema (vai no prompt do Gemma)


TEMAS: list[Tema] = [
    Tema("carros", "Carros", "🚗", "carro",
         "marca e modelo do carro (ex.: Volkswagen Gol, Fiat Mobi, Toyota Corolla); se não der, só a marca",
         ("a photo of a car", "a photo of a car parked on the street", "a photo of the front of a car",
          "a photo of the back of a car", "a side view photo of a car", "a photo of a pickup truck",
          "a photo of an SUV"),
         ('amenity="parking"', 'shop="car"', 'amenity="fuel"'),
         "estacionamentos, concessionárias e postos", "veículos",
         "carros, caminhonetes e SUVs de verdade (inteiros ou só a frente/traseira). Carro de brinquedo NÃO conta"),
    Tema("plantas", "Plantas e flores", "🌿", "planta",
         "nome popular da planta ou flor em português (ex.: ipê-amarelo, girassol, costela-de-adão)",
         ("a photo of a plant", "a photo of a flower", "a photo of a tree", "a close-up photo of a leaf",
          "a photo of a potted plant", "a photo of a succulent", "a photo of a cactus", "a photo of a flowering bush"),
         ('leisure~"park|garden"', 'shop="florist"', 'landuse="forest"'),
         "parques, praças, jardins e floriculturas", "casa e decoração",
         "qualquer planta viva: árvore, flor, folha, arbusto, planta em vaso, suculenta, cacto. Planta de plástico NÃO conta"),
    Tema("passaros", "Pássaros", "🐦", "pássaro",
         "nome popular do pássaro em português (ex.: bem-te-vi, sabiá-laranjeira, pombo, quero-quero)",
         ("a photo of a bird", "a photo of a bird on a tree branch", "a photo of a bird flying",
          "a photo of a pigeon", "a photo of a small bird on the ground", "a photo of a bird on a wire"),
         ('leisure="park"', 'natural~"wood|water|beach"'),
         "parques, matas, lagoas e praias", None,
         "qualquer ave viva, mesmo pequena na foto: pombo, pardal, galinha, pato, papagaio de estimação"),
    Tema("pets", "Cachorros e gatos", "🐶", "cachorro ou gato",
         "espécie e raça em português (ex.: cachorro vira-lata caramelo, gato siamês, cachorro shih-tzu)",
         ("a photo of a dog", "a photo of a cat", "a photo of a puppy", "a photo of a kitten",
          "a photo of a dog lying down", "a photo of a cat sleeping", "a photo of a dog on a leash"),
         ('leisure="dog_park"', 'shop="pet"', 'amenity="veterinary"'),
         "parcões, pet shops e veterinários", "animais",
         "cachorros e gatos de verdade, de qualquer raça ou vira-lata, filhotes também"),
    Tema("pecas", "Peças e periféricos de computador", "🖥️", "peça de computador",
         "nome da peça ou periférico em português (ex.: mouse, teclado, monitor, headset, webcam, pendrive, "
         "placa de vídeo, memória RAM, processador, placa-mãe, SSD, fonte)",
         ("a photo of a computer mouse", "a photo of a computer keyboard", "a photo of a computer monitor",
          "a photo of a gaming headset", "a photo of a webcam", "a photo of a USB flash drive",
          "a photo of a graphics card", "a photo of RAM memory sticks", "a photo of a computer motherboard",
          "a photo of a computer power supply", "a photo of a computer part"),
         ('shop~"computer|electronics"', 'craft="electronics_repair"'),
         "lojas de informática e assistências técnicas", "eletrônicos",
         "peças internas E periféricos: mouse, teclado, monitor, headset/fone, webcam, microfone, caixinha de som de PC, "
         "cabo, pendrive, HD/SSD externo, roteador, gabinete, placa de vídeo, RAM, processador, placa-mãe, cooler, fonte. "
         "Um monitor ou notebook de verdade conta (a tela dele ligada não é trapaça)"),
]
POR_ID = {t.id: t for t in TEMAS}

# Reserva sem chave: frases de "não vale" (foto de tela/impressão) e de "nenhum tema".
# "nenhum" não pode ter frases genéricas ("um objeto do dia a dia"): elas roubavam o mouse do tema de peças.
FRASES_TELA = ("a photo of a computer screen showing a picture", "a photo of a phone screen showing a picture",
               "a printed photo on paper", "a drawing or cartoon", "a toy model")
FRASES_NENHUM = ("a photo of a person", "a selfie", "a photo of a room interior", "a photo of food on a plate",
                 "a photo of a building", "a photo of an empty sky", "a photo of a document with text")


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
