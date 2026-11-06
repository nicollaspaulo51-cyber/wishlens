# Configurar o Supabase (banco de dados + login)

Sem o Supabase, o WishLens funciona em **modo protótipo**: os desejos ficam só na sessão do navegador.
Com ele, cada pessoa tem uma conta, os desejos ficam salvos na nuvem e a comparação passa a exigir
um pedido de conexão aceito, registrado no banco.

> ⚠️ O código (`src/banco.py`) e o SQL (`supabase/schema.sql`) foram escritos, mas **ainda não foram testados
> contra um projeto Supabase real**. Se algo falhar, a mensagem de erro aparece no app.

## Passo a passo

1. **Crie o projeto.** Acesse [supabase.com](https://supabase.com), entre com o GitHub, clique em
   **New project**, dê o nome `wishlens`, escolha a região **South America (São Paulo)** e uma senha
   forte para o banco (guarde-a).
2. **Crie as tabelas.** No menu lateral, abra **SQL Editor** → **New query**, cole todo o conteúdo de
   [`supabase/schema.sql`](../supabase/schema.sql) e clique em **Run**. Isso cria:
   - `perfis`: apelido de cada pessoa (criado automaticamente no cadastro);
   - `desejos`: um registro por foto/desejo;
   - `conexoes`: pedidos de conexão entre duas pessoas (com aceite);
   - o bucket privado `fotos`;
   - as regras de segurança (RLS): cada pessoa só vê os próprios desejos e os de conexões aceitas.
3. **(Opcional, para testes)** Em **Authentication → Sign In / Providers → Email**, desligue
   **Confirm email** para não precisar confirmar o e-mail a cada conta de teste.
4. **Copie as chaves.** Em **Project Settings → API**, copie a **Project URL** e a chave **anon public**.
5. **Configure o app.**
   - **Rodando no Streamlit Cloud:** em *App settings → Secrets*, cole:
     ```toml
     SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
     SUPABASE_KEY = "sua-anon-key"
     ```
   - **Rodando no computador:** crie `.streamlit/secrets.toml` com o mesmo conteúdo
     (modelo em `.streamlit/secrets.toml.example`). Esse arquivo está no `.gitignore` e **nunca** deve ir para o GitHub.
6. **Instale o pacote** `supabase` (já está no `requirements.txt`).

Pronto: ao abrir o app, a barra lateral mostra **Entrar / Criar conta** em vez do campo de nome.

## Como os dados ficam protegidos

| Regra | Onde |
|---|---|
| Cada pessoa só lê os próprios desejos e os de conexões **aceitas** | política `desejos_ler` |
| Só quem recebeu o pedido pode aceitar a conexão | política `conexoes_aceitar` |
| Fotos ficam numa pasta com o id da pessoa, em bucket privado | política `fotos_proprias` |
| A localização guardada é só a cidade (nunca coordenadas) | coluna `cidade` + `src/fotos.py` |
| A chave usada pelo app é a pública (`anon`); a RLS é quem protege | `.streamlit/secrets.toml` |

## Exportar para a análise

Na página **Meus Desejos → Ver tabela completa e baixar**, o botão **Baixar CSV anonimizado**
gera o arquivo usado nos notebooks (`src/exportar.py`): sem nomes, ids, fotos ou localização exata.
