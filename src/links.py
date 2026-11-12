"""Links de busca em lojas online, receitas, delivery e adoção.

Não usamos dados dessas empresas: apenas montamos links de busca públicos.
"""

from urllib.parse import quote_plus

from src.categorias import Item, termo_de_busca


def links_para(item: Item) -> dict[str, str]:
    termo = quote_plus(item.nome)
    if item.tipo == "comprar":
        busca = termo_de_busca(item)  # com marca/modelo: busca o produto certo, não a categoria
        termo = quote_plus(busca)
        return {
            "Mercado Livre": f"https://lista.mercadolivre.com.br/{quote_plus(busca.replace(' ', '-'))}",
            "Amazon": f"https://www.amazon.com.br/s?k={termo}",
            "Magazine Luiza": f"https://www.magazineluiza.com.br/busca/{termo}/",
            "Google Shopping": f"https://www.google.com/search?tbm=shop&q={termo}",
        }
    if item.tipo == "receita":
        termo = quote_plus(termo_de_busca(item))
        return {
            "Receitas (TudoGostoso)": f"https://www.tudogostoso.com.br/busca?q={termo}",
            "Receitas (Google)": f"https://www.google.com/search?q=receita+de+{termo}",
            "Delivery (iFood)": f"https://www.ifood.com.br/busca?q={termo}",
        }
    if item.tipo == "adotar":
        return {
            "Adoção (Google)": f"https://www.google.com/search?q=adoção+de+{termo}+perto+de+mim",
            "Instagram #adote": f"https://www.instagram.com/explore/tags/adote{termo.replace('+', '')}/",
        }
    return {}
