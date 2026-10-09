-- 献ダテマン（kondate/）：オンラインランキングとレベルごとのレコード
-- 読むのは誰でも可。書き込みは kd_submit_player / kd_submit_record / kd_hide_player だけ（端末で作った合鍵が一致したとき）。
-- ユーザーを消すのは hidden を立てるだけ（関数に DELETE を書くと MCP の適用が確認待ちで止まるため）。

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.kd_players (
  id          uuid primary key,
  name        text        not null check (char_length(name) between 1 and 12),
  food        text        not null check (char_length(food) between 1 and 16),
  emo         text        not null check (char_length(emo) between 1 and 8),
  cleared     int         not null default 0 check (cleared between 0 and 100),
  total_score bigint      not null default 0 check (total_score between 0 and 1000000000),
  quiz_best   int         not null default 0 check (quiz_best between 0 and 10),
  quiz_pass   int         not null default 0 check (quiz_pass >= 0),
  hidden      boolean     not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists kd_players_cleared_idx on public.kd_players (cleared desc, total_score desc);

create table if not exists public.kd_secrets (
  id          uuid primary key,
  secret_hash text not null
);

create table if not exists public.kd_records (
  level     int    not null check (level between 1 and 100),
  player_id uuid   not null references public.kd_players (id),
  score     int    not null check (score between 0 and 10000000),
  time      numeric not null check (time >= 3 and time < 1000),
  set_at    timestamptz not null default now(),
  primary key (level, player_id)
);

alter table public.kd_players enable row level security;
alter table public.kd_secrets enable row level security;
alter table public.kd_records enable row level security;
drop policy if exists "kd players readable" on public.kd_players;
create policy "kd players readable" on public.kd_players for select to anon, authenticated using (true);
drop policy if exists "kd records readable" on public.kd_records;
create policy "kd records readable" on public.kd_records for select to anon, authenticated using (true);
revoke insert, update, delete, truncate, references, trigger on public.kd_players from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger on public.kd_records from anon, authenticated;
revoke all on public.kd_secrets from anon, authenticated;

-- 合鍵の確認（初回は登録）。外からは呼べない
create or replace function public.kd_ok(p_id uuid, p_secret text) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare h text;
begin
  if p_id is null or p_secret is null or char_length(p_secret) < 32 then return false; end if;
  select secret_hash into h from public.kd_secrets where id = p_id;
  if h is null then
    insert into public.kd_secrets (id, secret_hash) values (p_id, crypt(p_secret, gen_salt('bf')));
    return true;
  end if;
  return h = crypt(p_secret, h);
end; $$;
revoke all on function public.kd_ok(uuid, text) from public, anon, authenticated;

create or replace function public.kd_submit_player(
  p_id uuid, p_secret text, p_name text, p_food text, p_emo text,
  p_cleared int, p_total bigint, p_quiz_best int, p_quiz_pass int
) returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.kd_ok(p_id, p_secret) then raise exception 'not the owner'; end if;
  insert into public.kd_players as p (id, name, food, emo, cleared, total_score, quiz_best, quiz_pass, hidden, updated_at)
  values (p_id, btrim(p_name), btrim(p_food), btrim(p_emo), p_cleared, p_total, p_quiz_best, p_quiz_pass, false, now())
  on conflict (id) do update set
    name = excluded.name, food = excluded.food, emo = excluded.emo,
    cleared = excluded.cleared, total_score = excluded.total_score,
    quiz_best = excluded.quiz_best, quiz_pass = excluded.quiz_pass,
    hidden = false, updated_at = now();
end; $$;

-- レベルのスコアとタイムを送る。スコアは高いとき・タイムは速いときだけ上書き
create or replace function public.kd_submit_record(p_id uuid, p_secret text, p_level int, p_score int, p_time numeric)
returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.kd_ok(p_id, p_secret) then raise exception 'not the owner'; end if;
  insert into public.kd_records as r (level, player_id, score, time)
  values (p_level, p_id, p_score, round(p_time, 2))
  on conflict (level, player_id) do update set
    score = greatest(r.score, excluded.score),
    time = least(r.time, excluded.time),
    set_at = now()
  where excluded.score > r.score or excluded.time < r.time;
end; $$;

-- 端末でユーザーを消したらランキングから隠す
create or replace function public.kd_hide_player(p_id uuid, p_secret text) returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.kd_ok(p_id, p_secret) then raise exception 'not the owner'; end if;
  update public.kd_players set hidden = true, updated_at = now() where id = p_id;
end; $$;

revoke all on function public.kd_submit_player(uuid, text, text, text, text, int, bigint, int, int) from public;
revoke all on function public.kd_submit_record(uuid, text, int, int, numeric) from public;
revoke all on function public.kd_hide_player(uuid, text) from public;
grant execute on function public.kd_submit_player(uuid, text, text, text, text, int, bigint, int, int) to anon, authenticated;
grant execute on function public.kd_submit_record(uuid, text, int, int, numeric) to anon, authenticated;
grant execute on function public.kd_hide_player(uuid, text) to anon, authenticated;
