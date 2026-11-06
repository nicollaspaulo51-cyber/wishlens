# Roteiro do vídeo: WishLens

Duração sugerida: **8 a 10 minutos**. Grave a tela com o app aberto, os notebooks no GitHub
e, se quiser, a prévia da interface. Cada bloco corresponde a uma fase do CRISP-DM.

| # | Tempo | Fase | O que falar | O que mostrar na tela |
|---|---|---|---|---|
| 0 | 0:00–0:40 | Abertura | "Já viu algo na rua e pensou *quero isso*? O WishLens transforma esse momento em dados." Apresente o nome e o slogan *Point. Snap. Want.* | Tela inicial do app; alternar o botão ☀️/🌙 |
| 1 | 0:40–1:40 | **Entendimento do negócio** | O problema (não há um lugar único para descobrir onde conseguir o que se deseja nem para entender os próprios desejos), para quem é e as 4 perguntas de negócio. Critérios de sucesso. | `README.md` e o início do notebook 01 |
| 2 | 1:40–3:30 | **Entendimento dos dados** | De onde vêm os dados (fotos → registros), as colunas, as licenças. Explicar o `describe()`: count (dados ausentes em `preco_max`), média × mediana (assimetria do preço), desvio padrão, quartis da hora. Mostrar 2 ou 3 gráficos e o que eles dizem. | Notebook 01: `describe()`, countplot por categoria, heatmap dia × hora, heatmap pessoa × categoria |
| 3 | 3:30–4:30 | **Preparação** | As 3 regras de limpeza (confiança < 0,45, duplicados, mínimo de 10 desejos), a anonimização (LGPD) e a ideia do **vetor de perfil** (proporção por categoria, e por que proporção e não contagem). | Notebook 02: antes/depois da limpeza, tabela anonimizada, heatmap dos perfis |
| 4 | 4:30–6:30 | **Modelagem** | Cotovelo + silhueta para escolher k; K-Means; nome de cada grupo a partir do centro. Similaridade do cosseno: o que significa 100% e 0%. Recomendação "pessoas parecidas". | Notebook 03: gráficos de cotovelo/silhueta, heatmap dos centros, matriz de similaridade |
| 5 | 6:30–7:40 | **Avaliação** | Silhueta atingiu o critério? Estabilidade (ARI). Limitações (dados fictícios, amostra, viés da turma, erros do reconhecimento, faixa de preço). Checklist de LGPD. | Notebook 04 |
| 6 | 7:40–9:20 | **Implantação / produto** | Demonstração ao vivo: enviar uma foto → confirmar o item → links e lugares próximos → salvar. Ir em **Meus Desejos** (cartão "Seu perfil", gráficos) e em **Comparar** (% de combinação, radar, sugestões, aceite). | App Streamlit (ou a prévia) |
| 7 | 9:20–10:00 | Encerramento | Próximos passos: coleta real com a turma, reconhecimento automático com o CLIP, banco Supabase e publicação. | `README.md` → Roadmap |

## Dicas
- **Diga sempre que os dados mostrados são fictícios** enquanto a coleta real não estiver pronta.
  Os gráficos funcionam igual com os dados reais.
- Fale das **escolhas**, não só dos resultados: por que proporção, por que silhueta, por que confirmar o item.
- Mostre o código só quando ele explicar algo. O professor quer ver o raciocínio em cada fase.
- Termine com uma frase de impacto: *"O WishLens mostra que até um desejo de 2 segundos vira um dado útil,
  com cuidado com a privacidade de quem deseja."*
