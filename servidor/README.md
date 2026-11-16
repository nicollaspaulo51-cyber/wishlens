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

## Publicar numa máquina da turma (tudo open source)

O juiz roda em qualquer computador com Linux e Docker: um PC velho, um Raspberry Pi 5 de 4 GB ou um servidor da
faculdade. Ele precisa de uns 2 GB de memória livres e de ficar ligado.

1. **Linux e Docker.** Num PC com Ubuntu ou Debian: `sudo apt install docker.io docker-compose-v2 git`.
   No Windows, primeiro o WSL (`wsl --install`, como administrador, e reiniciar), depois o mesmo comando dentro do Ubuntu.
2. **Código:** `git clone -b claude/vibrant-feynman-4fhs11 https://github.com/nicollaspaulo51-cyber/wishlens.git`
   e `cd wishlens/servidor`.
3. **Chaves:** `cp .env.example .env` e preencha `SUPABASE_URL` e `SUPABASE_KEY` (a chave anon, a mesma dos Secrets
   do Streamlit). Sem elas o jogo fica em memória, bom para testar.
4. **Subir:** `docker compose up -d --build`. A primeira vez leva uns 10 min (PyTorch e CLIP).
   Teste em `http://<ip-da-máquina>:7860/saude`. O juiz volta sozinho se a máquina reiniciar.
5. **Acesso pela internet (HTTPS):** o celular precisa de HTTPS fora da rede local.
   - No roteador, encaminhe as portas 80 e 443 para esta máquina.
   - Aponte um domínio para o IP público (o da faculdade é o ideal) e ponha-o em `DOMINIO` no `.env`.
   - `docker compose --profile https up -d`: o Caddy pega o certificado do Let's Encrypt sozinho.
6. **No app:** `EXPO_PUBLIC_SERVIDOR_URL=https://<DOMINIO>` em `app_celular/.env`.
7. **Atualizar** quando houver código novo no GitHub: `docker compose up -d --build`.

Internet por 4G ou com CGNAT não deixa abrir portas: nesse caso, use a rede da faculdade.
