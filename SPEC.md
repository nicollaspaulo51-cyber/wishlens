# Spec: WishLens (jogo de fotos do mundo real)

Atualizado em 13/11/2026. A versão anterior (desejos de consumo: onde comprar, preço, lojas) foi removida do app;
os notebooks 01–04 e o CSV de desejos ficam como "versão anterior" até serem refeitos com os dados do jogo.

## Tela principal (`app/Home.py` + `src/mapa_jogo.py`)
- Barra compacta: tema do dia (×2), pontos e posição de hoje.
- **Mapa do jogo** (Leaflet num componente HTML, roda no navegador):
  - personagem próprio do WishLens (SVG: explorador com boné, mochila e lupa) na posição do GPS, acompanhando o
    `watchPosition`; círculo de alcance pulsando;
  - lugares de cada tema (Overpass, uma consulta com as tags de todos os temas: `lugares.buscar_pontos_temas`)
    que **aparecem, piscam e somem** (animação CSS com duração e atraso sorteados por ponto; tema do dia maior e
    mais frequente); manchas 🟡 da turma por célula de ~500 m (`armazenamento.manchas`);
  - tocar num ponto → cartão dentro do mapa (o que procurar, distância, endereço, horário, Google Maps/Waze);
  - dados vão como JSON; o JavaScript só usa `textContent` (nada do OSM vira HTML).
- Filtro por tema (`st.pills`), "Atualizar lugares" (nova busca a partir da posição atual).
- **📷 Fotografar** → `st.camera_input` → cartão de pontos.
- Sem GPS: endereço digitado (Nominatim). Sem o componente de GPS contínuo: o personagem fica na posição inicial.

## Juízes
- **Gemma** (`visao.identificar_captura`): tema, achado, foto_real, certeza. Prompt com o que conta em cada tema e
  os sinais de foto de tela (borda, moiré, reflexo, bordas de janela).
- **CLIP** (`reconhecimento.julgar_clip`), em toda foto: grupos = 5 temas + "tela" + "nenhum"; a chance de cada
  grupo é a da sua melhor frase. "tela" tem frases gêmeas de cada objeto dos temas. Devolve tema, achado (nome da
  frase do tema que mais combinou: "mouse", "teclado", "flor"), foto_real (falso se "tela" é o 1º palpite, exceto
  peças) e a chance de cada grupo.
- **Veto** (`jogo.veto_clip`, aplicado na leitura): CLIP viu tela (exceto peças) ou o tema do Gemma fora dos 2
  primeiros palpites do CLIP.
- Sem Gemma: o CLIP decide sozinho. Sem nenhum modelo: a pessoa escolhe o tema e digita.
- Recusa por tema pode ser contestada (coluna `contestada`, sem pontos).

## Pontos (`src/jogo.py`)
Base 10, novidade +10, raridade 20/(1+n anteriores), ×2 no tema do dia. Achado genérico ("carro"): só a base,
até 3 por tema por dia. 0 com motivo: não é foto real, fora dos temas, vetada pelo CLIP, sem achado, foto repetida
(dHash ≤ 6 bits, mesmo achado) ou mesmo achado específico no mesmo dia. Recalculados a partir das capturas.

## Pódio, coleção, avaliação
- Pódio: hoje, semana (segunda até hoje) e geral; filtro por tema; empate para quem chegou antes.
- Coleção: álbum por tema, raridade, estilo de jogador (K-Means por tema).
- Avaliação: concordância CLIP × Gemma, matriz de confusão, vetos, recusas, contestações, CSV anonimizado.

## Banco
Tabela `capturas` (RLS: logados leem as colunas sem localização; cada um insere as suas com `criado_em` de agora;
só a contestação da própria captura pode ser alterada). Mapa da turma pela função `manchas_capturas()`.
As tabelas `desejos` e `conexoes` da versão anterior ficam no schema, sem uso pelo app.

## Comandos
```bash
pip install -r requirements.txt          # app completo, com CLIP
pip install -r requirements-dev.txt      # leve, sem torch (testes e CI)
streamlit run app/Home.py
python -m pytest -q tests/
```

## Limites
- **Sempre:** User-Agent identificável e no máximo 1 requisição/s ao Nominatim; cache das consultas no app; guardar
  só bairro e célula de ~500 m; nunca guardar a foto; rodar os testes antes de commitar.
- **Nunca:** commitar `secrets.toml`; salvar foto com EXIF/GPS; usar nome, personagens ou arte de jogos existentes.

## Riscos
- Memória do Streamlit Cloud com torch + CLIP (~1 GB): torch só-CPU; o CLIP agora carrega só o modelo (sem o
  vocabulário de produtos).
- Overpass e Nominatim públicos têm limite de uso: servidores de reserva, cache e mensagem amigável.
- Foto de tela bem tirada (de perto, sem borda) ainda pode enganar o CLIP sozinho: o Gemma é o juiz principal.
