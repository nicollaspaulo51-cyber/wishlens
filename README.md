# 🔍 WishLens

> **Point. Snap. Discover.**: um jogo de fotos do mundo real. Fotografe carros, plantas, pássaros, cachorros e gatos ou peças de computador, ganhe pontos e suba no pódio.

Projeto final da disciplina **Ciência de Dados I (Turma 12)**, desenvolvido com a metodologia **CRISP-DM**.

![testes](https://github.com/nicollaspaulo51-cyber/wishlens/actions/workflows/testes.yml/badge.svg)

## O que é
| Página | O que faz |
|---|---|
| 🎯 **Jogar** (início) | Tema do dia em destaque. A pessoa tira uma foto **com a câmera do app**; a IA diz o tema e o achado (ex.: "Volkswagen Fusca", "bem-te-vi") e se é foto real. Mostra os pontos na hora. |
| 🗺️ **Explorar** | Mapa com pontos **piscando** onde procurar cada tema (parques, estacionamentos, pet shops… do OpenStreetMap) e onde a turma já achou coisas. O tema do dia pisca mais forte. |
| 🏆 **Pódio** | Ranking de hoje, da semana e geral, por tema, e os achados mais raros da semana. |
| 📚 **Minha Coleção** | Álbum por tema, raridade de cada achado, estilo de jogador (K-Means) e gráficos. |
| 🔎 **Onde encontrar** | Depois de uma captura: preço, lojas online e lugares próximos (a parte de compras do WishLens original). |
| ⭐ Meus Desejos · ✨ Descobrir · 👥 Comparar | Páginas da versão anterior (desejos de consumo), mantidas. |

### Temas e pontos
Temas (todos valem sempre): 🚗 carros · 🌿 plantas e flores · 🐦 pássaros · 🐶 cachorros e gatos · 🖥️ peças de computador.
O **tema do dia** muda à meia-noite (rodízio pela data) e vale **o dobro**.

| Parcela | Pontos |
|---|---|
| Base | 10 |
| Novo pra você | +10 |
| Raridade | +20 ÷ (1 + vezes que a turma já achou): o 1º a achar ganha +20, o 2º +10, o 3º +7… |
| Tema do dia | tudo ×2 |
| Achado genérico (só "carro", sem o modelo) | só a base |
| Foto de tela/impressão, repetida (hash da imagem), fora dos temas ou mesma coisa no mesmo dia | 0, com o motivo |

Os pontos são **recalculados a partir das capturas** (`src/jogo.py`): gravar um número falso no banco não vale nada.

## CRISP-DM
| Fase | Pergunta | Onde está |
|---|---|---|
| 1. Negócio | Como um jogo de fotos do mundo real faz as pessoas descobrirem coisas novas na cidade? Quais estilos de jogador existem? O que é raro e onde? | este README + `notebooks/01_entendimento.ipynb` |
| 2. Dados | Quais dados temos, de onde vêm, quais limitações? (`describe()`, distribuições, nulos) | `notebooks/01_entendimento.ipynb` |
| 3. Preparação | Limpeza, categorias unificadas, vetor de perfil por usuário | `notebooks/02_preparacao.ipynb` |
| 4. Modelagem | K-Means (perfis de desejo e estilos de jogador por tema) + similaridade do cosseno + raridade pela frequência dos achados | `notebooks/03_modelagem.ipynb`, `src/jogo.py` |
| 5. Avaliação | Os perfis fazem sentido? Acurácia da IA nos achados? Taxa de fotos recusadas? Privacidade (LGPD)? | `notebooks/04_avaliacao.ipynb` |
| 6. Produto | Site publicado | `app/` |

## Arquitetura
```
Usuário (foto/câmera) → Streamlit → CLIP (reconhecimento, modelo aberto, sempre)
                              ├─► Gemma via Google AI Studio (opcional: marca, modelo e preço)
                              ├─► Mercado Livre (preço pelos anúncios, quando a API responde)
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
| [Gemma 3](https://ai.google.dev/gemma) (opcional, pela API do Google AI Studio) | marca, modelo e preço estimado | pesos abertos, [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (não é licença OSI) |
| [API do Mercado Livre](https://developers.mercadolivre.com.br/) | faixa de preço pelos anúncios | termos do Mercado Livre |
| [LVIS v1](https://www.lvisdataset.org/) (lista de ~1.200 objetos) | vocabulário do reconhecimento (`data/vocabulario.csv`) | CC BY 4.0 |
| [Open Multilingual Wordnet](https://omwn.org/) / OpenWN-PT | nomes em português do vocabulário | CC BY-SA |

## Privacidade
- A foto salva é reduzida e **não carrega EXIF/GPS** (`src/fotos.py`).
- A localização é usada só para buscar lugares próximos; o banco guarda apenas cidade/bairro.
- O CSV versionado no GitHub é **anonimizado**; fotos brutas nunca entram no repositório (`.gitignore`).
- A comparação entre duas pessoas exige **aceite das duas**.
- Com o Gemma ligado, a foto vai para a API do Google **já sem EXIF/GPS** e reduzida (a mesma de `preparar_para_salvar`).
- No jogo, cada captura guarda o bairro e um **quadrado de ~500 m** (`celula`) para o mapa da turma, nunca a coordenada exata.
  A foto em si não é guardada, só um hash de 16 caracteres para detectar foto repetida. Os dois saem do CSV anonimizado.
- O pódio mostra só o apelido. Todos os jogadores logados veem as capturas dos outros (é o que permite o pódio e a raridade).

## Status

| Parte | Situação |
|---|---|
| Interface (Home, Meus Desejos, Descobrir, Comparar) com tema claro/escuro | ✅ funcionando |
| Feed "Descobrir" (recomendações por perfil + pessoas parecidas) | ✅ funcionando |
| Gráficos dos desejos, perfil por K-Means, comparação por cosseno | ✅ funcionando |
| Notebooks 01–04 do CRISP-DM | ✅ executados, **com dados fictícios** |
| CSV anonimizado (download no app) | ✅ funcionando |
| Reconhecimento automático (CLIP) | ✅ ~1.070 rótulos: catálogo curado (com frases de ~40 marcas conhecidas) + 947 do LVIS com categorias revisadas (`data/vocabulario.csv`); "Outra coisa…" aceita texto livre e marca. Acurácia em fotos reais ainda não medida |
| Marca, modelo e preço com IA (Gemma) | 🧪 opcional: só com `GEMINI_API_KEY` nos Secrets; sem chave, só o CLIP |
| Preço | 🧪 Mercado Livre (quartis dos anúncios) → estimativa da IA → tabela de referência; a fonte aparece junto do preço |
| Cartão do lugar no mapa | ✅ endereço, horário, telefone, site, preço de referência e "Como chegar" (Google Maps, Waze, OSM) |
| Banco e login (Supabase) | ⏳ código e SQL prontos, **não testados** com um projeto real: ver [docs/SUPABASE.md](docs/SUPABASE.md) |
| Localização (GPS da foto → GPS do navegador → endereço via Nominatim) | ✅ funcionando |
| Lugares próximos (OpenStreetMap / Overpass, mapa com tiles OSM) | ✅ funcionando (servidor `overpass.openstreetmap.fr` primeiro; reserva: outros Overpass e Nominatim) |
| Coleta de dados reais com a turma | ⏳ a fazer |
| Publicação no Streamlit Cloud | ⏳ a fazer (precisa de conta) |

## Documentação
- [Prévia da interface](docs/previa.html): página estática, baixe e abra no navegador (dados fictícios)
- [Plano do projeto](docs/PLANO.md)
- [Dicionário de dados](docs/DICIONARIO_DE_DADOS.md)
- [Roteiro do vídeo](docs/ROTEIRO_VIDEO.md)
- [Configurar o Supabase](docs/SUPABASE.md)

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```
Sem o reconhecimento automático (instalação bem mais leve, sem `torch`):
```bash
pip install -r requirements-dev.txt
```
Testes (sem internet): `python -m pytest tests/` (o teste do CLIP é pulado se `torch` não estiver instalado)

## Vocabulário do reconhecimento
`data/vocabulario.csv` e `data/vocabulario_clip.npy` são gerados por `scripts/gerar_vocabulario.py`
(LVIS + nomes em português do Open Multilingual Wordnet; categoria pela hierarquia do WordNet).
Só é preciso rodar de novo se mudar o modelo ou as regras: `pip install nltk && python scripts/gerar_vocabulario.py`.
A categoria automática erra (cenoura caía em "brinquedos", gaiola em "veículos"); as correções manuais ficam em
`scripts/correcoes_vocabulario.py` e valem sem recalcular o CLIP: `python scripts/correcoes_vocabulario.py`.

## Juiz com IA: Gemma (recomendado para o jogo)
Sem a chave, o jogo usa o CLIP só para dizer o **tema** e se a foto é de tela; o achado fica genérico ("carro") e vale só a base.
Com a `GEMINI_API_KEY`, o Gemma diz o modelo do carro, a espécie da planta ou do pássaro, a raça e a peça.

## Marca, modelo e preço com o Gemma (opcional)
1. Crie uma chave gratuita em https://aistudio.google.com/apikey.
2. No Streamlit Cloud: **Settings → Secrets** e cole `GEMINI_API_KEY = "sua-chave"` (formato em `.streamlit/secrets.toml.example`).
3. O modelo padrão é `gemma-3-27b-it` (pesos abertos). Se o Google deixar de servir esse modelo, ou para comparar,
   defina `GEMMA_MODELO` nos Secrets (ex.: `gemma-3-12b-it`, ou `gemini-2.5-flash`, que é fechado).

Sem chave, ou se a API falhar, o app continua só com o CLIP e mostra o motivo em uma linha.

## Publicar no Streamlit Community Cloud
1. Entre em https://share.streamlit.io com a conta do GitHub e clique em **Create app**.
2. Repositório `nicollaspaulo51-cyber/wishlens`, branch `main`, arquivo principal `app/Home.py`.
3. Em **Advanced settings**, escolha Python 3.12. O `requirements.txt` já instala o torch só-CPU.
4. (Opcional) Cole as chaves do Supabase e a `GEMINI_API_KEY` em **Secrets** no formato de `.streamlit/secrets.toml.example`.

A câmera e o GPS do navegador só funcionam em HTTPS (o Streamlit Cloud já usa) ou em `localhost`.

## Estrutura
```
app/            site Streamlit (Home + páginas Meus Desejos, Descobrir e Comparar)
src/            reconhecimento, fotos, localizacao, lugares, links, catálogo, armazenamento/banco,
                perfil (cosseno), clustering (K-Means), feed de recomendações, exportação, interface
notebooks/      análise CRISP-DM (01 → 04)
data/processed/ dados de demonstração (fictícios) e, depois, os anonimizados reais
supabase/       estrutura do banco (schema.sql)
docs/           plano, dicionário de dados, roteiro do vídeo, guia do Supabase
tests/          testes automáticos (rodam no GitHub Actions a cada push)
```

## Roadmap
- [x] Estrutura, catálogo de itens, fotos sem GPS, links, código do reconhecimento (CLIP) e dos lugares (OSM)
- [x] Interface: Home, Meus Desejos (gráficos) e Comparar (similaridade do cosseno), tema claro/escuro
- [x] Clustering de perfis (K-Means) + cartão "Seu perfil"
- [x] Notebooks 01–04 do CRISP-DM (com dados fictícios)
- [x] Código do login + banco (Supabase) e exportação anonimizada
- [ ] Criar o projeto Supabase e testar o login
- [x] Instalar o CLIP (torch só-CPU) e localização por GPS do navegador / endereço
- [ ] Medir a acurácia do reconhecimento em fotos reais
- [ ] Coleta com colegas → refazer os notebooks com `desejos.csv`
- [ ] Publicar no Streamlit Cloud
- [ ] Gravar o vídeo ([roteiro](docs/ROTEIRO_VIDEO.md))
