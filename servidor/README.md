# Servidor do juiz

O app de celular (`app_celular/`) manda a foto para cá. O CLIP julga, `src/jogo.py` calcula os pontos e a
captura é gravada no Supabase com o login da própria pessoa (o RLS continua valendo).

| Rota | O que faz |
|---|---|
| `GET /saude` | Se o CLIP já carregou e qual banco está em uso |
| `GET /temas` | Os temas e o tema do dia |
| `POST /julgar` | Foto (`foto`), `lat`, `lon` e `modo` em formulário: julga, grava e devolve o cartão de pontos |
| `GET /estado` | Pontos e posição de hoje, lupa, corrente, meta da turma e desafios |
| `GET /podio?periodo=hoje\|semana\|geral&tema=` | Ranking e guardiões |
| `GET /colecao` | Resumo, estilo, álbum por tema e medalhas |
| `POST /mapa` | `{lat, lon}`: lugares dos temas perto e manchas da turma |
| `POST /contestar` | `{id, tema}`: "o juiz errou" (não dá pontos; serve para avaliar os juízes) |

Login: cabeçalho `Authorization: Bearer <token do Supabase>`. Sem `SUPABASE_URL` e `SUPABASE_KEY` no ambiente,
o jogo fica em memória e o jogador é o cabeçalho `X-Apelido` (só para testar).

## Rodar no computador

```bash
pip install -r servidor/requirements.txt
uvicorn servidor.app:app --port 7860
```

## Publicar no Hugging Face Spaces (grátis)

1. Crie uma conta em huggingface.co e um **Space** novo: SDK **Docker**, modelo **Blank**, hardware **CPU basic**.
2. Em *Files*, envie os dois arquivos de `servidor/space/` (`Dockerfile` e `README.md`), substituindo os que existem.
3. Em *Settings → Variables and secrets*, crie os **secrets** `SUPABASE_URL` e `SUPABASE_KEY` (a chave anon,
   a mesma dos Secrets do Streamlit).
4. Espere o build (~5 min). O endereço do servidor é `https://<usuario>-<space>.hf.space`; abra `/saude` nele.
5. Para pegar código novo do GitHub: *Settings → Factory rebuild*.

O Space grátis dorme depois de 48 h sem uso; a primeira foto depois disso espera ele acordar (1 a 2 min).
