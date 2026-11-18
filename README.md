# WishLens

WishLens é um jogo em que você fotografa achados dos temas do jogo para ganhar pontos. O mapa mostra sua posição e indica lugares próximos onde procurar.

Projeto final da disciplina **Ciência de Dados I (Turma 12)**, desenvolvido com a metodologia **CRISP-DM**.

![testes](https://github.com/nicollaspaulo51-cyber/wishlens/actions/workflows/testes.yml/badge.svg)

## O que é
| Página | O que faz |
|---|---|
| **Jogar** (início) | Mapa com sua posição e marcadores de lugares próximos. Toque num marcador para ver o que procurar ali e como chegar. Use **Fotografar** para enviar uma foto para avaliação. |
| **Pódio** | Ranking de hoje, da semana e geral, por tema, e os achados mais raros da semana. |
| **Minha Coleção** | Álbum por tema, raridade de cada achado, estilo de jogador (K-Means) e gráficos. |
| **Avaliação** | CLIP × IA: concordância de tema, matriz de confusão, vetos, motivos de recusa e contestações. |

A interface segue a identidade de mapa topográfico sóbrio, com neutros frios de pedra e laranja de sinalização de trilha. Veja os detalhes no [README do app](app_celular/README.md#identidade-visual).

### Temas e pontos
Os cinco temas do **Mapa livre** vêm de `src/temas.py` e valem todos os dias. O **tema do dia** muda à meia-noite (horário de Brasília), em rodízio pela data, e vale **o dobro**.

| Tema | O que conta |
|---|---|
| Carros | Carros, caminhonetes e SUVs de verdade. |
| Plantas e flores | Plantas vivas, como árvores, flores, suculentas e cactos. |
| Frutas e comidas | Frutas, legumes e comidas de verdade, como manga, pão e coxinha. |
| Animais | Animais vivos, incluindo aves, cachorros, gatos, insetos e peixes. |
| Peças e periféricos de computador | Peças internas e periféricos, como placa de vídeo, mouse, teclado e monitor. |

**Frutas e comidas** entrou no rodízio no lugar de **Pássaros**. Novas fotos de aves entram em **Animais**; capturas antigas de **Pássaros** continuam valendo e aparecem na coleção e no Museu.

Fora do Mapa livre, os modos **Paisagens**, **Treino ao ar livre**, **Academias** e **Competição** têm regras de avaliação e pódios próprios. Em **Competição**, a foto é da tela de fim de partida e deve mostrar vitória ou derrota.

| Parcela | Pontos |
|---|---|
| Base | 10 |
| Novo pra você | +10 |
| Raridade | +20 ÷ (1 + vezes que a turma já achou): o 1º a achar ganha +20, o 2º +10, o 3º +7… |
| Tema do dia | tudo ×2 |
| Achado genérico (só "carro", sem o modelo) | só a base, até 3 vezes por tema por dia |
| Foto de tela ou impressão, repetida (hash da imagem), fora dos temas ou do mesmo achado no mesmo dia | 0, com o motivo. Um monitor real conta em Peças e periféricos de computador. |

Os pontos são **recalculados a partir das capturas** (`src/jogo.py`): gravar um número falso no banco não vale nada.

### Mecânicas de caminhada (bônus fora do ×2)
| Mecânica | Regra |
|---|---|
| Mirante | foto a até 40 m de um lugar do mapa: +5, até 3 por dia. No mapa, o lugar pulsa quando você chega perto |
| Pista | ao tocar num lugar, o mapa mostra o que a turma já achou em lugares do mesmo tipo (parque, pet shop...) |
| Lupa | 3 temas diferentes no dia enchem a lupa; o achado seguinte ganha +50% |
| Desafios do dia | 3 por dia, iguais para todos (sorteados pela data): +15 cada |
| Corrente | 7 dias seguidos com foto aceita: +20 |
| Medalhas | Bronze com 3, prata com 8 e ouro com 15. Veja o que cada medalha conta abaixo. |
| Álbum com lacunas | o que a turma já achou e você não aparece só com a 1ª letra |
| Guardião do quadrado | quem tem mais achados diferentes num quadrado de ~500 m na semana (só onde 2+ pessoas jogaram) |
| Meta da turma | das 12h às 14h, 20 fotos do tema do dia pela turma: cada uma ganha +10 |
| Clima | com chuva ([Open-Meteo](https://open-meteo.com)), achados de Plantas e flores ou Animais dão +5 quando não são do tema do dia |
| Mesmo objeto | o CLIP compara o "retrato" da foto com as suas fotos e as da turma no mesmo quadrado: o mesmo objeto de novo vale 0 para você; já fotografado pela turma, vale sem bônus de raridade |
| Foto borrada | se a foto está borrada e o CLIP fica em dúvida (nenhum grupo com 50% de chance), o app pede outra foto e não salva nada |
| Deslocamento impossível | mais de 3 km a mais de 120 km/h desde a sua foto anterior: a foto vale 0 |

As medalhas por tema contam achados aceitos, diferentes e não genéricos. A medalha Andarilho conta fotos aceitas tiradas em mirantes.

| Medalha | O que conta |
|---|---|
| Garagem cheia | Carros diferentes |
| Mão verde | Plantas diferentes |
| Bom garfo | Comidas diferentes |
| Amigo dos bichos | Animais diferentes |
| Garimpo tech | Peças diferentes |
| Andarilho | Fotos em mirantes |

O placar, a meta da turma e o pódio se atualizam a cada 30 s; os bônus e as novas medalhas aparecem como aviso logo depois da foto.

### Dois juízes em toda foto
- **IA open source** (juiz principal, com a `VISAO_URL`): um modelo de visão com licença OSI, como o Qwen2.5-VL 7B
  ou o Mistral Small (Apache 2.0). Diz o tema, o achado (modelo do carro, espécie, raça, comida ou peça) e
  se é foto real. O prompt lista os sinais de foto de tela (borda do monitor, moiré, reflexo, bordas de janela).
- **CLIP** da OpenAI (`openai/clip-vit-base-patch32`), em **toda foto**: compara a foto com frases de cada tema e com
  frases "gêmeas" de tela ("a photo of a computer screen showing a bird"). Ele barra a foto se "tela" for o 1º palpite
  dele (exceto se a tela for permitida, como em Peças e periféricos de computador e em Competição) ou se o tema da IA ficar fora dos 2 primeiros palpites dele.
  Usa a posição, não a chance, porque o CLIP é "confiante demais": uma diferença pequena de parecença vira 95% × 5%.
- Sem a IA, o CLIP julga sozinho e o achado é o objeto que mais combinou ("mouse", "teclado", "flor", "carro").
- O que cada modelo disse fica gravado. Quando o juiz erra, a pessoa pode **contestar** ("era um mouse!"):
  não ganha pontos, mas a contestação fica gravada (coluna `contestada`) para melhorar o identificador.

## CRISP-DM
| Fase | Pergunta | Onde está |
|---|---|---|
| 1. Negócio | Como um jogo de fotos do mundo real faz as pessoas descobrirem coisas novas na cidade? Quais estilos de jogador existem? O que é raro e onde? | este README |
| 2. Dados | Capturas do jogo: tema, achado, hora, bairro, o que cada juiz disse ([dicionário](docs/DICIONARIO_DE_DADOS.md)) | `src/jogo.py`, CSV de `python -m src.exportar` |
| 3. Preparação | Normalização dos achados ("VW Gol" = "Volkswagen Gol"), foto repetida, vetor de perfil por tema | `src/jogo.py` |
| 4. Modelagem | K-Means (estilos de jogador por tema) + raridade pela frequência dos achados | `src/clustering.py`, `src/jogo.py` |
| 5. Avaliação | CLIP e IA concordam (matriz de confusão)? Taxa de fotos recusadas e contestadas? Privacidade (LGPD)? | `src/jogo.py` (`avaliar_juizes`), notebook `04` |
| 6. Produto | App de celular + servidor do juiz | `app_celular/`, `servidor/` |

Os notebooks `01`–`05` usam os dados do jogo (o `05` analisa as mecânicas: tema × tipo de lugar, clima,
deslocamento impossível e o peso dos bônus). Enquanto a turma não joga, leem `data/processed/capturas_demo.csv`
(fictício, `python -m src.exemplo`); com os dados reais (exporte a tabela `capturas` no Supabase e rode `python -m src.exportar capturas_rows.csv`,
que grava `data/processed/avaliacao_juizes.csv` anonimizado), passam a usar os dados reais sozinhos.

## Arquitetura
```
App de celular (Expo / React Native, app_celular/): mapa nativo, câmera, pódio, álbum
   │ foto + GPS (só no pedido)
   ▼
Servidor do juiz (FastAPI + CLIP, servidor/) numa máquina da turma (Docker)
   ├─► regras do jogo (src/jogo.py): pontos, pódio, raridade, mecânicas
   ├─► OpenStreetMap / Overpass (onde procurar cada tema) e Open-Meteo (clima)
   └─► Supabase (capturas + login, com o token da própria pessoa; sem a foto, só um hash)
Supabase ──► CSV anonimizado (python -m src.exportar) ──► notebooks
```
Tudo é open source, inclusive onde roda: Linux, Docker e Caddy. Como subir o juiz: [servidor/README.md](servidor/README.md).
Como abrir o app: [app_celular/README.md](app_celular/README.md).

## Fontes de dados e licenças
| Fonte | Uso | Licença |
|---|---|---|
| Fotos tiradas no jogo (autor + colegas, com consentimento) | capturas (a foto não é guardada) | uso no projeto, anonimizadas |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | mapa e lugares de cada tema | ODbL |
| [CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32) | segundo juiz das fotos | MIT |
| [Open-Meteo](https://open-meteo.com) | clima de agora (bônus de chuva) | dados CC-BY 4.0, API sem chave |
| [Qwen2.5-VL 7B](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) no [Ollama](https://ollama.com) ou [Mistral Small](https://huggingface.co/mistralai) pela API da Mistral | juiz principal | Apache 2.0 (Ollama: MIT) |

Todo o projeto usa só modelos com licença aprovada pela OSI. O Gemma, usado antes como juiz principal, saiu porque a
licença dele (Gemma Terms of Use) não é OSI.

## Privacidade
- A foto **não é guardada**: só um hash de 16 caracteres para detectar foto repetida.
- A foto vai para a IA **já sem EXIF/GPS** e reduzida (`src/fotos.py`).
- O GPS mostra você no mapa do celular e vai ao servidor só no pedido; o banco guarda só o bairro e um **quadrado de ~500 m** (`celula`) para o
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
| Jogo: mapa com posição do jogador, temas, pontos, pódio, coleção, avaliação | Funciona com IA e mapa simulados |
| Juízes (IA open source + CLIP) | Falta testar com credenciais e fotos reais |
| Banco e login (Supabase) | Código e SQL prontos, **não testados** com um projeto real: ver [docs/SUPABASE.md](docs/SUPABASE.md) |
| Notebooks do CRISP-DM | Executados **com dados fictícios**; falta rodar com o CSV real |
| Coleta de dados reais com a turma | A fazer |

## Documentação
- [Dicionário de dados](docs/DICIONARIO_DE_DADOS.md)
- [Configurar o Supabase](docs/SUPABASE.md)
- [Plano do projeto](docs/PLANO.md) e [roteiro do vídeo](docs/ROTEIRO_VIDEO.md) (da versão anterior)

## Como rodar
- **Juiz:** `cd servidor && docker compose up -d --build` (detalhes em [servidor/README.md](servidor/README.md)).
- **App:** `cd app_celular && npm install && npx expo start`, e abra no Expo Go.
- **Análise e testes** (sem torch): `pip install -r requirements-dev.txt` e `python -m pytest tests/`
  (o teste do CLIP real é pulado sem `torch` ou sem internet).

## IA open source (juiz principal)
`src/visao.py` fala com qualquer API compatível com a da OpenAI (`/chat/completions`). Só use modelos com licença OSI
(Apache 2.0, MIT). As variáveis ficam no `servidor/.env` do juiz.

- **No computador:** instale o [Ollama](https://ollama.com), rode `ollama pull qwen2.5vl:7b` e configure `VISAO_URL` com a URL base da API compatível do Ollama. Sem GPU, cada foto leva de 20 a 60 s.
- **Pela API da Mistral** (se a máquina não tiver memória para o modelo): configure `VISAO_URL`, `VISAO_CHAVE` e `VISAO_MODELO` no `.env`. Para o Mistral Small, use `mistral-small-latest` como modelo.
- Atenção ao trocar de modelo: o Qwen2.5-VL 3B e o 72B **não** são Apache 2.0; o 7B e o 32B são.

Sem a `VISAO_URL`, ou se a API falhar, o app continua só com o CLIP e mostra o motivo em uma linha.
Capturas antigas, gravadas quando o juiz era o Gemma (`juiz = "gemma+clip"`), são lidas como `"ia+clip"`.

## Estrutura
```
app_celular/    app de celular (Expo / React Native)
servidor/       servidor do juiz (FastAPI + CLIP), Dockerfile e compose.yaml
src/            temas, jogo (pontos e pódio), visao (IA open source), reconhecimento (CLIP),
                lugares (OSM), localizacao, fotos, banco, clustering, exportação
notebooks/      análise CRISP-DM do jogo (01 → 05)
data/processed/ dados de demonstração da versão anterior (fictícios)
supabase/       estrutura do banco (schema.sql)
docs/           roteiro de testes, dicionário de dados, guia do Supabase
tests/          testes automáticos (rodam no GitHub Actions a cada push)
```

## Roadmap
- [x] Jogo: temas, tema do dia, pontos, pódio, coleção
- [x] Mapa com posição do jogador e marcadores de lugares próximos
- [x] Dois juízes (IA open source + CLIP) e página de Avaliação
- [x] Mecânicas de caminhada (mirantes, lupa, desafios, corrente, medalhas, guardiões, meta da turma, clima)
- [ ] Criar o projeto Supabase e jogar com a turma
- [x] Refazer os notebooks com os dados do jogo (fictícios)
- [ ] Rodar os notebooks com o CSV real da turma
- [ ] Publicar a versão final e gravar o vídeo
