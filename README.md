# 🔍 WishLens

> **Point. Snap. Want.**: aponte a câmera para qualquer coisa e descubra onde conseguir, o que você deseja e com quem você combina.

Projeto final da disciplina **Ciência de Dados I (Turma 12)**, desenvolvido com a metodologia **CRISP-DM**.

## O que é
Um site em que a pessoa **tira uma foto ou aponta a câmera** para qualquer coisa:

| Reconheceu… | O WishLens mostra |
|---|---|
| 🛍️ algo comprável (roupa, objeto, eletrônico) | lojas físicas próximas + lojas online |
| 🍲 comida | receitas, restaurantes próximos e delivery |
| 🐶 animal | abrigos, pet shops e veterinários próximos (adoção) |

Cada busca vira um **registro de desejo**. Com eles, o app gera **gráficos dos seus desejos de consumo** e permite **comparar seu perfil com o de outra pessoa** (com aceite das duas).

## CRISP-DM
| Fase | Pergunta | Onde está |
|---|---|---|
| 1. Negócio | As pessoas não têm um lugar único para descobrir onde conseguir o que desejam, nem para entender os próprios padrões de desejo. Quais perfis de desejo existem? O quanto duas pessoas se parecem? | este README + `notebooks/01_entendimento.ipynb` |
| 2. Dados | Quais dados temos, de onde vêm, quais limitações? (`describe()`, distribuições, nulos) | `notebooks/01_entendimento.ipynb` |
| 3. Preparação | Limpeza, categorias unificadas, vetor de perfil por usuário | `notebooks/02_preparacao.ipynb` |
| 4. Modelagem | K-Means (perfis de desejo) + similaridade do cosseno (comparar pessoas) | `notebooks/03_modelagem.ipynb` |
| 5. Avaliação | Os perfis fazem sentido? Acurácia do reconhecimento? Privacidade (LGPD)? | `notebooks/04_avaliacao.ipynb` |
| 6. Produto | Site publicado | `app/` |

## Arquitetura
```
Usuário (foto/câmera) → Streamlit → CLIP (reconhecimento, modelo aberto)
                              ├─► Supabase (banco de desejos + fotos sem GPS + login)
                              └─► OpenStreetMap / Overpass (lugares próximos)
Notebooks de análise ◄── CSV anonimizado (data/processed/)
```

## Fontes de dados e licenças
| Fonte | Uso | Licença |
|---|---|---|
| Fotos coletadas pelo app (autor + colegas, com consentimento) | dados de desejo reais | uso no projeto, anonimizados |
| [Olist – Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) | base complementar de consumo | CC BY-NC-SA 4.0 |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | lugares próximos | ODbL |
| [CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32) | reconhecimento de imagens | MIT |

## Privacidade
- A foto salva é reduzida e **não carrega EXIF/GPS** (`src/fotos.py`).
- A localização é usada só para buscar lugares próximos; o banco guarda apenas cidade/bairro.
- O CSV versionado no GitHub é **anonimizado**; fotos brutas nunca entram no repositório (`.gitignore`).
- A comparação entre duas pessoas exige **aceite das duas**.

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```
Testes (sem internet): `python -m pytest tests/`

## Estrutura
```
app/            site Streamlit (Home + páginas)
src/            reconhecimento, fotos, lugares, links, catálogo de categorias
notebooks/      análise CRISP-DM (01 → 04)
data/processed/ dados anonimizados para a análise
tests/          testes automáticos
```

## Roadmap
- [x] Estrutura, catálogo de itens, reconhecimento (CLIP), fotos sem GPS, lugares (OSM), links
- [ ] Login + salvar desejos no Supabase
- [x] Interface: Home, Meus Desejos (gráficos) e Comparar (similaridade do cosseno), com dados de exemplo
- [ ] Coleta com colegas + EDA (Olist + dados do app)
- [ ] Clustering de perfis
- [ ] Avaliação e vídeo final
