-- ジョッキーロード：ランキングから他の騎手のアバターと部屋を見られるようにする
-- look = { face, equip, room:{wp, fl, items:[{id,x,y,flip}]} }（見た目だけ。お金や成績は入れない）
-- 古いページ（11 引数の submit_jockey）もそのまま動くように、関数は 12 引数版を追加する。

alter table public.leaderboard add column if not exists look jsonb;

alter table public.leaderboard drop constraint if exists leaderboard_look_check;
alter table public.leaderboard add constraint leaderboard_look_check
  check (look is null or (jsonb_typeof(look) = 'object' and pg_column_size(look) <= 8000));

create or replace function public.submit_jockey(
  p_id uuid, p_secret text, p_group text, p_name text,
  p_level int, p_starts int, p_wins int, p_grade_wins int,
  p_income numeric, p_reach text, p_arc boolean, p_look jsonb
) returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  h text;
begin
  if p_secret is null or char_length(p_secret) < 32 then
    raise exception 'invalid secret';
  end if;

  select secret_hash into h from public.jockey_secrets where id = p_id;
  if h is null then
    insert into public.jockey_secrets (id, secret_hash)
    values (p_id, crypt(p_secret, gen_salt('bf')));
  elsif h <> crypt(p_secret, h) then
    raise exception 'not the owner of this jockey';
  end if;

  insert into public.leaderboard as l
    (id, group_code, name, level, starts, wins, grade_wins, income, reach, arc, look, updated_at)
  values
    (p_id, btrim(p_group), btrim(p_name), p_level, p_starts, p_wins, p_grade_wins,
     p_income, p_reach, coalesce(p_arc, false), p_look, now())
  on conflict (id) do update set
    group_code = excluded.group_code,
    name       = excluded.name,
    level      = excluded.level,
    starts     = excluded.starts,
    wins       = excluded.wins,
    grade_wins = excluded.grade_wins,
    income     = excluded.income,
    reach      = excluded.reach,
    arc        = excluded.arc,
    look       = coalesce(excluded.look, l.look),
    updated_at = now();
end;
$$;

revoke all on function public.submit_jockey(uuid, text, text, text, int, int, int, int, numeric, text, boolean, jsonb) from public;
grant execute on function public.submit_jockey(uuid, text, text, text, int, int, int, int, numeric, text, boolean, jsonb) to anon, authenticated;
