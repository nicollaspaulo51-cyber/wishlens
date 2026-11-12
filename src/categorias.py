"""Catálogo de itens que o WishLens sabe reconhecer.

Cada item tem:
- rotulo_en: texto em inglês usado no prompt do CLIP (o modelo entende melhor inglês)
- nome: nome em português mostrado ao usuário
- categoria: grupo usado na análise (EDA, clustering, comparação)
- tipo: "comprar", "receita" ou "adotar" (define o que o app mostra)

Para reconhecer coisas novas, basta adicionar linhas em ITENS.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    rotulo_en: str
    nome: str
    categoria: str
    tipo: str


_NOME_OK = re.compile(r"[\w .,'()/+-]{1,60}")


def nome_valido(nome: str) -> bool:
    """Nome digitado pela pessoa: só letras (com acento), números e pontuação simples.

    Os nomes aparecem em HTML em várias páginas (inclusive para outra pessoa, em Comparar),
    então nada de < > & " ; ou quebra de linha.
    """
    return bool(_NOME_OK.fullmatch(nome))


def tipo_da_categoria(categoria: str) -> str:
    """O que o app mostra para a categoria: receita/restaurante, adoção ou lojas."""
    return {"comida": "receita", "bebidas": "receita", "animais": "adotar"}.get(categoria, "comprar")


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

# Faixa estimada por item (R$, novo, Brasil, 2026). Estimativa escrita à mão: o preço real está nos links.
PRECO_ITEM = {
    # vestuário / calçados
    "camiseta": "R$ 30–150", "jaqueta": "R$ 120–600", "vestido": "R$ 80–400", "calça jeans": "R$ 80–350",
    "boné/chapéu": "R$ 30–200", "mochila": "R$ 80–500", "relógio": "R$ 100–2.000", "óculos de sol": "R$ 50–800",
    "tênis": "R$ 150–1.200", "sandália/chinelo": "R$ 30–250",
    # eletrônicos
    "celular": "R$ 800–8.000", "notebook": "R$ 2.500–8.000", "fone de ouvido": "R$ 50–2.000",
    "televisão": "R$ 1.200–6.000", "câmera fotográfica": "R$ 1.500–10.000", "smartwatch": "R$ 200–3.000",
    "teclado": "R$ 50–800", "mouse": "R$ 30–300", "tablet": "R$ 700–6.000", "monitor": "R$ 600–3.000",
    "caixa de som": "R$ 100–1.500", "carregador": "R$ 30–200", "impressora": "R$ 500–2.000",
    # brinquedos e games
    "videogame": "R$ 2.500–5.000", "brinquedo": "R$ 30–300", "controle de videogame": "R$ 200–600",
    # casa
    "sofá": "R$ 1.200–5.000", "cadeira": "R$ 100–1.500", "luminária": "R$ 50–400", "garrafa": "R$ 20–200",
    "travesseiro/almofada": "R$ 30–200", "mesa": "R$ 300–3.000", "planta": "R$ 20–200", "caneca": "R$ 15–80",
    "eletrodoméstico": "R$ 150–3.000",
    # esporte / beleza / papelaria / veículos
    "bicicleta": "R$ 700–5.000", "bola de futebol": "R$ 50–400", "violão/guitarra": "R$ 300–3.000",
    "prancha de surfe": "R$ 800–3.500", "perfume": "R$ 80–900", "maquiagem": "R$ 20–300",
    "livro": "R$ 30–120", "caneta/lápis": "R$ 2–50", "caderno": "R$ 15–80",
    "carro": "R$ 50.000–200.000", "moto": "R$ 12.000–60.000",
    # comida e bebida (prato em restaurante/delivery)
    "pizza": "R$ 40–120", "hambúrguer": "R$ 25–70", "sushi": "R$ 50–150", "arroz e feijão": "R$ 20–45",
    "macarrão": "R$ 30–80", "salada": "R$ 20–50", "bolo": "R$ 30–120", "sorvete": "R$ 10–40",
    "açaí": "R$ 15–40", "churrasco": "R$ 50–150", "cachorro-quente": "R$ 10–30", "pastel": "R$ 8–25",
    "café": "R$ 5–20", "suco": "R$ 8–20",
}


def faixa_preco(item: Item) -> str:
    """Faixa do item; sem ela (vocabulário grande, texto livre), a da categoria marcada como estimativa."""
    if item.nome in PRECO_ITEM:
        return PRECO_ITEM[item.nome]
    faixa = FAIXA_PRECO.get(item.categoria, "—")
    return faixa if item.categoria == "animais" else f"{faixa} (estimativa da categoria)"

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
