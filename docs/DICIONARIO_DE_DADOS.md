# Dicionário de dados

## `capturas`: uma linha por foto do jogo

| Coluna | Tipo | Origem | Exemplo | No CSV anonimizado |
|---|---|---|---|---|
| `id` | uuid | banco | `3f2a…` | removida |
| `usuario` | texto | apelido de quem fotografou | `ana` | vira `u01`, `u02`… |
| `criado_em` | data e hora | hora da captura (Brasília) | `2026-11-12 15:40` | arredondada para a hora |
| `tema` | texto | juiz (Gemma ou CLIP): `carros`, `plantas`, `passaros`, `pets`, `pecas` ou `nenhum` | `carros` | mantida |
| `achado` | texto | juiz | `Volkswagen Fusca` | mantida |
| `confianca` | 0–1 | certeza do juiz | `0.9` | mantida |
| `foto_real` | sim/não | juiz: falso se for tela, impressão, desenho ou brinquedo | `true` | mantida |
| `foto_hash` | 16 hex | dHash da foto (detecta repetida) | `a1b2…` | removida |
| `cidade` | texto | bairro, cidade (GPS do navegador) | `Jardim da Penha, Vitória - ES` | só a cidade |
| `celula` | texto | quadrado de ~500 m | `-20.290,-40.295` | removida |
| `juiz` | texto | quem julgou: `gemma+clip`, `gemma`, `clip` ou `manual` | `gemma+clip` | mantida |
| `clip_tema` | texto | tema mais provável para o CLIP (vazio = nenhum) | `pecas` | mantida |
| `clip_foto_real` | sim/não | o CLIP achou que não é tela | `true` | mantida |
| `clip_prob_tema` | 0–1 | chance que o CLIP deu ao tema final | `0.62` | mantida |
| `clip_prob_tela` | 0–1 | chance de tela/impressão/desenho para o CLIP | `0.08` | mantida |
| `clip_rank_tema` | 1–7 | posição do tema final entre os palpites do CLIP (1 = o preferido dele); > 2 = veto | `1` | mantida |
| `contestada` | texto | tema que a pessoa disse que era, numa foto recusada | `pecas` | mantida |

### Colunas calculadas (`src/jogo.calcular_pontos`)
| Coluna | Como |
|---|---|
| `aceita` / `motivo` | recusa se não é foto real, fora dos temas, vetada pelo CLIP, sem achado, foto repetida ou mesma coisa no mesmo dia |
| `base`, `novidade`, `raridade` | 10; +10 se novo para a pessoa; 20/(1+n anteriores da turma) |
| `do_dia` | o tema era o tema do dia na data da captura |
| `pontos` | (base + novidade + raridade) × 2 se `do_dia` |

## Versão anterior (desejos de consumo)
As seções abaixo descrevem os dados da versão anterior do WishLens, ainda usados pelos notebooks 01–04 e pelo CSV
de demonstração. O app não grava mais desejos; a tabela continua no banco só para não apagar dados.

## `desejos`: um registro por foto (versão anterior)

| Coluna | Tipo | Origem | Exemplo | No CSV anonimizado |
|---|---|---|---|---|
| `id` | uuid | gerado pelo banco | `3f2a…` | removida |
| `usuario` | texto | apelido de quem fotografou (login) | `ana` | vira código: `u01`, `u02`… |
| `criado_em` | data e hora | EXIF da foto ou hora do envio | `2026-11-05 19:42` | arredondada para a hora cheia |
| `item` | texto | reconhecimento (CLIP) confirmado pela pessoa | `tênis` | mantida |
| `categoria` | texto (12 valores) | catálogo `src/categorias.py` | `calçados` | mantida |
| `tipo` | `comprar` / `receita` / `adotar` | catálogo | `comprar` | mantida |
| `faixa_preco` | texto | referência por categoria (`FAIXA_PRECO`) | `R$ 100–500` | mantida |
| `confianca` | número 0–1 | probabilidade do 1º palpite do CLIP (vazia se escolhido à mão) | `0.71` | mantida |
| `cidade` | texto | geocodificação do GPS (só cidade/bairro) | `Jardim da Penha, Vitória - ES` | só a cidade: `Vitória - ES` |
| `acao` | texto | o que a pessoa fez depois | `ver_loja_online`, `ver_mapa`, `ver_receita`, `salvou` | mantida |
| `foto_url` / `foto_path` | texto | caminho da foto no bucket privado | `fotos/<uid>/a1.jpg` | removida |

### Colunas derivadas na análise (notebook 01)

| Coluna | Como é calculada |
|---|---|
| `hora` | `criado_em.dt.hour` |
| `dia_semana` | `criado_em.dt.dayofweek` (0 = segunda) |
| `preco_min`, `preco_max` | números extraídos de `faixa_preco` (adoção = 0; "R$ 1.000+" não tem máximo) |

## `perfis`: uma linha por pessoa (notebook 02, `src/clustering.matriz_perfis`)

| Coluna | Significado |
|---|---|
| `usuario` | código anonimizado |
| uma coluna por categoria (12) | proporção dos desejos da pessoa naquela categoria; cada linha soma 1 |

Esse vetor é usado no **K-Means** (perfis de desejo) e na **similaridade do cosseno** (página Comparar).

## Categorias e tipos

| Tipo | Categorias |
|---|---|
| comprar | vestuário, calçados, eletrônicos, brinquedos e games, casa e decoração, esporte e lazer, beleza, livros e papelaria, veículos |
| receita (comer) | comida, bebidas |
| adotar | animais |

## Arquivos em `data/processed/`

| Arquivo | Conteúdo |
|---|---|
| `desejos_demo.csv` | **dados fictícios** (12 pessoas em 4 estilos + "exemplo:eu") gerados por `src/exemplo.py` |
| `perfis_demo.csv` | matriz de perfis gerada a partir do arquivo acima (notebook 02) |
| `desejos.csv` | *(a criar)* CSV anonimizado real, baixado do app |
