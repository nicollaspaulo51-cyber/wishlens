"""Catálogo de itens que o WishLens sabe reconhecer.

Cada item tem:
- rotulo_en: texto em inglês usado no prompt do CLIP (o modelo entende melhor inglês)
- nome: nome em português mostrado ao usuário
- categoria: grupo usado na análise (EDA, clustering, comparação)
- tipo: "comprar", "receita" ou "adotar" (define o que o app mostra)

Para reconhecer coisas novas, basta adicionar linhas em ITENS.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    rotulo_en: str
    nome: str
    categoria: str
    tipo: str


# Faixa de preço de referência por categoria (estimativa simples, em R$)
FAIXA_PRECO = {
    "vestuário": "R$ 50–300",
    "calçados": "R$ 100–500",
    "eletrônicos": "R$ 300–5.000",
    "casa e decoração": "R$ 50–1.000",
    "esporte e lazer": "R$ 50–1.500",
    "beleza": "R$ 20–200",
    "livros e papelaria": "R$ 10–150",
    "brinquedos e games": "R$ 50–3.000",
    "veículos": "R$ 1.000+",
    "comida": "R$ 15–80",
    "bebidas": "R$ 5–60",
    "animais": "adoção gratuita",
}

ITENS: list[Item] = [
    # vestuário / calçados
    Item("a t-shirt", "camiseta", "vestuário", "comprar"),
    Item("a jacket", "jaqueta", "vestuário", "comprar"),
    Item("a dress", "vestido", "vestuário", "comprar"),
    Item("a pair of jeans", "calça jeans", "vestuário", "comprar"),
    Item("a cap or hat", "boné/chapéu", "vestuário", "comprar"),
    Item("a backpack", "mochila", "vestuário", "comprar"),
    Item("a wristwatch", "relógio", "vestuário", "comprar"),
    Item("sunglasses", "óculos de sol", "vestuário", "comprar"),
    Item("sneakers", "tênis", "calçados", "comprar"),
    Item("sandals", "sandália/chinelo", "calçados", "comprar"),
    # eletrônicos
    Item("a smartphone", "celular", "eletrônicos", "comprar"),
    Item("a laptop", "notebook", "eletrônicos", "comprar"),
    Item("headphones", "fone de ouvido", "eletrônicos", "comprar"),
    Item("a television", "televisão", "eletrônicos", "comprar"),
    Item("a camera", "câmera fotográfica", "eletrônicos", "comprar"),
    Item("a smartwatch", "smartwatch", "eletrônicos", "comprar"),
    Item("a computer keyboard", "teclado", "eletrônicos", "comprar"),
    Item("a computer mouse", "mouse", "eletrônicos", "comprar"),
    Item("a tablet computer", "tablet", "eletrônicos", "comprar"),
    Item("a computer monitor", "monitor", "eletrônicos", "comprar"),
    Item("a bluetooth speaker", "caixa de som", "eletrônicos", "comprar"),
    Item("a phone charger or cable", "carregador", "eletrônicos", "comprar"),
    Item("a printer", "impressora", "eletrônicos", "comprar"),
    # games / brinquedos
    Item("a video game console", "videogame", "brinquedos e games", "comprar"),
    Item("a toy", "brinquedo", "brinquedos e games", "comprar"),
    Item("a video game controller", "controle de videogame", "brinquedos e games", "comprar"),
    # casa
    Item("a sofa", "sofá", "casa e decoração", "comprar"),
    Item("a chair", "cadeira", "casa e decoração", "comprar"),
    Item("a lamp", "luminária", "casa e decoração", "comprar"),
    Item("a water bottle", "garrafa", "casa e decoração", "comprar"),
    Item("a pillow", "travesseiro/almofada", "casa e decoração", "comprar"),
    Item("a table", "mesa", "casa e decoração", "comprar"),
    Item("a potted plant", "planta", "casa e decoração", "comprar"),
    Item("a coffee mug", "caneca", "casa e decoração", "comprar"),
    Item("a kitchen appliance", "eletrodoméstico", "casa e decoração", "comprar"),
    # esporte / lazer
    Item("a bicycle", "bicicleta", "esporte e lazer", "comprar"),
    Item("a soccer ball", "bola de futebol", "esporte e lazer", "comprar"),
    Item("a guitar", "violão/guitarra", "esporte e lazer", "comprar"),
    Item("a surfboard", "prancha de surfe", "esporte e lazer", "comprar"),
    # beleza / livros / veículos
    Item("a perfume bottle", "perfume", "beleza", "comprar"),
    Item("makeup", "maquiagem", "beleza", "comprar"),
    Item("a book", "livro", "livros e papelaria", "comprar"),
    Item("a pen or pencil", "caneta/lápis", "livros e papelaria", "comprar"),
    Item("a notebook (paper)", "caderno", "livros e papelaria", "comprar"),
    Item("a car", "carro", "veículos", "comprar"),
    Item("a motorcycle", "moto", "veículos", "comprar"),
    # comida (receita + restaurante + delivery)
    Item("a pizza", "pizza", "comida", "receita"),
    Item("a hamburger", "hambúrguer", "comida", "receita"),
    Item("sushi", "sushi", "comida", "receita"),
    Item("a plate of rice and beans", "arroz e feijão", "comida", "receita"),
    Item("pasta", "macarrão", "comida", "receita"),
    Item("a salad", "salada", "comida", "receita"),
    Item("a cake", "bolo", "comida", "receita"),
    Item("ice cream", "sorvete", "comida", "receita"),
    Item("acai bowl", "açaí", "comida", "receita"),
    Item("barbecue meat", "churrasco", "comida", "receita"),
    Item("a hot dog", "cachorro-quente", "comida", "receita"),
    Item("fried pastry (pastel)", "pastel", "comida", "receita"),
    Item("a cup of coffee", "café", "bebidas", "receita"),
    Item("a glass of juice", "suco", "bebidas", "receita"),
    # animais (adoção)
    Item("a dog", "cachorro", "animais", "adotar"),
    Item("a cat", "gato", "animais", "adotar"),
    Item("a rabbit", "coelho", "animais", "adotar"),
    Item("a bird", "pássaro", "animais", "adotar"),
]

CATEGORIAS = sorted({i.categoria for i in ITENS})

# Emoji de cada item, usado nos cartões do feed "Descobrir"
EMOJI = {
    "camiseta": "👕", "jaqueta": "🧥", "vestido": "👗", "calça jeans": "👖", "boné/chapéu": "🧢",
    "mochila": "🎒", "relógio": "⌚", "óculos de sol": "🕶️", "tênis": "👟", "sandália/chinelo": "🩴",
    "celular": "📱", "notebook": "💻", "fone de ouvido": "🎧", "televisão": "📺", "câmera fotográfica": "📷",
    "smartwatch": "⌚", "teclado": "⌨️", "mouse": "🖱️", "tablet": "📱", "monitor": "🖥️", "caixa de som": "🔊",
    "carregador": "🔌", "impressora": "🖨️", "controle de videogame": "🎮", "garrafa": "🍶",
    "travesseiro/almofada": "🛏️", "mesa": "🪑", "caneta/lápis": "✏️", "caderno": "📓", "videogame": "🎮", "brinquedo": "🧸", "sofá": "🛋️",
    "cadeira": "🪑", "luminária": "💡", "planta": "🪴", "caneca": "☕", "eletrodoméstico": "🍳",
    "bicicleta": "🚲", "bola de futebol": "⚽", "violão/guitarra": "🎸", "prancha de surfe": "🏄",
    "perfume": "🧴", "maquiagem": "💄", "livro": "📚", "carro": "🚗", "moto": "🏍️",
    "pizza": "🍕", "hambúrguer": "🍔", "sushi": "🍣", "arroz e feijão": "🍛", "macarrão": "🍝",
    "salada": "🥗", "bolo": "🍰", "sorvete": "🍨", "açaí": "🫐", "churrasco": "🥩",
    "cachorro-quente": "🌭", "pastel": "🥟", "café": "☕", "suco": "🧃",
    "cachorro": "🐶", "gato": "🐱", "coelho": "🐰", "pássaro": "🐦",
}


def emoji(item: Item) -> str:
    return EMOJI.get(item.nome, {"comprar": "🛍️", "receita": "🍲", "adotar": "🐾"}[item.tipo])
