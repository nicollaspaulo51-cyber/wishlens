# Como testar: marca, preço e cartão da loja

Branch: `claude/vibrant-feynman-4fhs11` (feita a partir de `feat/fluxo-completo`, a versão publicada).

## 1. Publicar uma cópia de teste (não mexe no app atual)
1. Entre em https://share.streamlit.io → **Create app**.
2. Repositório `nicollaspaulo51-cyber/wishlens`, branch **`claude/vibrant-feynman-4fhs11`**, arquivo `app/Home.py`.
3. Em **Advanced settings**: Python 3.12.
4. Deixe **sem** Secrets por enquanto (o passo 3 testa sem a chave).

## 2. Pegar a chave gratuita do Gemma
1. Abra https://aistudio.google.com/apikey e clique em **Create API key**.
2. Guarde a chave. Não cole em conversa nem no GitHub.

## 3. Teste A: sem chave (só CLIP)
| Faça | Deve acontecer |
|---|---|
| Foto de um tênis Nike com o logo aparecendo | Top-3 com "Tênis" (às vezes já "Tênis · Nike") |
| Foto de uma lata de Monster ou Coca-Cola | "Energético · Monster" / "Refrigerante · Coca-Cola" |
| Foto de um carro | "Carro" na frente de "camião", "aeronaves" etc. |
| Foto de uma cenoura | Aparece como comida (antes ia para "brinquedos") |
| "Outra coisa…" → nome "garrafa térmica", marca "Stanley", categoria "casa e decoração" | Cartão mostra "Garrafa térmica · Stanley" |
| Olhe o cartão do item | Preço com a fonte embaixo: "Mercado Livre, N anúncios" ou "referência" |

## 4. Teste B: com a chave (Gemma)
1. No app de teste: **⋮ → Settings → Secrets** e cole:
   ```
   GEMINI_API_KEY = "sua-chave"
   ```
2. Salve e espere o app reiniciar (~1 min).

| Faça | Deve acontecer |
|---|---|
| Foto de um produto com marca visível (tênis, celular, fone) | 1ª opção com ✨, ex.: "✨ Tênis · Nike Air Max 90" |
| Mesmo produto sem logo visível | ✨ sem marca (o Gemma não deve inventar) |
| Foto de um prato de comida | ✨ com o nome do prato; preço de porção, fonte "estimativa da IA" ou "referência" |
| Foto de um cachorro | Categoria animais, preço "adoção gratuita" |

Se aparecer **"⚠️ IA de marcas indisponível agora (API respondeu 404 …)"**, o modelo `gemma-3-27b-it` não está disponível
para a sua chave. Acrescente nos Secrets `GEMMA_MODELO = "gemma-3-12b-it"` (ou `"gemini-2.5-flash"`, que é fechado) e teste de novo.
Com "400/403 … API key not valid", a chave foi colada errada.

## 5. Teste C: cartão da loja
| Faça | Deve acontecer |
|---|---|
| Permita o GPS (ou digite um bairro) → **Buscar lugares próximos** | Mapa com marcadores coloridos e tabela com coluna "endereço" |
| Toque num marcador | Abaixo do mapa: cartão com nome, distância, endereço, horário em português (seg–sex…), telefone clicável, preço de referência |
| Toque em "🧭 Google Maps" / "🧭 Waze" | Abre a rota até a loja no app do celular |
| Toque numa linha da tabela | Abre o cartão da mesma loja |
| Arraste ou dê zoom no mapa | A página **não** recarrega |

Endereço, horário e telefone só aparecem quando a loja tem esses dados no OpenStreetMap. Quando não tem, o horário mostra "não informado no mapa".

## 6. Preço pelo Mercado Livre
Não deu para testar daqui (o sandbox bloqueia o site). Se a fonte do preço **nunca** aparecer como "Mercado Livre",
a API pública passou a exigir login. Nesse caso o app usa a estimativa da IA e depois a tabela, sem erro na tela.

## 7. Depois de aprovar
Peça o pull request de `claude/vibrant-feynman-4fhs11` → `feat/fluxo-completo`. Com o merge, o link atual do Streamlit
recebe as mudanças. Copie também a `GEMINI_API_KEY` para os Secrets do app atual.

## Já verificado aqui
- `python -m pytest -q tests/`: 44 passando (rede simulada: Gemma, Mercado Livre, Overpass e Nominatim).
- App rodando com a rede simulada: opção ✨ com marca, preço com fonte e cartão aberto pela tabela.
  O mapa não carregou aqui porque o Leaflet vem de um CDN bloqueado no sandbox; o clique no marcador
  usa o mesmo cartão, mas só dá para confirmar no app publicado.
- **Não** testado aqui: o CLIP de verdade (o Hugging Face está bloqueado), o Gemma real (falta a chave) e o Mercado Livre.
