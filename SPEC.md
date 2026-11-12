# Spec: WishLens — fluxo "aponte → reconheça → onde conseguir"

## Objetivo
A pessoa abre o site no celular, aponta a câmera para um **produto, comida ou animal**, e o WishLens:
1. reconhece o que é (top‑3 para confirmar);
2. mostra **lugares próximos** no mapa: lojas (produto), restaurantes (comida), abrigos / pet shops / veterinários (animal);
3. mostra **links online**: lojas para comprar, receitas e delivery, ou adoção.

Todo o stack é **open source** (código, bibliotecas, modelo de IA, dados de mapa). Os links levam a lojas comerciais, o que é permitido.
Exceções opcionais, desligadas sem configuração: o **Gemma** (pesos abertos, licença Gemma; chamado pela API do
Google AI Studio porque não cabe no Streamlit Cloud gratuito) para marca/modelo/preço, e a **API do Mercado Livre** para preço.
O fluxo completo funciona sem os dois.

Fora de escopo nesta etapa: Supabase real, coleta de dados com a turma, notebooks, páginas Meus Desejos / Descobrir / Comparar.

## Capability map
| Módulo | Responsabilidade | Depende de | Arquivo |
|---|---|---|---|
| reconhecimento | foto → top‑3 itens (CLIP zero‑shot) | categorias | `src/reconhecimento.py` (já pronto; ativar) |
| localizacao | posição: GPS da foto → GPS do navegador → endereço (Nominatim) | — | `src/localizacao.py` (novo) |
| lugares-proximos | Overpass com servidor de reserva, mapa OSM | localizacao, categorias | `src/lugares.py` |
| busca-online | links de lojas / receitas / delivery / adoção | categorias | `src/links.py` (sem mudança) |
| fluxo-app | tela única que liga tudo | todos | `app/Home.py` |

Ordem: reconhecimento, localizacao, busca-online → lugares-proximos → fluxo-app → publicação.

## Vocabulário (atualizado em 12/11/2026)
- Reconhecimento sobre ~1.070 rótulos: catálogo curado (`src/categorias.py`, peso 1,7× no ranking, frases de marcas conhecidas e média de 3 frases por rótulo) + 947 objetos do LVIS (CC BY 4.0) com nomes em português do Open Multilingual Wordnet (CC BY-SA).
- Categoria: hierarquia do WordNet (comida, bebida, animal doméstico, roupa, calçado, móvel, veículo...); o que sobrar vai para a categoria de produto do item curado mais parecido no CLIP. Animais selvagens ficam fora (nada para adotar). Correções manuais e remoção de rótulos sem sentido (avião, placa de rua...) em `scripts/correcoes_vocabulario.py`.
- Marca: o CLIP sai com marca quando as frases dela levam ao menos metade da chance do item; com `GEMINI_API_KEY`, o Gemma (`src/visao.py`) sugere objeto, marca, modelo e faixa de preço como 1ª opção.

## Preço (`src/precos.py`, atualizado em 12/11/2026)
Mercado Livre (1º a 3º quartil dos anúncios novos de "marca modelo item") → faixa do Gemma → tabela de referência. A fonte aparece ao lado do preço. Comida e bebida não buscam anúncios.

## Cartão do lugar
Clique no marcador (ou na linha da tabela) → cartão com endereço, horário (traduzido do `opening_hours` do OSM), telefone, site, preço de referência e "Como chegar" (Google Maps, Waze, OSM). Texto do OSM sempre escapado; links só `http(s)` e `tel:`.
- Vetores de texto pré-calculados em `data/vocabulario_clip.npy`; `nltk` só é usado pelo script gerador, não pelo app.
- "Outra coisa…": nome digitado (validado: letras, números e pontuação simples, até 60) + categoria obrigatória.

## Critérios de aceite
1. Com `torch` + `transformers` instalados, fotos de cachorro, pizza e tênis retornam o item certo no top‑3.
2. O app pede a localização do navegador; aceitando, usa as coordenadas sem digitação.
3. Negando o GPS, digitar "Jardim da Penha, Vitória" devolve coordenadas pelo Nominatim.
4. "Buscar lugares próximos" mostra mapa com tiles OpenStreetMap e tabela ordenada por distância. Se `overpass-api.de` falhar, tenta um espelho; se ambos falharem, mensagem amigável.
5. Os links online funcionam para os três tipos (comprar / receita / adotar).
6. Ao salvar um desejo, guarda só cidade/bairro, nunca a coordenada exata.
7. `python -m pytest -q tests/` passa localmente e no GitHub Actions, sem acesso à internet.
8. O app publicado no Streamlit Community Cloud abre no celular e reconhece uma foto da câmera.

## Tech stack (todos abertos)
| Peça | Licença |
|---|---|
| Streamlit | Apache‑2.0 |
| CLIP ViT‑B/32 via `transformers` | MIT / Apache‑2.0 |
| `torch` (build só‑CPU) | BSD‑3 |
| OpenStreetMap, Overpass, Nominatim | dados ODbL, software GPL/AGPL |
| `streamlit-js-eval` (GPS do navegador) | MIT |
| `folium` + `streamlit-folium` (mapa com tiles OSM) | MIT |
| Supabase (já no código, não usado nesta etapa) | Apache‑2.0 |

## Comandos
```bash
pip install -r requirements.txt          # app completo, com CLIP
pip install -r requirements-dev.txt      # leve, sem torch (testes e CI)
streamlit run app/Home.py
python -m pytest -q tests/
```

## Estrutura
```
app/Home.py            fluxo principal (câmera → resultado → lugares → links)
app/pages/             outras páginas (não mudam nesta etapa)
src/reconhecimento.py  CLIP zero-shot
src/localizacao.py     Nominatim: endereço → coordenada, coordenada → bairro   (novo)
src/lugares.py         Overpass/OSM
src/links.py           links online
src/categorias.py      catálogo de itens (fonte única de rótulos/categorias)
tests/                 pytest, rede sempre mockada
```

## Estilo
Código e nomes em português, como o resto do repo; funções pequenas com docstring de uma linha; `src/` não importa Streamlit (o cache fica no app).
```python
def geocodificar(endereco: str) -> tuple[float, float, str] | None:
    """Converte um endereço em (lat, lon, nome) usando o Nominatim (OSM)."""
    resp = requests.get(NOMINATIM_URL + "/search", params={...},
                        headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    achados = resp.json()
    if not achados:
        return None
    ...
```

## Testes
- `pytest`, arquivos em `tests/`, rede mockada com `unittest.mock.patch`.
- `test_localizacao.py`: endereço encontrado → coordenadas; nada encontrado → `None`; envia User‑Agent; bairro extraído do `/reverse`.
- `test_lugares.py`: consulta de "animais" inclui `animal_shelter`; falha no 1º servidor → usa o espelho; resultado ordenado por distância.
- Links: já cobertos em `test_basico.py`.
- CLIP: teste marcado como lento e pulado quando `torch` não está instalado (CI continua leve).

## Limites
- **Sempre:** User‑Agent identificável e no máximo 1 requisição/s ao Nominatim (política de uso do OSM); cache das consultas no app; guardar só cidade/bairro; rodar os testes antes de commitar.
- **Perguntar antes:** dependência além das listadas acima; mudar `supabase/schema.sql` ou o CI.
- **Nunca:** commitar `secrets.toml`; usar API paga ou fechada como fonte de dados; salvar foto com EXIF/GPS.

## Riscos
- Memória do Streamlit Cloud com torch + CLIP (~1 GB): usar torch só‑CPU; se não couber, plano B é `open_clip` com modelo menor.
- Overpass e Nominatim públicos têm limite de uso: servidor de reserva, cache e mensagem amigável.
- Cobertura do OSM na região pode ser fraca: os links online continuam como alternativa.

## Perguntas em aberto
- Nenhuma bloqueante. A conta no Streamlit Cloud é sua: a publicação (critério 8) precisa que você faça o login lá.
