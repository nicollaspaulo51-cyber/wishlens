# 🔍 WishLens

> **Aponte. Fotografe. Descubra.**: um jogo de fotos do mundo real. Seu personagem anda no mapa, os lugares onde dá para achar cada tema piscam, e você fotografa carros, plantas, pássaros, cachorros e gatos ou peças de computador para ganhar pontos e subir no pódio.

Projeto final da disciplina **Ciência de Dados I (Turma 12)**, desenvolvido com a metodologia **CRISP-DM**.

![testes](https://github.com/nicollaspaulo51-cyber/wishlens/actions/workflows/testes.yml/badge.svg)

## O que é
| Página | O que faz |
|---|---|
| 🎯 **Jogar** (início) | Mapa com o **personagem** do WishLens (um explorador com uma lupa) na sua posição, andando com o GPS. Os lugares onde dá para achar cada tema **aparecem, piscam e somem**; os do tema do dia são maiores. Tocar num ponto mostra o que procurar ali e "Como chegar". Embaixo, **📷 Fotografar**: a foto é julgada e vira pontos na hora. |
| 🏆 **Pódio** | Ranking de hoje, da semana e geral, por tema, e os achados mais raros da semana. |
| 📚 **Minha Coleção** | Álbum por tema, raridade de cada achado, estilo de jogador (K-Means) e gráficos. |
| 📊 **Avaliação** | CLIP × IA: concordância de tema, matriz de confusão, vetos, motivos de recusa e contestações. |

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

### Mecânicas de caminhada (bônus fora do ×2)
| Mecânica | Regra |
|---|---|
| Mirante | foto a até 40 m de um lugar do mapa: +5, até 3 por dia. No mapa, o lugar pulsa quando você chega perto |
| Pista | ao tocar num lugar, o mapa mostra o que a turma já achou em lugares do mesmo tipo (parque, pet shop...) |
| Lupa | 3 temas diferentes no dia enchem a lupa; o achado seguinte ganha +50% |
| Desafios do dia | 3 por dia, iguais para todos (sorteados pela data): +15 cada |
| Corrente | 7 dias seguidos com foto aceita: +20 |
| Medalhas | 6 medalhas (5 temas + mirantes) em bronze (3), prata (8) e ouro (15) |
| Álbum com lacunas | o que a turma já achou e você não aparece só com a 1ª letra |
| Guardião do quadrado | quem tem mais achados diferentes num quadrado de ~500 m na semana (só onde 2+ pessoas jogaram) |
| Meta da turma | das 12h às 14h, 20 fotos do tema do dia pela turma: cada uma ganha +10 |
| Clima | com chuva ([Open-Meteo](https://open-meteo.com)), plantas e pássaros dão +5 (fora do tema do dia) |
| Mesmo objeto | o CLIP compara o "retrato" da foto com as suas fotos e as da turma no mesmo quadrado: o mesmo objeto de novo vale 0 para você; já fotografado pela turma, vale sem bônus de raridade |
| Foto borrada | se a foto está borrada e o CLIP fica em dúvida (nenhum grupo com 50% de chance), o app pede outra foto e não salva nada |
| Deslocamento impossível | mais de 3 km a mais de 120 km/h desde a sua foto anterior: a foto vale 0 |

O placar, a meta da turma e o pódio se atualizam sozinhos a cada 30 s; cada bônus e cada medalha nova aparecem como
aviso logo depois da foto.

### Dois juízes em toda foto
- **IA open source** (juiz principal, com a `VISAO_URL`): um modelo de visão com licença OSI, como o Qwen2.5-VL 7B
  ou o Mistral Small (Apache 2.0). Diz o tema, o achado (modelo do carro, espécie, raça, peça) e
  se é foto real. O prompt lista os sinais de foto de tela (borda do monitor, moiré, reflexo, bordas de janela).
- **CLIP** da OpenAI (`openai/clip-vit-base-patch32`), em **toda foto**: compara a foto com frases de cada tema e com
  frases "gêmeas" de tela ("a photo of a computer screen showing a bird"). Ele barra a foto se "tela" for o 1º palpite
  dele (exceto peças: monitor ligado é peça) ou se o tema da IA ficar fora dos 2 primeiros palpites dele.
  Usa a posição, não a chance, porque o CLIP é "confiante demais": uma diferença pequena de parecença vira 95% × 5%.
- Sem a IA, o CLIP julga sozinho e o achado é o objeto que mais combinou ("mouse", "teclado", "flor", "carro").
- O que cada modelo disse fica gravado. Quando o juiz erra, a pessoa pode **contestar** ("era um mouse!"):
  não ganha pontos, mas a contestação aparece na página Avaliação para melhorar o identificador.

## CRISP-DM
| Fase | Pergunta | Onde está |
|---|---|---|
| 1. Negócio | Como um jogo de fotos do mundo real faz as pessoas descobrirem coisas novas na cidade? Quais estilos de jogador existem? O que é raro e onde? | este README |
| 2. Dados | Capturas do jogo: tema, achado, hora, bairro, o que cada juiz disse ([dicionário](docs/DICIONARIO_DE_DADOS.md)) | `src/jogo.py`, CSV na página Avaliação |
| 3. Preparação | Normalização dos achados ("VW Gol" = "Volkswagen Gol"), foto repetida, vetor de perfil por tema | `src/jogo.py` |
| 4. Modelagem | K-Means (estilos de jogador por tema) + raridade pela frequência dos achados | `src/clustering.py`, `src/jogo.py` |
| 5. Avaliação | CLIP e IA concordam (matriz de confusão)? Taxa de fotos recusadas e contestadas? Privacidade (LGPD)? | página 📊 Avaliação |
| 6. Produto | Site publicado | `app/` |

Os notebooks `01`–`05` usam os dados do jogo (o `05` analisa as mecânicas: tema × tipo de lugar, clima,
deslocamento impossível e o peso dos bônus). Enquanto a turma não joga, leem `data/processed/capturas_demo.csv`
(fictício, `python -m src.exemplo`); com o CSV da página Avaliação salvo como `data/processed/avaliacao_juizes.csv`,
passam a usar os dados reais sozinhos.

## Arquitetura
```
Celular (GPS + câmera) → Streamlit
   ├─ mapa do jogo (Leaflet, no navegador): personagem, pontos que piscam, cartão do lugar
   ├─► OpenStreetMap / Overpass (onde procurar cada tema)
   ├─► IA open source por API compatível com a da OpenAI (juiz principal) + CLIP (segundo juiz, no servidor)
   └─► Supabase (capturas + login; sem a foto, só um hash)
Página Avaliação ──► CSV anonimizado ──► notebooks
```

**Em construção: app de celular.** O jogo está indo para um app nativo (Expo / React Native, em `app_celular/`).
O CLIP roda no **servidor do juiz** (`servidor/`, FastAPI, publicado no Hugging Face Spaces), que reaproveita
as mesmas regras de `src/`. Como publicar: [servidor/README.md](servidor/README.md).

## Fontes de dados e licenças
| Fonte | Uso | Licença |
|---|---|---|
| Fotos tiradas no jogo (autor + colegas, com consentimento) | capturas (a foto não é guardada) | uso no projeto, anonimizadas |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | mapa e lugares de cada tema | ODbL |
| [Leaflet](https://leafletjs.com/) | mapa no navegador | BSD-2 |
| [CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32) | segundo juiz das fotos | MIT |
| [Open-Meteo](https://open-meteo.com) | clima de agora (bônus de chuva) | dados CC-BY 4.0, API sem chave |
| [Qwen2.5-VL 7B](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) no [Ollama](https://ollama.com) ou [Mistral Small](https://huggingface.co/mistralai) pela API da Mistral | juiz principal | Apache 2.0 (Ollama: MIT) |

Todo o projeto usa só modelos com licença aprovada pela OSI. O Gemma, usado antes como juiz principal, saiu porque a
licença dele (Gemma Terms of Use) não é OSI.

O personagem do mapa é um desenho próprio do WishLens (SVG em `src/mapa_jogo.py`).

## Privacidade
- A foto **não é guardada**: só um hash de 16 caracteres para detectar foto repetida.
- A foto vai para a IA **já sem EXIF/GPS** e reduzida (`src/fotos.py`).
- O GPS move o personagem no seu navegador; o banco guarda só o bairro e um **quadrado de ~500 m** (`celula`) para o
  mapa da turma, nunca a coordenada exata. Hash e célula saem do CSV anonimizado.
- O pódio mostra só o apelido. Os jogadores logados veem tema, achado e hora das capturas dos outros (é o que permite
  o pódio e a raridade), mas **não** o bairro nem a célula: o mapa da turma vem de uma função do banco que só devolve
  totais por quadrado de ~500 m, sem dizer quem nem quando, e só onde houve pelo menos 2 capturas.
- As mecânicas gravam só o que sai da posição, nunca ela: se a foto foi num mirante (sim/não), o tipo de lugar, o clima
  e os km e minutos desde a sua foto anterior. O guardião mostra o apelido de quem guarda um quadrado, mas só na
  semana, só onde 2 pessoas ou mais jogaram e sem horário; a página Pódio mostra só quantos quadrados cada um guarda.
- Para o Open-Meteo vai só a coordenada arredondada (~1 km).
- Limite conhecido: mirante, clima e deslocamento são calculados no app, como o "foto real" da IA. Quem adulterar o
  app consegue forjá-los; para um jogo de turma isso é aceitável.

## Status
| Parte | Situação |
|---|---|
| Jogo: mapa com personagem, temas, pontos, pódio, coleção, avaliação | ✅ funcionando (testado com IA e mapa simulados) |
| Juízes (IA open source + CLIP) | 🧪 a testar com a chave real e fotos reais |
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

## IA open source (juiz principal)
`src/visao.py` fala com qualquer API compatível com a da OpenAI (`/chat/completions`). Só use modelos com licença OSI
(Apache 2.0, MIT). Formato completo em `.streamlit/secrets.toml.example`.

- **No computador (tudo local):** instale o [Ollama](https://ollama.com), rode `ollama pull qwen2.5vl:7b` e use
  `VISAO_URL = "http://localhost:11434/v1"`. Sem GPU, cada foto leva de 20 a 60 s.
- **No Streamlit Cloud** (não tem RAM para rodar o modelo): crie uma chave em https://console.mistral.ai e cole nos
  Secrets `VISAO_URL = "https://api.mistral.ai/v1"`, `VISAO_CHAVE = "sua-chave"` e `VISAO_MODELO = "mistral-small-latest"`.
- Atenção ao trocar de modelo: o Qwen2.5-VL 3B e o 72B **não** são Apache 2.0; o 7B e o 32B são.

Sem a `VISAO_URL`, ou se a API falhar, o app continua só com o CLIP e mostra o motivo em uma linha.
Capturas antigas, gravadas quando o juiz era o Gemma (`juiz = "gemma+clip"`), são lidas como `"ia+clip"`.

## Publicar no Streamlit Community Cloud
1. Entre em https://share.streamlit.io com a conta do GitHub e clique em **Create app**.
2. Repositório `nicollaspaulo51-cyber/wishlens`, a branch desejada, arquivo principal `app/Home.py`.
3. Em **Advanced settings**, escolha Python 3.12. O `requirements.txt` já instala o torch só-CPU.
4. Cole as chaves do Supabase e as da IA (`VISAO_URL`, `VISAO_CHAVE`, `VISAO_MODELO`) em **Secrets** no formato de `.streamlit/secrets.toml.example`.

A câmera e o GPS do navegador só funcionam em HTTPS (o Streamlit Cloud já usa) ou em `localhost`.

## Estrutura
```
app/            Jogar (Home) + páginas Pódio, Minha Coleção e Avaliação
servidor/       servidor do juiz para o app de celular (FastAPI + CLIP) e os arquivos do Space
src/            temas, jogo (pontos e pódio), mapa_jogo (personagem e mapa), visao (IA open source), reconhecimento (CLIP),
                lugares (OSM), localizacao, fotos, armazenamento/banco, clustering, exportação, interface
notebooks/      análise CRISP-DM do jogo (01 → 05)
data/processed/ dados de demonstração da versão anterior (fictícios)
supabase/       estrutura do banco (schema.sql)
docs/           roteiro de testes, dicionário de dados, guia do Supabase
tests/          testes automáticos (rodam no GitHub Actions a cada push)
```

## Roadmap
- [x] Jogo: temas, tema do dia, pontos, pódio, coleção
- [x] Mapa com personagem e pontos que piscam
- [x] Dois juízes (IA open source + CLIP) e página de Avaliação
- [x] Mecânicas de caminhada (mirantes, lupa, desafios, corrente, medalhas, guardiões, meta da turma, clima)
- [ ] Criar o projeto Supabase e jogar com a turma
- [x] Refazer os notebooks com os dados do jogo (fictícios)
- [ ] Rodar os notebooks com o CSV real da turma
- [ ] Publicar a versão final e gravar o vídeo
