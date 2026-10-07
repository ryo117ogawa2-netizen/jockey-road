-- ジョッキーロード：オンラインランキング
-- 誰でも読めるが、書き込みは submit_jockey / delete_jockey 関数経由のみ。
-- 各騎手は端末で作った秘密の合鍵（secret）を持ち、合鍵が一致しないと更新・削除できない。

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.leaderboard (
  id          uuid primary key,
  group_code  text        not null check (char_length(group_code) between 1 and 32),
  name        text        not null check (char_length(name) between 1 and 12),
  level       int         not null default 1 check (level between 1 and 200),
  starts      int         not null default 0 check (starts >= 0),
  wins        int         not null default 0 check (wins >= 0 and wins <= starts),
  grade_wins  int         not null default 0 check (grade_wins >= 0 and grade_wins <= wins),
  income      numeric     not null default 0 check (income >= 0),
  reach       text        not null default '地方' check (char_length(reach) <= 16),
  arc         boolean     not null default false,
  updated_at  timestamptz not null default now()
);
create index if not exists leaderboard_group_idx on public.leaderboard (group_code);

create table if not exists public.jockey_secrets (
  id          uuid primary key,
  secret_hash text not null
);

alter table public.leaderboard    enable row level security;
alter table public.jockey_secrets enable row level security;

drop policy if exists "leaderboard is readable" on public.leaderboard;
create policy "leaderboard is readable" on public.leaderboard
  for select to anon, authenticated using (true);

revoke insert, update, delete on public.leaderboard from anon, authenticated;
revoke all on public.jockey_secrets from anon, authenticated;

create or replace function public.submit_jockey(
  p_id uuid, p_secret text, p_group text, p_name text,
  p_level int, p_starts int, p_wins int, p_grade_wins int,
  p_income numeric, p_reach text, p_arc boolean
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
    (id, group_code, name, level, starts, wins, grade_wins, income, reach, arc, updated_at)
  values
    (p_id, btrim(p_group), btrim(p_name), p_level, p_starts, p_wins, p_grade_wins,
     p_income, p_reach, coalesce(p_arc, false), now())
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
    updated_at = now();
end;
$$;

create or replace function public.delete_jockey(p_id uuid, p_secret text)
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  h text;
begin
  select secret_hash into h from public.jockey_secrets where id = p_id;
  if h is null or h <> crypt(p_secret, h) then
    raise exception 'not the owner of this jockey';
  end if;
  delete from public.leaderboard where id = p_id;
  delete from public.jockey_secrets where id = p_id;
end;
$$;

revoke all on function public.submit_jockey(uuid, text, text, text, int, int, int, int, numeric, text, boolean) from public;
revoke all on function public.delete_jockey(uuid, text) from public;
grant execute on function public.submit_jockey(uuid, text, text, text, int, int, int, int, numeric, text, boolean) to anon, authenticated;
grant execute on function public.delete_jockey(uuid, text) to anon, authenticated;
