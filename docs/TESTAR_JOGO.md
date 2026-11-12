# Como testar o jogo (tema do dia, pódio e mapa)

Branch: `claude/vibrant-feynman-4fhs11`. O app atual no Streamlit continua igual até o merge.

## 1. Publicar uma cópia de teste
Abra (o formulário já vem preenchido):
https://share.streamlit.io/deploy?repository=nicollaspaulo51-cyber/wishlens&branch=claude/vibrant-feynman-4fhs11&mainModule=app/Home.py

Se você já criou o app de teste desta branch, ele atualiza sozinho: abra e, se precisar, clique em **⋮ → Reboot app**.

## 2. Secrets (⋮ → Settings → Secrets)
```toml
GEMINI_API_KEY = "sua-chave"                     # juiz com IA (https://aistudio.google.com/apikey)
SUPABASE_URL = "https://SEU-PROJETO.supabase.co" # pódio compartilhado (passo 6)
SUPABASE_KEY = "sua-anon-key"
```
Dá para testar em etapas: primeiro sem nada, depois só com o Gemma, depois com o Supabase.

## 3. Antes de tudo: a câmera do celular
No celular, abra o app e confira se a câmera do `Jogar` deixa usar a **câmera traseira** (ícone de trocar câmera)
e se a foto sai nítida o bastante para ler o modelo de um carro. O jogo depende disso e não dá para testar daqui.

## 4. Teste rápido, sem chave nenhuma
| Faça | Deve acontecer |
|---|---|
| Abra o app | Faixa roxa com o **tema do dia** e os outros 4 temas embaixo |
| Barra lateral → **Carregar dados de exemplo** | Pódio e Coleção ganham jogadores fictícios |
| Tire uma foto de um carro | Cartão com o tema "Carros" e pontos (sem a chave, o achado é genérico, "carro", e vale só a base) |
| Tire a **mesma** foto de novo (ou aponte para a mesma cena parada) | 0 pontos: "foto repetida" |
| **Pódio** | 3 degraus, abas Hoje/Semana/Geral, filtro por tema, "achados mais raros" |
| **Minha Coleção** | Estilo de jogador, álbum por tema, gráficos |

## 5. Com o Gemma (juiz com IA)
| Faça | Deve acontecer |
|---|---|
| Foto de um carro na rua | "Volkswagen Gol", "Fiat Mobi"… e pontos com novidade e raridade |
| Foto de uma planta, um pássaro, um cachorro e uma peça | Tema certo e o nome (espécie, raça, peça) |
| Foto **da tela do computador** mostrando um carro | 0 pontos: "não é foto real" |
| Foto de algo fora dos temas (uma caneca) | 0 pontos: "não é de nenhum tema" |
| Mesma coisa duas vezes no mesmo dia | A 2ª vale 0: "você já achou isso hoje" |
| Algo do **tema do dia** | Selo "tema do dia ×2" no cartão |
| Botão **🔎 Onde encontrar** (carros, plantas, pets, peças) | Abre preço, lojas online e mapa daquele achado |

Erro 404 no Gemma? Acrescente `GEMMA_MODELO = "gemma-3-12b-it"` nos Secrets.

## 6. Supabase (pódio entre pessoas)
Siga o [docs/SUPABASE.md](SUPABASE.md): criar o projeto gratuito, rodar o `supabase/schema.sql` e colar as chaves.
Para conferir a privacidade: no Supabase, **SQL Editor** → `select cidade from capturas` funciona (você é admin),
mas o app nunca recebe bairro/célula dos outros; o mapa mostra só manchas com 2+ capturas.
Depois:
1. Crie duas contas (celular e computador, ou uma janela anônima).
2. Tire uma foto com cada uma.
3. Em **Pódio**, as duas devem aparecer. Quem achar um carro primeiro ganha mais raridade que o segundo.

Sem o Supabase, cada pessoa só vê ela mesma (e os exemplos) no pódio.

## 7. Explorar (mapa que pisca)
| Faça | Deve acontecer |
|---|---|
| Abra **Explorar** e permita o GPS (ou digite o bairro) | Mapa com pontos coloridos **pulsando** por tema |
| Olhe o tema do dia | Os pontos dele são maiores e pulsam mais rápido |
| Com dados de exemplo em Vitória-ES (ou fotos com GPS) | 🟡 pontos amarelos = onde a turma achou coisas |
| Toque num ponto | Cartão com o lugar, horário e "Como chegar" (Google Maps/Waze) |
| Desmarque temas no filtro | Os pontos daquele tema somem |

## Já verificado aqui
- `pytest`: 66 testes passando (rede e IA simuladas): pontos, raridade, ×2, recusas, hash de foto repetida,
  pódio, tema do dia virando à meia-noite de Brasília, juiz do Gemma, busca de pontos por tema, exportação sem hash e célula,
  capturas do Supabase (datas com fuso) misturadas com as da memória.
- Busca no Supabase em páginas de 1.000 (o limite da API), para o pódio não perder as capturas mais novas.
- Foto repetida só conta para o mesmo achado: dois pássaros diferentes contra o céu não são barrados.
- O reconhecimento de reserva (CLIP) rodou de ponta a ponta com pesos aleatórios, sem erro.
- App rodando com a IA e o OpenStreetMap simulados, câmera falsa do Chromium:
  foto → +27 pontos; foto de tela → recusada; Pódio, Coleção e "Onde encontrar" navegando pelo menu.
- Pulso do mapa: conferido renderizando o mapa com o Leaflet local (aqui o CDN do Leaflet é bloqueado).

**Não** testado aqui: o Gemma real, o CLIP real (o Hugging Face está bloqueado), o Supabase real e o mapa dentro do app publicado.
