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
    # CLIP: (objeto em inglês, nome em português). A frase é "a photo of <objeto>"; o nome da frase que
    # mais combinou vira o achado quando só o CLIP julga (mouse e teclado são achados diferentes).
    objetos_clip: tuple[tuple[str, str], ...]
    tags_osm: tuple[str, ...]  # onde procurar no mapa (filtros do Overpass)
    onde: str                  # texto curto: onde costuma ter
    conta: str = ""            # o que conta como este tema (vai no prompt do Gemma)
    cor: str = "#6D4AFF"       # cor do tema no mapa

    @property
    def frases_clip(self) -> tuple[str, ...]:
        return tuple(f"a photo of {o}" for o, _ in self.objetos_clip)


TEMAS: list[Tema] = [
    Tema("carros", "Carros", "🚗", "carro",
         "marca e modelo do carro (ex.: Volkswagen Gol, Fiat Mobi, Toyota Corolla); se não der, só a marca",
         (("a car", "carro"), ("a car parked on the street", "carro"), ("the front of a car", "carro"),
          ("the back of a car", "carro"), ("a car seen from the side", "carro"), ("a pickup truck", "caminhonete"),
          ("an SUV", "SUV")),
         ('amenity="parking"', 'shop="car"', 'amenity="fuel"'),
         "estacionamentos, concessionárias e postos",
         "carros, caminhonetes e SUVs de verdade (inteiros ou só a frente/traseira). Carro de brinquedo NÃO conta",
         "#E5484D"),
    Tema("plantas", "Plantas e flores", "🌿", "planta",
         "nome popular da planta ou flor em português (ex.: ipê-amarelo, girassol, costela-de-adão)",
         (("a plant", "planta"), ("a flower", "flor"), ("a tree", "árvore"), ("a leaf, close-up", "folha"),
          ("a potted plant", "planta em vaso"), ("a succulent", "suculenta"), ("a cactus", "cacto"),
          ("a flowering bush", "arbusto florido")),
         ('leisure~"park|garden"', 'shop="florist"', 'landuse="forest"'),
         "parques, praças, jardins e floriculturas",
         "qualquer planta viva: árvore, flor, folha, arbusto, planta em vaso, suculenta, cacto. Planta de plástico NÃO conta",
         "#30A46C"),
    Tema("passaros", "Pássaros", "🐦", "pássaro",
         "nome popular do pássaro em português (ex.: bem-te-vi, sabiá-laranjeira, pombo, quero-quero)",
         (("a bird", "pássaro"), ("a bird on a tree branch", "pássaro"), ("a bird flying", "pássaro"),
          ("a pigeon", "pombo"), ("a small bird on the ground", "pássaro"), ("a bird on a wire", "pássaro"),
          ("a parakeet", "periquito")),
         ('leisure="park"', 'natural~"wood|water|beach"'),
         "parques, matas, lagoas e praias",
         "qualquer ave viva, mesmo pequena na foto: pombo, pardal, galinha, pato, papagaio de estimação",
         "#0091FF"),
    Tema("pets", "Cachorros e gatos", "🐶", "cachorro ou gato",
         "espécie e raça em português (ex.: cachorro vira-lata caramelo, gato siamês, cachorro shih-tzu)",
         (("a dog", "cachorro"), ("a cat", "gato"), ("a puppy", "filhote de cachorro"), ("a kitten", "filhote de gato"),
          ("a dog lying down", "cachorro"), ("a cat sleeping", "gato"), ("a dog on a leash", "cachorro")),
         ('leisure="dog_park"', 'shop="pet"', 'amenity="veterinary"'),
         "parcões, pet shops e veterinários",
         "cachorros e gatos de verdade, de qualquer raça ou vira-lata, filhotes também",
         "#F76B15"),
    Tema("pecas", "Peças e periféricos de computador", "🖥️", "peça de computador",
         "nome da peça ou periférico em português (ex.: mouse, teclado, monitor, headset, webcam, pendrive, "
         "placa de vídeo, memória RAM, processador, placa-mãe, SSD, fonte)",
         (("a computer mouse", "mouse"), ("a computer keyboard", "teclado"), ("a computer monitor", "monitor"),
          ("a gaming headset", "headset"), ("a webcam", "webcam"), ("a USB flash drive", "pendrive"),
          ("a graphics card", "placa de vídeo"), ("RAM memory sticks", "memória RAM"),
          ("a computer motherboard", "placa-mãe"), ("a computer power supply", "fonte"),
          ("a computer part", "peça de computador")),
         ('shop~"computer|electronics"', 'craft="electronics_repair"'),
         "lojas de informática e assistências técnicas",
         "peças internas E periféricos: mouse, teclado, monitor, headset/fone, webcam, microfone, caixinha de som de PC, "
         "cabo, pendrive, HD/SSD externo, roteador, gabinete, placa de vídeo, RAM, processador, placa-mãe, cooler, fonte. "
         "Um monitor ou notebook de verdade conta (a tela dele ligada não é trapaça)",
         "#8E4EC6"),
]
POR_ID = {t.id: t for t in TEMAS}

# "Não vale": frases genéricas de tela/impressão + frases GÊMEAS de cada objeto dos temas
# ("um pássaro numa tela de computador"), para "pássaro de verdade" disputar com "pássaro na tela".
MODELOS_TELA = ("a photo of a computer screen showing {}", "a photo of a phone screen displaying {}",
                "a printed picture of {}")
FRASES_TELA = (("a photo of a computer screen showing a picture", "a photo of a phone screen showing a picture",
                "a printed photo on paper", "a drawing or cartoon", "a toy model")
               + tuple(dict.fromkeys(m.format(o) for t in TEMAS if t.id != "pecas"
                                     for o, _ in t.objetos_clip for m in MODELOS_TELA)))
# "nenhum" não pode ter frases genéricas ("um objeto do dia a dia"): elas roubavam o mouse do tema de peças.
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
