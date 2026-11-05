# Plano do Projeto Final — **WishLens** 🔍✨

> *Point. Snap. Want.*: aponte a câmera para qualquer coisa e descubra onde conseguir, o que você deseja e com quem você combina.

## Contexto
Projeto final da disciplina **Ciência de Dados I (Turma 12)**. O professor pede um produto de dados desenvolvido com **CRISP-DM**, com EDA (`describe()`, Pandas, Seaborn) e, no final, **clustering**. O recomendador por **similaridade do cosseno**, visto em aula, pode ser reaproveitado. A entrega é um **vídeo** que apresenta cada fase do CRISP-DM.

**Ideia do aluno:** um app/site em que a pessoa envia uma foto ou aponta a câmera para qualquer coisa:
- **comprável** → lojas físicas próximas + lojas online;
- **comida** → receitas, restaurantes próximos, delivery;
- **animal** → lugares de adoção próximos.

Cada busca vira um registro de "desejo". O app mostra **gráficos dos desejos** e permite **comparar seus desejos com os de outra pessoa** escolhida.

**Princípio:** a câmera e os mapas são a "embalagem". A nota vem da **análise dos dados de desejo** (EDA, clustering, similaridade).

---

## 1. Arquitetura

```
Usuário (foto/câmera) → Site Streamlit → Reconhecimento (modelo aberto CLIP)
                                  ├─► Supabase Storage  (fotos reduzidas, sem GPS)
                                  ├─► Supabase Postgres (tabela de desejos + usuários)
                                  └─► OpenStreetMap (lojas/restaurantes/abrigos próximos)
Notebooks de análise ◄── exportação CSV anonimizada
GitHub: apenas código (app + notebooks + CSV anonimizado)
```

| Peça | Escolha | Por quê |
|---|---|---|
| App/site | **Streamlit** (Python) | `st.camera_input` e `st.file_uploader` prontos; mesma linguagem da análise |
| Reconhecimento | **CLIP aberto** (`open_clip` ou Hugging Face) com classificação zero-shot | Reconhece "qualquer coisa" a partir de uma lista de rótulos em texto, sem treinar modelo |
| Banco + fotos + login | **Supabase** (open source, plano gratuito) | O Streamlit Cloud apaga arquivos locais ao reiniciar |
| Lugares próximos | **OpenStreetMap / Overpass API** (ODbL) | `shop=*`, `amenity=restaurant/fast_food`, `amenity=animal_shelter` |
| Lojas online / receitas / delivery | **Links de busca** (ex.: Mercado Livre, receitas, iFood) | Não exige dados de terceiros |
| Gráficos | Seaborn (notebooks), Plotly (app) | Seaborn é exigência da disciplina |
| Publicação | Streamlit Community Cloud | Gratuito, publicado direto do GitHub |

---

## 2. Modelo de dados (tabela `desejos`)

| Campo | Tipo | Origem |
|---|---|---|
| id | uuid | gerado |
| usuario_id | uuid | login |
| criado_em | timestamp | EXIF ou hora do envio |
| item | texto | CLIP (melhor rótulo) |
| confianca | float | CLIP |
| categoria | texto | mapa rótulo → categoria (vestuário, eletrônicos, comida, pet…) |
| tipo | comprar / receita / adotar | mapa da categoria |
| faixa_preco | texto | tabela de referência por categoria |
| cidade, bairro | texto | GPS do EXIF/navegador → geocodificação reversa (só bairro é guardado) |
| acao | ver_loja_online / ver_mapa / ver_receita / ignorar | clique no app |
| foto_url | texto | Supabase Storage (foto reduzida a ~1024 px, sem EXIF) |

Tabela `conexoes` (usuario_a, usuario_b, aceito): a comparação só ocorre se **as duas pessoas aceitarem**.

---

## 3. Dados para a análise
1. **Dados reais coletados:** o aluno + 3 a 5 colegas usam o protótipo por ~2 semanas, com meta de 30 a 50 fotos por pessoa e com consentimento.
2. **Base aberta complementar:** **Olist** (e-commerce brasileiro, CC BY-NC-SA, uso acadêmico) como substituta dos "desejos" em escala, para o clustering ter volume. As categorias são mapeadas para as mesmas do app.

---

## 4. Fases do CRISP-DM → entregas

| Fase | O que fazer | Entregável |
|---|---|---|
| **1. Negócio** | Problema, público, perguntas (ex.: "quais perfis de desejo existem?", "o quanto duas pessoas se parecem?"), critérios de sucesso | `README.md` + seção no notebook 01 |
| **2. Dados** | Fontes e licenças, `describe()`, distribuições por categoria/horário/preço, nulos e confiança do reconhecimento | `notebooks/01_entendimento.ipynb` |
| **3. Preparação** | Limpeza, juntar as categorias do app com as do Olist, remover baixa confiança, montar o **vetor de perfil** por usuário (proporção por categoria) | `notebooks/02_preparacao.ipynb`, `data/processed/` |
| **4. Modelagem** | **K-Means** sobre os perfis (k escolhido por cotovelo/silhueta) e **similaridade do cosseno** usuário×usuário para comparar e recomendar | `notebooks/03_modelagem.ipynb` |
| **5. Avaliação** | Os clusters fazem sentido (nomear perfis)? Acurácia do CLIP numa amostra rotulada à mão. Limitações: amostra pequena, cobertura do OSM, LGPD | `notebooks/04_avaliacao.ipynb` |
| **6. Produto** | App publicado: foto → resultado → lugares → gráficos pessoais → comparação | `app/` + link público + vídeo |

---

## 5. Estrutura do repositório (GitHub)
```
wishlens/
├── README.md
├── requirements.txt
├── .streamlit/secrets.toml.example   ← chaves do Supabase NUNCA vão para o Git
├── app/
│   ├── Home.py                ← enviar foto / câmera
│   └── pages/ (Meus_Desejos.py, Comparar.py)
├── src/
│   ├── reconhecimento.py      ← CLIP zero-shot + mapa de categorias
│   ├── lugares.py             ← consultas Overpass/OSM
│   ├── links.py               ← links de lojas online/receitas/delivery
│   ├── fotos.py               ← reduzir imagem, remover EXIF, ler data/GPS
│   └── banco.py               ← acesso ao Supabase
├── notebooks/ 01_entendimento … 04_avaliacao
└── data/processed/desejos_anonimizado.csv
```

---

## 6. Cronograma sugerido (ajustar à data de entrega do final)

| Semana | Foco |
|---|---|
| 1 | Repositório, README com a proposta, lista de rótulos/categorias, teste do CLIP com fotos de exemplo |
| 2 | App mínimo: foto → item + categoria → salvar no Supabase; login |
| 3 | Lugares próximos (OSM) + links online; publicar no Streamlit Cloud; **início da coleta com colegas** |
| 4 | Coleta + página "Meus Desejos" (gráficos) + EDA no Olist |
| 5 | Preparação, clustering e similaridade; página "Comparar" |
| 6 | Avaliação, ajustes, roteiro e gravação do vídeo |

---

## 7. Riscos e cuidados
- **Privacidade (LGPD):** consentimento, remover GPS das fotos, guardar só o bairro, CSV anonimizado no GitHub, comparação só com aceite mútuo.
- **Reconhecimento erra:** mostrar as 3 melhores opções para o usuário confirmar. A confirmação também melhora a qualidade dos dados.
- **OSM incompleto na região:** registrar como limitação; o link de busca online serve de alternativa.
- **Poucos dados reais:** complementar com o Olist; deixar claro no vídeo o que é real coletado e o que é base aberta.

---

## 8. Verificação
- `streamlit run app/Home.py` localmente: enviar 10 fotos variadas (roupa, prato, cachorro, objeto) e conferir item, categoria, tipo e lugares próximos.
- Conferir no Supabase se o registro foi salvo e se a foto não tem EXIF (`exiftool`).
- Medir a acurácia do CLIP numa amostra de 30 fotos rotuladas à mão.
- Rodar os notebooks 01→04 do início ao fim a partir do CSV anonimizado (Kernel → Restart & Run All).
- Testar o app publicado pelo celular (câmera real).

## Próximo passo imediato (após aprovação)
Com o endereço do repositório no GitHub: criar a estrutura de pastas, o README com a proposta e o `src/reconhecimento.py`, e testar o CLIP com as primeiras fotos. Para isso, a rede da sessão precisa liberar Hugging Face/PyPI (os modelos) e a Overpass API (OSM).
