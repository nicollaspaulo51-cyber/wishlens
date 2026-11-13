-- WishLens · estrutura do banco no Supabase
-- Como usar: Supabase > SQL Editor > cole este arquivo inteiro > Run.  (Passo a passo: docs/SUPABASE.md)
-- Privacidade: a RLS (Row Level Security) garante que cada pessoa veja só os próprios desejos
-- e os de quem aceitou se conectar com ela.

-- ---------------------------------------------------------------- perfis (apelido público)
create table if not exists public.perfis (
  id         uuid primary key references auth.users (id) on delete cascade,
  apelido    text not null unique check (char_length(apelido) between 2 and 30),
  criado_em  timestamptz not null default now()
);

-- Cria o perfil automaticamente quando alguém se cadastra (apelido vem do cadastro).
create or replace function public.criar_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfis (id, apelido)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'apelido', split_part(new.email, '@', 1)));
  return new;
end $$;

drop trigger if exists ao_criar_usuario on auth.users;
create trigger ao_criar_usuario after insert on auth.users
  for each row execute function public.criar_perfil();

-- ---------------------------------------------------------------- desejos (VERSÃO ANTERIOR)
-- O app não usa mais esta tabela nem a de conexões (eram da parte de compras). Ficam aqui só para não
-- apagar dados de quem já criou o banco; para remover, rode à mão: drop table public.conexoes, public.desejos;
create table if not exists public.desejos (
  id           uuid primary key default gen_random_uuid(),
  usuario_id   uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  criado_em    timestamptz not null default now(),
  item         text not null,
  categoria    text not null,
  tipo         text not null check (tipo in ('comprar', 'receita', 'adotar')),
  faixa_preco  text,
  confianca    real check (confianca is null or confianca between 0 and 1),
  cidade       text,              -- só cidade/bairro, nunca coordenadas exatas
  acao         text,
  foto_path    text,              -- caminho no bucket "fotos" (foto reduzida, sem EXIF)
  marca        text               -- marca reconhecida na foto (opcional)
);
-- Banco criado antes desta coluna: rodar de novo este arquivo a adiciona.
alter table public.desejos add column if not exists marca text;
create index if not exists desejos_usuario_idx on public.desejos (usuario_id, criado_em desc);

-- ---------------------------------------------------------------- capturas do jogo
-- Cada foto do jogo. Os PONTOS não ficam aqui: o app recalcula a partir das capturas (src/jogo.py),
-- então gravar um número falso não adianta.
create table if not exists public.capturas (
  id           uuid primary key default gen_random_uuid(),
  usuario_id   uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  criado_em    timestamptz not null default now(),
  tema         text not null check (char_length(tema) <= 20),
  achado       text not null default '' check (char_length(achado) <= 60),
  confianca    real check (confianca is null or confianca between 0 and 1),
  foto_real    boolean not null default true,
  foto_hash    text check (foto_hash is null or foto_hash ~ '^[0-9a-f]{16}$'),
  cidade       text,              -- só bairro/cidade
  celula       text,              -- quadrado de ~500 m (ex.: "-20.290,-40.295"), nunca a coordenada exata
  foto_path    text
);
create index if not exists capturas_data_idx on public.capturas (criado_em);

-- O que cada juiz disse (avaliação CLIP x Gemma) e a contestação da pessoa. Rodar de novo este arquivo
-- acrescenta as colunas num banco antigo.
alter table public.capturas add column if not exists juiz text check (juiz is null or juiz in ('gemma+clip', 'gemma', 'clip', 'manual'));
alter table public.capturas add column if not exists clip_tema text;
alter table public.capturas add column if not exists clip_foto_real boolean;
alter table public.capturas add column if not exists clip_prob_tema real check (clip_prob_tema is null or clip_prob_tema between 0 and 1);
alter table public.capturas add column if not exists clip_prob_tela real check (clip_prob_tela is null or clip_prob_tela between 0 and 1);
alter table public.capturas add column if not exists clip_rank_tema smallint check (clip_rank_tema is null or clip_rank_tema between 1 and 20);
alter table public.capturas add column if not exists contestada text;

-- ---------------------------------------------------------------- conexões (comparar desejos)
create table if not exists public.conexoes (
  solicitante   uuid not null references public.perfis (id) on delete cascade,
  destinatario  uuid not null references public.perfis (id) on delete cascade,
  aceito        boolean not null default false,
  criado_em     timestamptz not null default now(),
  primary key (solicitante, destinatario),
  check (solicitante <> destinatario)
);

-- Duas pessoas estão conectadas se existe um pedido aceito em qualquer direção.
create or replace function public.conectados(a uuid, b uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.conexoes
    where aceito and ((solicitante = a and destinatario = b) or (solicitante = b and destinatario = a))
  );
$$;

-- ---------------------------------------------------------------- RLS
alter table public.perfis   enable row level security;
alter table public.desejos  enable row level security;
alter table public.conexoes enable row level security;
alter table public.capturas enable row level security;

-- capturas: todo jogador logado vê todas (pódio e raridade); cada um só cria as suas; a única coisa
-- que dá para alterar é a contestação ("o juiz errou, era X") na própria captura, que não muda pontos.
drop policy if exists capturas_ler on public.capturas;
create policy capturas_ler on public.capturas for select to authenticated using (true);
drop policy if exists capturas_criar on public.capturas;
create policy capturas_criar on public.capturas for insert to authenticated
  with check (usuario_id = auth.uid() and criado_em between now() - interval '5 minutes' and now() + interval '1 minute');
drop policy if exists capturas_contestar on public.capturas;
create policy capturas_contestar on public.capturas for update to authenticated
  using (usuario_id = auth.uid()) with check (usuario_id = auth.uid());
revoke update on public.capturas from anon, authenticated;
grant update (contestada) on public.capturas to authenticated;

-- Privacidade: bairro e célula (~500 m) de cada captura NÃO são legíveis pela API, nem para outros jogadores.
-- Sem isso, apelido + hora + lugar formariam um rastro de onde cada pessoa esteve.
revoke select on public.capturas from anon, authenticated;
grant select (id, usuario_id, criado_em, tema, achado, confianca, foto_real, foto_hash,
              juiz, clip_tema, clip_foto_real, clip_prob_tema, clip_prob_tela, clip_rank_tema, contestada)
  on public.capturas to authenticated;

-- O mapa da turma usa só este resumo: por quadrado de ~500 m e tema, sem quem nem quando,
-- e só onde houve pelo menos 2 capturas.
create or replace function public.manchas_capturas()
returns table (celula text, tema text, n bigint, achados text[])
language sql stable security definer set search_path = public as $$
  select c.celula, c.tema, count(*) as n, (array_agg(distinct c.achado))[1:3] as achados
  from public.capturas c
  where c.celula is not null and c.foto_real and c.tema <> 'nenhum'
  group by c.celula, c.tema
  having count(*) >= 2;
$$;
revoke execute on function public.manchas_capturas() from public, anon;
grant execute on function public.manchas_capturas() to authenticated;

-- perfis: qualquer pessoa logada vê apelidos (para pedir conexão); cada um edita o seu.
drop policy if exists perfis_ler on public.perfis;
create policy perfis_ler on public.perfis for select to authenticated using (true);
drop policy if exists perfis_editar on public.perfis;
create policy perfis_editar on public.perfis for update to authenticated using (id = auth.uid());

-- desejos: vejo os meus e os de conexões aceitas; só crio/apago os meus.
drop policy if exists desejos_ler on public.desejos;
create policy desejos_ler on public.desejos for select to authenticated
  using (usuario_id = auth.uid() or public.conectados(auth.uid(), usuario_id));
drop policy if exists desejos_criar on public.desejos;
create policy desejos_criar on public.desejos for insert to authenticated with check (usuario_id = auth.uid());
drop policy if exists desejos_apagar on public.desejos;
create policy desejos_apagar on public.desejos for delete to authenticated using (usuario_id = auth.uid());

-- conexões: vejo as que me envolvem; peço em meu nome; só quem recebeu pode aceitar; ambos podem desfazer.
drop policy if exists conexoes_ler on public.conexoes;
create policy conexoes_ler on public.conexoes for select to authenticated
  using (auth.uid() in (solicitante, destinatario));
drop policy if exists conexoes_pedir on public.conexoes;
create policy conexoes_pedir on public.conexoes for insert to authenticated
  with check (solicitante = auth.uid() and aceito = false);
drop policy if exists conexoes_aceitar on public.conexoes;
create policy conexoes_aceitar on public.conexoes for update to authenticated
  using (destinatario = auth.uid()) with check (destinatario = auth.uid());
drop policy if exists conexoes_desfazer on public.conexoes;
create policy conexoes_desfazer on public.conexoes for delete to authenticated
  using (auth.uid() in (solicitante, destinatario));

-- ---------------------------------------------------------------- fotos (Storage)
-- Bucket privado; cada pessoa só mexe na pasta com o próprio id: fotos/<uid>/<arquivo>.jpg
insert into storage.buckets (id, name, public) values ('fotos', 'fotos', false)
  on conflict (id) do nothing;

drop policy if exists fotos_proprias on storage.objects;
create policy fotos_proprias on storage.objects for all to authenticated
  using (bucket_id = 'fotos' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'fotos' and (storage.foldername(name))[1] = auth.uid()::text);
