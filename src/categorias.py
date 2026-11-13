"""Categorias da VERSÃO ANTERIOR do WishLens (desejos de consumo).

O jogo só usa `nome_valido`. O resto (ITENS, CATEGORIAS, faixa de preço) fica porque os notebooks
01–04, os dados de exemplo de desejos (`src/exemplo.gerar_exemplos`) e os testes do K-Means usam;
será refeito com os temas do jogo na próxima etapa.
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


def faixa_preco(item: Item) -> str:
    return FAIXA_PRECO.get(item.categoria, "—")


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
    Item("french fries", "batata frita", "comida", "receita"),
    Item("a sandwich", "sanduíche", "comida", "receita"),
    Item("pao de queijo, small round Brazilian cheese bread balls", "pão de queijo", "comida", "receita"),
    Item("coxinha, a teardrop-shaped Brazilian fried chicken croquette", "coxinha", "comida", "receita"),
    Item("tapioca crepe", "tapioca", "comida", "receita"),
    Item("feijoada, Brazilian black bean stew", "feijoada", "comida", "receita"),
    Item("fried chicken", "frango frito", "comida", "receita"),
    Item("a chocolate bar", "chocolate", "comida", "receita"),
    Item("cookies or biscuits", "biscoito", "comida", "receita"),
    Item("a bag of potato chips", "salgadinho", "comida", "receita"),
    Item("popcorn", "pipoca", "comida", "receita"),
    Item("brigadeiro, Brazilian chocolate truffles", "brigadeiro", "comida", "receita"),
    Item("a cup of coffee", "café", "bebidas", "receita"),
    Item("a glass of juice", "suco", "bebidas", "receita"),
    Item("a can of energy drink", "energético", "bebidas", "receita"),
    Item("a can of soda", "refrigerante", "bebidas", "receita"),
    Item("a can of beer", "cerveja", "bebidas", "receita"),
    Item("a plastic bottle of mineral water", "água mineral", "bebidas", "receita"),
    Item("a bottle of wine", "vinho", "bebidas", "receita"),
    Item("a cup of tea", "chá", "bebidas", "receita"),
    Item("a glass of milk", "leite", "bebidas", "receita"),
    Item("a cocktail drink", "drink", "bebidas", "receita"),
    # animais (adoção)
    Item("a dog", "cachorro", "animais", "adotar"),
    Item("a cat", "gato", "animais", "adotar"),
    Item("a rabbit", "coelho", "animais", "adotar"),
    Item("a bird", "pássaro", "animais", "adotar"),
    Item("a hamster", "hamster", "animais", "adotar"),
    Item("a guinea pig", "porquinho-da-índia", "animais", "adotar"),
    Item("a pet fish in an aquarium", "peixe de aquário", "animais", "adotar"),
    Item("a turtle", "tartaruga", "animais", "adotar"),
]

CATEGORIAS = sorted({i.categoria for i in ITENS})
