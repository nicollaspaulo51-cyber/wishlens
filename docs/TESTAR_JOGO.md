# Como testar o jogo (personagem no mapa, juízes e pódio)

Branch: `claude/vibrant-feynman-4fhs11`.

## 1. Atualizar o app de teste
O app de teste desta branch nem sempre atualiza sozinho depois de um push. Abra o app, toque em
**Gerenciar aplicativo** (canto de baixo) → **⋮ → Reboot app** e espere 2 ou 3 minutos.
Confira que atualizou: o menu deve ter só **Home, Pódio, Minha Coleção e Avaliação**, e a tela inicial abre com o mapa.

Ainda não criou o app de teste? Abra (o formulário já vem preenchido):
https://share.streamlit.io/deploy?repository=nicollaspaulo51-cyber/wishlens&branch=claude/vibrant-feynman-4fhs11&mainModule=app/Home.py

## 2. Secrets (⋮ → Settings → Secrets)
```toml
GEMINI_API_KEY = "sua-chave"                     # juiz principal (https://aistudio.google.com/apikey)
SUPABASE_URL = "https://SEU-PROJETO.supabase.co" # pódio compartilhado (passo 6)
SUPABASE_KEY = "sua-anon-key"
```
Com a chave, o rodapé do cartão de pontos mostra **"Juízes: Gemma ✔ · CLIP ✔"**. Se mostrar só "CLIP", a chave não
está sendo lida.

## 3. Tela principal: personagem no mapa
| Faça | Deve acontecer |
|---|---|
| Abra o app no celular e **permita a localização** | Mapa com o **personagem** (explorador com lupa) na sua posição, balançando, com um círculo pulsando |
| Olhe os pontos coloridos | Eles **aparecem, piscam e somem**, cada um no seu ritmo; os do tema do dia são maiores |
| Ande alguns metros com o app aberto | O personagem anda junto (se o navegador permitir GPS contínuo) |
| Toque num ponto | Cartão: o que procurar ali, distância, endereço/horário (quando o mapa tem) e "Como chegar" |
| Desmarque temas nos botões acima do mapa | Os pontos daquele tema somem |
| **🔄 Atualizar lugares** depois de andar | Busca os lugares de novo a partir de onde você está |
| Sem permitir o GPS | Aparece "Sem GPS: onde você está?"; digite o bairro e o mapa abre lá |
| Tema escuro (🌙 na barra lateral) | O mapa fica escuro também |

## 4. Fotos (os dois erros que você encontrou)
| Faça | Deve acontecer |
|---|---|
| **📷 Fotografar** → foto de um **mouse** | Peças e periféricos de computador · Mouse, com pontos |
| Depois, foto de um **teclado** | Também vale: Teclado (antes dava "você já achou isso hoje") |
| Foto do **pássaro na tela do computador** | 0 pontos: "não é foto real" (Gemma) ou "o CLIP viu uma tela ou impressão" |
| Pássaro, planta ou cachorro de verdade | Vale, com o nome (espécie/raça) se o Gemma estiver ligado |
| Mesmo mouse de novo no mesmo dia | 0: "você já achou isso hoje" (mesmo achado específico) |
| Carros sem o modelo (só "carro") | Valem a base até 3 vezes por dia; a 4ª dá 0 com o motivo |
| Foto recusada por tema ou por "tela" sem ser | "O juiz errou? Era…": escolha e **Contestar** (não dá pontos, vai para a Avaliação) |

Com o CLIP sozinho (sem a chave), uma foto de tela bem tirada (de perto, sem borda) ainda pode passar. O Gemma é
o juiz principal para isso.

Erro 404 no Gemma? Acrescente `GEMMA_MODELO = "gemma-3-12b-it"` nos Secrets.

## 5. Antes de tudo: a câmera do celular
Confira se a câmera deixa usar a **câmera traseira** (ícone de trocar câmera) e se a foto sai nítida o bastante
para ler o modelo de um carro.

## 6. Supabase (pódio entre pessoas)
Siga o [docs/SUPABASE.md](SUPABASE.md). Se já rodou o `supabase/schema.sql` antes, **rode de novo** (ele só
acrescenta o que falta). Depois, crie duas contas, tire uma foto com cada uma e veja as duas no **Pódio**.
Sem o Supabase, cada pessoa só vê ela mesma (e os exemplos) no pódio.

## 7. Pódio, Coleção e Avaliação
| Faça | Deve acontecer |
|---|---|
| Barra lateral → **Carregar dados de exemplo** | Pódio, Coleção e Avaliação ganham jogadores fictícios |
| **Pódio** | 3 degraus, abas Hoje/Semana/Geral, filtro por tema, "achados mais raros" |
| **Minha Coleção** | Estilo de jogador, álbum por tema, gráficos |
| **Avaliação** | Concordância CLIP × Gemma, matriz de confusão, vetos, recusas, contestações, CSV |

## Já verificado aqui
- `pytest`: 59 testes passando (rede e IA simuladas), incluindo: mouse e teclado viram achados diferentes só com o
  CLIP; frases gêmeas de tela; o CLIP só derruba o "é real" do Gemma se "tela" for 3× mais provável que o tema
  (um pássaro de verdade não é barrado por uma vantagem pequena; menos peças); limite de 3 fotos genéricas por dia; HTML do mapa sem brecha para nome malicioso do OSM; nenhuma
  página importa código removido.
- Mapa renderizado no Chromium com o Leaflet local: personagem aparece, 7 de 8 pontos mudaram de visível para
  invisível (ou o contrário) em 1,7 s, cartão abre ao tocar, tema claro e escuro.
- App com os juízes simulados: mouse +40, teclado +40, pássaro na tela recusado; menu com 4 páginas.

**Não** testado aqui: o mapa dentro do app publicado (o Leaflet vem de um CDN bloqueado neste ambiente), o GPS
contínuo no celular, o Gemma real, o CLIP real e o Supabase real.
