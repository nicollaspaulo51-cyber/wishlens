-- Rode uma vez no SQL Editor: libera as tabelas para quem está logado (corrige "permission denied for table").
-- A RLS continua valendo: cada pessoa só vê e mexe no que as políticas do schema.sql permitem.
grant usage on schema public to authenticated;
grant select, insert, update, delete on public.perfis, public.desejos, public.conexoes to authenticated;
grant insert on public.capturas to authenticated;
-- capturas: leitura só das colunas sem lugar (privacidade) e alteração só da contestação
grant select (id, usuario_id, criado_em, tema, achado, confianca, foto_real, foto_hash,
              juiz, clip_tema, clip_foto_real, clip_prob_tema, clip_prob_tela, clip_rank_tema, contestada,
              mirante, tipo_lugar, clima, km_anterior, min_anterior, mesmo_objeto)
  on public.capturas to authenticated;
grant update (contestada) on public.capturas to authenticated;
grant execute on function public.manchas_capturas() to authenticated;
grant execute on function public.guardioes_quadrados() to authenticated;
grant execute on function public.objeto_visto(text, text, text) to authenticated;
