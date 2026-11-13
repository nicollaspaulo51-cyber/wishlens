# Configurar o Supabase (banco de dados + login)

Sem o Supabase, o WishLens funciona em **modo protótipo**: as capturas do jogo ficam só na sessão do navegador,
então **o pódio mostra só você** (e os dados de exemplo). Para a turma jogar junto, o Supabase é obrigatório.
Com ele, cada pessoa tem uma conta, as capturas ficam salvas na nuvem e o pódio passa a juntar a turma.

> ⚠️ O código (`src/banco.py`) e o SQL (`supabase/schema.sql`) foram escritos, mas **ainda não foram testados
> contra um projeto Supabase real**. Se algo falhar, a mensagem de erro aparece no app.

## Passo a passo

1. **Crie o projeto.** Acesse [supabase.com](https://supabase.com), entre com o GitHub, clique em
   **New project**, dê o nome `wishlens`, escolha a região **South America (São Paulo)** e uma senha
   forte para o banco (guarde-a).
2. **Crie as tabelas.** No menu lateral, abra **SQL Editor** → **New query**, cole todo o conteúdo de
   [`supabase/schema.sql`](../supabase/schema.sql) e clique em **Run**. Isso cria:
   - `perfis`: apelido de cada pessoa (criado automaticamente no cadastro);
   - `desejos` e `conexoes`: da versão anterior (compras), não usadas pelo app;
   - `capturas`: uma linha por foto do jogo (pódio, coleção e mapa);
   - o bucket privado `fotos`;
   - as regras de segurança (RLS) das capturas (ver a tabela abaixo).
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

Pronto: ao abrir o app, a página Jogar mostra **Entre para jogar** (e a barra lateral, **Entrar / Criar conta**).

### Testar o pódio compartilhado
1. Crie duas contas (ex.: no celular e no computador, ou numa janela anônima).
2. Tire uma foto com cada uma em **Jogar**.
3. Abra **Pódio**: as duas contas devem aparecer.

Já tinha rodado o `schema.sql` antes? Rode de novo: ele usa `if not exists` e só acrescenta o que falta (tabela `capturas`, coluna `marca`).

## Como os dados ficam protegidos

| Regra | Onde |
|---|---|
| Fotos ficam numa pasta com o id da pessoa, em bucket privado | política `fotos_proprias` |
| A localização guardada é só a cidade (nunca coordenadas) | coluna `cidade` + `src/fotos.py` |
| Capturas: todos os logados leem (pódio), cada um só cria as suas, com a hora de agora; ninguém altera | políticas `capturas_ler` e `capturas_criar` |
| Bairro e célula das capturas não são legíveis pela API (nem pelos outros jogadores) | `grant select (...)` só nas outras colunas |
| O mapa da turma só recebe totais por quadrado e tema, sem quem/quando, com 2+ capturas | função `manchas_capturas()` |
| No jogo, a posição fica num quadrado de ~500 m, nunca exata | coluna `celula` |
| A chave usada pelo app é a pública (`anon`); a RLS é quem protege | `.streamlit/secrets.toml` |

## Exportar para a análise

Na página **Meus Desejos → Ver tabela completa e baixar**, o botão **Baixar CSV anonimizado**
gera o arquivo usado nos notebooks (`src/exportar.py`): sem nomes, ids, fotos ou localização exata.
