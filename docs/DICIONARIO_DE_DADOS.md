# Dicionário de dados

## `capturas`: uma linha por foto do jogo

| Coluna | Tipo | Origem | Exemplo | No CSV anonimizado |
|---|---|---|---|---|
| `id` | uuid | banco | `3f2a…` | removida |
| `usuario` | texto | apelido de quem fotografou | `ana` | vira `u01`, `u02`… |
| `criado_em` | data e hora | hora da captura (Brasília) | `2026-11-12 15:40` | arredondada para a hora |
| `tema` | texto | juiz (IA open source ou CLIP): `carros`, `plantas`, `passaros`, `pets`, `pecas` ou `nenhum` | `carros` | mantida |
| `achado` | texto | juiz | `Volkswagen Fusca` | mantida |
| `confianca` | 0–1 | certeza do juiz | `0.9` | mantida |
| `foto_real` | sim/não | juiz: falso se for tela, impressão, desenho ou brinquedo | `true` | mantida |
| `foto_hash` | 16 hex | dHash da foto (detecta repetida) | `a1b2…` | removida |
| `cidade` | texto | bairro, cidade (GPS do navegador) | `Jardim da Penha, Vitória - ES` | só a cidade |
| `celula` | texto | quadrado de ~500 m | `-20.290,-40.295` | removida |
| `juiz` | texto | quem julgou: `ia+clip`, `ia`, `clip` ou `manual` (capturas antigas: `gemma+clip`/`gemma`, lidas como `ia+clip`/`ia`) | `ia+clip` | mantida |
| `clip_tema` | texto | tema mais provável para o CLIP (vazio = nenhum) | `pecas` | mantida |
| `clip_foto_real` | sim/não | o CLIP achou que não é tela | `true` | mantida |
| `clip_prob_tema` | 0–1 | chance que o CLIP deu ao tema final | `0.62` | mantida |
| `clip_prob_tela` | 0–1 | chance de tela/impressão/desenho para o CLIP | `0.08` | mantida |
| `clip_rank_tema` | 1–7 | posição do tema final entre os palpites do CLIP (1 = o preferido dele); > 2 = veto | `1` | mantida |
| `contestada` | texto | tema que a pessoa disse que era, numa foto recusada | `pecas` | mantida |
| `mirante` | sim/não | a foto foi a até 40 m de um lugar do mapa (calculado no app; a coordenada não é gravada) | `true` | mantida |
| `tipo_lugar` | texto | tag do OSM do lugar do mirante (`park`, `pet`, `parking`...); vazio fora de mirante | `park` | mantida |
| `clima` | texto | Open-Meteo na hora da foto: `chuva`, `nublado`, `sol` ou `neve` | `chuva` | mantida |
| `km_anterior` | número | km desde a foto anterior da pessoa (nesta sessão do navegador) | `0.8` | mantida |
| `min_anterior` | número | minutos desde a foto anterior da pessoa | `12.5` | mantida |
| `mesmo_objeto` | texto | `seu` (você já fotografou este mesmo objeto) ou `turma` (alguém fotografou no mesmo quadrado); vazio se é novo | `turma` | mantida |
| `clip_vetor` | 512 números | "retrato" da foto pelo CLIP, usado só pela função `objeto_visto` do banco; não é legível pela API nem vai para o CSV | — | fica só no banco |

### Colunas calculadas (`src/jogo.calcular_pontos`)
| Coluna | Como |
|---|---|
| `aceita` / `motivo` | recusa se não é foto real, deslocamento impossível (>3 km a >120 km/h), fora dos temas, vetada pelo CLIP, sem achado, foto repetida ou mesma coisa no mesmo dia |
| `base`, `novidade`, `raridade` | 10; +10 se novo para a pessoa; 20/(1+n anteriores da turma) |
| `do_dia` | o tema era o tema do dia na data da captura |
| `extra` | bônus fora do ×2: mirante (+5, até 3/dia), chuva (+5), lupa (+50%), desafios (+15 cada), corrente de 7 dias (+20), meta da turma (+10) |
| `lupa` / `meta` | a parte do `extra` que veio da lupa e da meta da turma |
| `detalhes` | texto com cada bônus (ex.: `mirante +5; desafio: ... +15`); não vai para o CSV |
| `pontos` | (base + novidade + raridade) × 2 se `do_dia`, + `extra` |

## Colunas derivadas na análise (notebook 02 → `capturas_limpas.csv`)

| Coluna | Como é calculada |
|---|---|
| `hora` | `criado_em.dt.hour` |
| `dia_semana` | `criado_em.dt.day_of_week` (0 = segunda) |
| `data` | `criado_em.dt.date` |
| `especifico` | o achado diz modelo, espécie ou raça (`not jogo.eh_generico`) |
| `concorda` | os dois juízes julgaram e o CLIP escolheu o mesmo tema |
| `recusa` | `motivo` sem o detalhe entre parênteses |

## `perfis_jogadores`: uma linha por jogador (notebook 02, `src/clustering.matriz_perfis`)

| Coluna | Significado |
|---|---|
| `usuario` | código anonimizado |
| `carros`, `plantas`, `passaros`, `pets`, `pecas` | proporção das fotos aceitas da pessoa em cada tema; cada linha soma 1 |

Só entra quem tem pelo menos 5 fotos aceitas. Esse vetor alimenta o **K-Means** (estilo de jogador) e a
**similaridade do cosseno** entre jogadores (notebook 03).

## Arquivos em `data/processed/`

| Arquivo | Conteúdo |
|---|---|
| `capturas_demo.csv` | **dados fictícios** (9 jogadores em 4 estilos, ~2 semanas), gerados por `python -m src.exemplo` |
| `avaliacao_juizes.csv` | *(a criar)* CSV anonimizado real, baixado na página Avaliação; quando existe, os notebooks usam ele |
| `capturas_limpas.csv` | saída do notebook 02 (capturas tratadas + colunas derivadas) |
| `perfis_jogadores.csv` | saída do notebook 02 (um vetor por jogador) |

A tabela `desejos` da versão anterior (app de compras) continua no banco só para não apagar dados; o app e os
notebooks não a usam mais.
