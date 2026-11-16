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
    achado: str                # o que a IA deve dizer como "achado" (vai no prompt da IA)
    # CLIP: (objeto em inglês, nome em português). A frase é "a photo of <objeto>"; o nome da frase que
    # mais combinou vira o achado quando só o CLIP julga (mouse e teclado são achados diferentes).
    objetos_clip: tuple[tuple[str, str], ...]
    tags_osm: tuple[str, ...]  # onde procurar no mapa (filtros do Overpass)
    onde: str                  # texto curto: onde costuma ter
    conta: str = ""            # o que conta como este tema (vai no prompt da IA)
    cor: str = "#136B4C"       # cor do tema no mapa

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
    # id "pets" mantido: as capturas antigas de cachorros e gatos continuam no mesmo tema
    Tema("pets", "Animais", "🐾", "animal",
         "nome popular do animal em português, com a raça quando der (ex.: cachorro vira-lata caramelo, gato siamês, "
         "cavalo, vaca, lagartixa, borboleta, capivara, sagui)",
         (("a dog", "cachorro"), ("a cat", "gato"), ("a puppy", "filhote de cachorro"), ("a kitten", "filhote de gato"),
          ("a horse", "cavalo"), ("a cow", "vaca"), ("a goat", "cabra"), ("a pig", "porco"),
          ("a lizard", "lagarto"), ("a gecko on a wall", "lagartixa"), ("a turtle", "tartaruga"),
          ("a butterfly", "borboleta"), ("a bee", "abelha"), ("a spider", "aranha"), ("an ant", "formiga"),
          ("a fish in the water", "peixe"), ("a frog", "sapo"), ("a squirrel", "esquilo"),
          # sem "an animal" genérico: ele roubaria as fotos de pássaros
          ("a small monkey on a tree", "sagui"), ("a capybara", "capivara"), ("a rabbit", "coelho")),
         ('leisure="dog_park"', 'shop="pet"', 'amenity="veterinary"', 'tourism="zoo"'),
         "parcões, pet shops, veterinários e zoológicos",
         "qualquer animal vivo que não seja ave (as aves são do tema Pássaros): cachorro, gato, cavalo, vaca, "
         "lagarto, inseto, peixe, sapo, sagui, capivara... Bicho de pelúcia ou de brinquedo NÃO conta",
         "#F76B15"),
    Tema("pecas", "Peças e periféricos de computador", "🖥️", "peça de computador",
         "nome da peça ou periférico em português (ex.: mouse, teclado, monitor, headset, webcam, pendrive, "
         "placa de vídeo, memória RAM, processador, placa-mãe, SSD, fonte)",
         (("a computer mouse", "mouse"), ("a computer keyboard", "teclado"), ("a computer monitor", "monitor"),
          ("a gaming headset", "headset"), ("over-ear headphones", "fone de ouvido"),
          # Sem estas, fone comum e fone sem fio viravam "mouse" (a peça de formato mais parecido)
          ("wireless earbuds in their charging case", "fone de ouvido"), ("in-ear earphones", "fone de ouvido"),
          ("a microphone", "microfone"), ("computer speakers", "caixinha de som"),
          ("a webcam", "webcam"), ("a USB flash drive", "pendrive"),
          ("a graphics card", "placa de vídeo"), ("RAM memory sticks", "memória RAM"),
          ("a computer motherboard", "placa-mãe"), ("a computer power supply", "fonte"),
          ("a computer part", "peça de computador")),
         # lojas de informática são raras no OpenStreetMap fora do centro: celular, lan house, TI e shopping também têm
         ('shop~"computer|electronics|mobile_phone"', 'craft="electronics_repair"', 'amenity="internet_cafe"',
          'office="it"', 'shop="mall"'),
         "lojas de informática e de celular, assistências técnicas, lan houses e shoppings",
         "peças internas E periféricos: mouse, teclado, monitor, headset/fone, webcam, microfone, caixinha de som de PC, "
         "cabo, pendrive, HD/SSD externo, roteador, gabinete, placa de vídeo, RAM, processador, placa-mãe, cooler, fonte. "
         "Um monitor ou notebook de verdade conta (a tela dele ligada não é trapaça)",
         "#8E4EC6"),
]
POR_ID = {t.id: t for t in TEMAS}

# Modos (cada um numa aba do app, com o seu juiz e o seu pódio). O tema da captura é o id do modo e o achado é
# o tipo (pôr do sol, barra fixa, supino...). O Mapa livre são os 5 TEMAS acima e não muda.
MODOS: dict[str, Tema] = {t.id: t for t in [
    Tema("paisagens", "Paisagens", "🌄", "paisagem", "tipo de paisagem",
         (("a sunset over the horizon", "pôr do sol"), ("a sunrise over the horizon", "nascer do sol"),
          ("a city skyline seen from far away", "vista da cidade"), ("a beach with the sea and the horizon", "praia"),
          ("a mountain landscape", "montanha"), ("a river or lake landscape", "rio ou lagoa"),
          ("a waterfall", "cachoeira"), ("a starry night sky", "céu estrelado"),
          ("a wide landscape with a horizon", "paisagem"), ("a forest seen from far away", "paisagem")),
         ('tourism="viewpoint"',), "mirantes",
         "a vista aberta, com horizonte. Uma árvore ou flor de perto não é paisagem", "#0EA5A4"),
    Tema("treino", "Treino ao ar livre", "🤸", "aparelho de praça", "aparelho de ginástica de praça",
         (("an outdoor pull-up bar in a park", "barra fixa"), ("outdoor parallel bars for exercise", "paralelas"),
          ("an outdoor sit-up bench in a park", "abdominal"),
          ("an outdoor elliptical walker exercise machine in a park", "simulador de caminhada"),
          ("an outdoor leg press exercise machine in a public square", "leg press de praça"),
          ("an outdoor rowing exercise machine in a park", "remada"),
          ("an outdoor chest press exercise machine in a park", "supino de praça"),
          ("outdoor fitness equipment in a public park", "aparelho de praça")),
         ('leisure="fitness_station"', 'leisure~"park|pitch"'), "academias ao ar livre de praças e parques",
         "aparelhos de ginástica de praça ou parque", "#D6409F"),
    Tema("academia", "Academias", "🏋️", "aparelho de academia", "aparelho de musculação ou ginástica",
         (("a treadmill in a gym", "esteira"), ("a weight bench press in a gym", "supino"),
          ("a leg press machine in a gym", "leg press"), ("dumbbells on a rack", "halteres"),
          ("an exercise bike in a gym", "bicicleta ergométrica"), ("a cable crossover machine", "cross-over"),
          ("a barbell with weight plates", "barra com anilhas"), ("a smith machine in a gym", "smith"),
          ("a lat pulldown machine", "puxador"), ("kettlebells on the floor of a gym", "kettlebell"),
          ("gym exercise equipment", "aparelho de academia")),
         ('leisure="fitness_centre"',), "academias de ginástica",
         "aparelhos de musculação ou ginástica dentro da academia. Foto com uma pessoa em destaque não vale",
         "#E54666"),
]}
TODOS = {**POR_ID, **MODOS}  # o tema de qualquer captura, de qualquer aba

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
                 "a photo of a building", "a photo of an empty sky", "a photo of a document with text",
                 # celular não é periférico (e a tela dele mostrando um teclado não é um teclado)
                 "a photo of a smartphone", "a person holding a smartphone",
                 # o verso do celular (lentes da câmera, capinha) virava "fone de ouvido" pelo formato do estojo
                 "the back of a smartphone with camera lenses", "a mobile phone in a phone case",
                 # O CLIP só escolhe entre as frases que tem: sem estes objetos comuns, qualquer coisa fora dos temas
                 # caía no objeto de tema mais parecido (uma garrafa virava "peça de computador"). Nada aqui pode
                 # ser objeto de tema (TV e notebook ficam de fora: parecem monitor).
                 *(f"a photo of {o}" for o in (
                     "a water bottle", "a cup or mug", "a chair", "a table", "a backpack", "a shoe", "clothes",
                     "a set of keys", "a wallet", "a pen", "a book", "a TV remote control", "eyeglasses",
                     "a wristwatch", "a power bank", "a door", "a bed", "a sofa", "a lamp", "an electric fan",
                     "a cardboard box", "a bicycle", "a motorcycle", "a plastic bag", "a toothbrush", "a bowl")))


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
