# 🔍 WishLens

> **Point. Snap. Discover.**: um jogo de fotos do mundo real. Seu personagem anda no mapa, os lugares onde dá para achar cada tema piscam, e você fotografa carros, plantas, pássaros, cachorros e gatos ou peças de computador para ganhar pontos e subir no pódio.

Projeto final da disciplina **Ciência de Dados I (Turma 12)**, desenvolvido com a metodologia **CRISP-DM**.

![testes](https://github.com/nicollaspaulo51-cyber/wishlens/actions/workflows/testes.yml/badge.svg)

## O que é
| Página | O que faz |
|---|---|
| 🎯 **Jogar** (início) | Mapa com o **personagem** do WishLens (um explorador com uma lupa) na sua posição, andando com o GPS. Os lugares onde dá para achar cada tema **aparecem, piscam e somem**; os do tema do dia são maiores. Tocar num ponto mostra o que procurar ali e "Como chegar". Embaixo, **📷 Fotografar**: a foto é julgada e vira pontos na hora. |
| 🏆 **Pódio** | Ranking de hoje, da semana e geral, por tema, e os achados mais raros da semana. |
| 📚 **Minha Coleção** | Álbum por tema, raridade de cada achado, estilo de jogador (K-Means) e gráficos. |
| 📊 **Avaliação** | CLIP × Gemma: concordância de tema, matriz de confusão, vetos, motivos de recusa e contestações. |

### Temas e pontos
Temas (todos valem sempre): 🚗 carros · 🌿 plantas e flores · 🐦 pássaros · 🐶 cachorros e gatos · 🖥️ peças e periféricos de computador (mouse, teclado e monitor contam).
O **tema do dia** muda à meia-noite (rodízio pela data) e vale **o dobro**.

| Parcela | Pontos |
|---|---|
| Base | 10 |
| Novo pra você | +10 |
| Raridade | +20 ÷ (1 + vezes que a turma já achou): o 1º a achar ganha +20, o 2º +10, o 3º +7… |
| Tema do dia | tudo ×2 |
| Achado genérico (só "carro", sem o modelo) | só a base, até 3 vezes por tema por dia |
| Foto de tela/impressão, repetida (hash da imagem), fora dos temas ou mesma coisa no mesmo dia | 0, com o motivo |

Os pontos são **recalculados a partir das capturas** (`src/jogo.py`): gravar um número falso no banco não vale nada.

### Dois juízes em toda foto
- **Gemma** (juiz principal, com a `GEMINI_API_KEY`): diz o tema, o achado (modelo do carro, espécie, raça, peça) e
  se é foto real. O prompt lista os sinais de foto de tela (borda do monitor, moiré, reflexo, bordas de janela).
- **CLIP** da OpenAI (`openai/clip-vit-base-patch32`), em **toda foto**: compara a foto com frases de cada tema e com
  frases "gêmeas" de tela ("a photo of a computer screen showing a bird"). Ele barra a foto se "tela" for o 1º palpite
  dele (exceto peças: monitor ligado é peça) ou se o tema do Gemma ficar fora dos 2 primeiros palpites dele.
  Usa a posição, não a chance, porque o CLIP é "confiante demais": uma diferença pequena de parecença vira 95% × 5%.
- Sem a chave, o CLIP julga sozinho e o achado é o objeto que mais combinou ("mouse", "teclado", "flor", "carro").
- O que cada modelo disse fica gravado. Quando o juiz erra, a pessoa pode **contestar** ("era um mouse!"):
  não ganha pontos, mas a contestação aparece na página Avaliação para melhorar o identificador.

## CRISP-DM
| Fase | Pergunta | Onde está |
|---|---|---|
| 1. Negócio | Como um jogo de fotos do mundo real faz as pessoas descobrirem coisas novas na cidade? Quais estilos de jogador existem? O que é raro e onde? | este README |
| 2. Dados | Capturas do jogo: tema, achado, hora, bairro, o que cada juiz disse ([dicionário](docs/DICIONARIO_DE_DADOS.md)) | `src/jogo.py`, CSV na página Avaliação |
| 3. Preparação | Normalização dos achados ("VW Gol" = "Volkswagen Gol"), foto repetida, vetor de perfil por tema | `src/jogo.py` |
| 4. Modelagem | K-Means (estilos de jogador por tema) + raridade pela frequência dos achados | `src/clustering.py`, `src/jogo.py` |
| 5. Avaliação | CLIP e Gemma concordam (matriz de confusão)? Taxa de fotos recusadas e contestadas? Privacidade (LGPD)? | página 📊 Avaliação |
| 6. Produto | Site publicado | `app/` |

Os notebooks `01`–`04` usam os dados do jogo. Enquanto a turma não joga, leem `data/processed/capturas_demo.csv`
(fictício, `python -m src.exemplo`); com o CSV da página Avaliação salvo como `data/processed/avaliacao_juizes.csv`,
passam a usar os dados reais sozinhos.

## Arquitetura
```
Celular (GPS + câmera) → Streamlit
   ├─ mapa do jogo (Leaflet, no navegador): personagem, pontos que piscam, cartão do lugar
   ├─► OpenStreetMap / Overpass (onde procurar cada tema)
   ├─► Gemma via Google AI Studio (juiz principal) + CLIP (segundo juiz, no servidor)
   └─► Supabase (capturas + login; sem a foto, só um hash)
Página Avaliação ──► CSV anonimizado ──► notebooks
```

## Fontes de dados e licenças
| Fonte | Uso | Licença |
|---|---|---|
| Fotos tiradas no jogo (autor + colegas, com consentimento) | capturas (a foto não é guardada) | uso no projeto, anonimizadas |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | mapa e lugares de cada tema | ODbL |
| [Leaflet](https://leafletjs.com/) | mapa no navegador | BSD-2 |
| [CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32) | segundo juiz das fotos | MIT |
| [Gemma 3](https://ai.google.dev/gemma) (pela API do Google AI Studio) | juiz principal | pesos abertos, [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (não é licença OSI) |

O personagem do mapa é um desenho próprio do WishLens (SVG em `src/mapa_jogo.py`).

## Privacidade
- A foto **não é guardada**: só um hash de 16 caracteres para detectar foto repetida.
- Com o Gemma ligado, a foto vai para a API do Google **já sem EXIF/GPS** e reduzida (`src/fotos.py`).
- O GPS move o personagem no seu navegador; o banco guarda só o bairro e um **quadrado de ~500 m** (`celula`) para o
  mapa da turma, nunca a coordenada exata. Hash e célula saem do CSV anonimizado.
- O pódio mostra só o apelido. Os jogadores logados veem tema, achado e hora das capturas dos outros (é o que permite
  o pódio e a raridade), mas **não** o bairro nem a célula: o mapa da turma vem de uma função do banco que só devolve
  totais por quadrado de ~500 m, sem dizer quem nem quando, e só onde houve pelo menos 2 capturas.

## Status
| Parte | Situação |
|---|---|
| Jogo: mapa com personagem, temas, pontos, pódio, coleção, avaliação | ✅ funcionando (testado com IA e mapa simulados) |
| Juízes (Gemma + CLIP) | 🧪 a testar com a chave real e fotos reais |
| Banco e login (Supabase) | ⏳ código e SQL prontos, **não testados** com um projeto real: ver [docs/SUPABASE.md](docs/SUPABASE.md) |
| Notebooks do CRISP-DM | ✅ refeitos com os dados do jogo e executados, **com dados fictícios**; rodar de novo com o CSV real |
| Coleta de dados reais com a turma | ⏳ a fazer |

## Documentação
- [Como testar o jogo](docs/TESTAR_JOGO.md)
- [Dicionário de dados](docs/DICIONARIO_DE_DADOS.md)
- [Configurar o Supabase](docs/SUPABASE.md)
- [Plano do projeto](docs/PLANO.md) e [roteiro do vídeo](docs/ROTEIRO_VIDEO.md) (da versão anterior)

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```
Sem o CLIP (instalação bem mais leve, sem `torch`): `pip install -r requirements-dev.txt`. Sem nenhum juiz, o jogo
pede para a pessoa dizer o tema e o que fotografou.

Testes (sem internet): `python -m pytest tests/` (o teste do CLIP real é pulado sem `torch` ou sem internet).

## Gemma (juiz principal)
1. Crie uma chave gratuita em https://aistudio.google.com/apikey.
2. No Streamlit Cloud: **Settings → Secrets** e cole `GEMINI_API_KEY = "sua-chave"` (formato em `.streamlit/secrets.toml.example`).
3. O modelo padrão é `gemma-3-27b-it` (pesos abertos). Se o Google deixar de servir esse modelo, defina `GEMMA_MODELO`
   nos Secrets (ex.: `gemma-3-12b-it`, ou `gemini-2.5-flash`, que é fechado).

Sem chave, ou se a API falhar, o app continua só com o CLIP e mostra o motivo em uma linha.

## Publicar no Streamlit Community Cloud
1. Entre em https://share.streamlit.io com a conta do GitHub e clique em **Create app**.
2. Repositório `nicollaspaulo51-cyber/wishlens`, a branch desejada, arquivo principal `app/Home.py`.
3. Em **Advanced settings**, escolha Python 3.12. O `requirements.txt` já instala o torch só-CPU.
4. Cole as chaves do Supabase e a `GEMINI_API_KEY` em **Secrets** no formato de `.streamlit/secrets.toml.example`.

A câmera e o GPS do navegador só funcionam em HTTPS (o Streamlit Cloud já usa) ou em `localhost`.

## Estrutura
```
app/            Jogar (Home) + páginas Pódio, Minha Coleção e Avaliação
src/            temas, jogo (pontos e pódio), mapa_jogo (personagem e mapa), visao (Gemma), reconhecimento (CLIP),
                lugares (OSM), localizacao, fotos, armazenamento/banco, clustering, exportação, interface
notebooks/      análise CRISP-DM do jogo (01 → 04)
data/processed/ dados de demonstração da versão anterior (fictícios)
supabase/       estrutura do banco (schema.sql)
docs/           roteiro de testes, dicionário de dados, guia do Supabase
tests/          testes automáticos (rodam no GitHub Actions a cada push)
```

## Roadmap
- [x] Jogo: temas, tema do dia, pontos, pódio, coleção
- [x] Mapa com personagem e pontos que piscam
- [x] Dois juízes (Gemma + CLIP) e página de Avaliação
- [ ] Criar o projeto Supabase e jogar com a turma
- [x] Refazer os notebooks com os dados do jogo (fictícios)
- [ ] Rodar os notebooks com o CSV real da turma
- [ ] Publicar a versão final e gravar o vídeo
