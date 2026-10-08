-- ジョッキーロード：対戦ルームと対戦の申し込み
-- ルームに集まった騎手が「同じレース・同じ馬場・同じ相手・同じ馬」で走り、タイムで順位を競う（ゴースト対戦）。
-- 先に走った人の走り（ghost = 0.5 秒ごとの位置）は、あとから走る人のレースにゴーストとして出てくる。
-- 読むのは誰でも可。書き込みは下の関数だけ（騎手の合鍵 = jockey_secrets が一致したときだけ）。

create table if not exists public.race_rooms (
  id          uuid primary key default gen_random_uuid(),
  code        text not null unique check (code ~ '^[A-Z0-9]{6}$'),
  title       text not null check (char_length(title) between 1 and 24),
  race_id     text not null check (char_length(race_id) between 1 and 32),
  seed        int  not null,
  going       text not null check (going in ('良','稍重','重','不良')),
  host_id     uuid not null,
  created_at  timestamptz not null default now()
);

create table if not exists public.room_entries (
  room_id     uuid not null references public.race_rooms(id) on delete cascade,
  jockey_id   uuid not null,
  name        text not null check (char_length(name) between 1 and 12),
  look        jsonb check (look is null or (jsonb_typeof(look) = 'object' and pg_column_size(look) <= 8000)),
  time        numeric check (time is null or (time > 0 and time < 1000)),
  fell        boolean not null default false,
  ghost       jsonb check (ghost is null or (jsonb_typeof(ghost) = 'array' and pg_column_size(ghost) <= 20000)),
  finished_at timestamptz,
  joined_at   timestamptz not null default now(),
  primary key (room_id, jockey_id)
);
create index if not exists room_entries_jockey_idx on public.room_entries (jockey_id);

create table if not exists public.challenges (
  id          uuid primary key default gen_random_uuid(),
  room_id     uuid not null references public.race_rooms(id) on delete cascade,
  from_id     uuid not null,
  from_name   text not null,
  to_id       uuid not null,
  to_name     text not null,
  status      text not null default 'pending' check (status in ('pending','accepted','declined')),
  created_at  timestamptz not null default now()
);
create index if not exists challenges_to_idx on public.challenges (to_id, status);

alter table public.race_rooms   enable row level security;
alter table public.room_entries enable row level security;
alter table public.challenges   enable row level security;

drop policy if exists "rooms are readable" on public.race_rooms;
create policy "rooms are readable" on public.race_rooms for select to anon, authenticated using (true);
drop policy if exists "entries are readable" on public.room_entries;
create policy "entries are readable" on public.room_entries for select to anon, authenticated using (true);
drop policy if exists "challenges are readable" on public.challenges;
create policy "challenges are readable" on public.challenges for select to anon, authenticated using (true);

revoke insert, update, delete on public.race_rooms, public.room_entries, public.challenges from anon, authenticated;

-- 合鍵の確認（外からは呼べない）
create or replace function public.jockey_ok(p_id uuid, p_secret text)
returns boolean
language sql stable
security definer
set search_path = public, extensions
as $$
  select exists (select 1 from public.jockey_secrets where id = p_id and secret_hash = crypt(p_secret, secret_hash));
$$;
revoke all on function public.jockey_ok(uuid, text) from public, anon, authenticated;

-- ルームを作る（作った人は自動で参加）
create or replace function public.create_room(
  p_id uuid, p_secret text, p_name text, p_look jsonb, p_title text, p_race text, p_going text
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  rid uuid; c text; tries int := 0;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  if (select count(*) from public.race_rooms where host_id = p_id and created_at > now() - interval '1 day') >= 30 then
    raise exception 'too many rooms';
  end if;
  loop
    c := upper(substr(md5(random()::text || clock_timestamp()::text), 1, 6));
    exit when not exists (select 1 from public.race_rooms where code = c);
    tries := tries + 1;
    if tries > 10 then raise exception 'could not make a code'; end if;
  end loop;
  insert into public.race_rooms (code, title, race_id, seed, going, host_id)
  values (c, btrim(p_title), p_race, floor(random() * 2147483647)::int, p_going, p_id)
  returning id into rid;
  insert into public.room_entries (room_id, jockey_id, name, look) values (rid, p_id, btrim(p_name), p_look);
  return json_build_object('id', rid, 'code', c);
end;
$$;

-- コードで参加する（1 ルーム 11 人まで）
create or replace function public.join_room(
  p_id uuid, p_secret text, p_name text, p_look jsonb, p_code text
) returns uuid
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  rid uuid;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  select id into rid from public.race_rooms where code = upper(btrim(p_code));
  if rid is null then raise exception 'room not found'; end if;
  if exists (select 1 from public.room_entries where room_id = rid and jockey_id = p_id) then return rid; end if;
  if (select count(*) from public.room_entries where room_id = rid) >= 11 then raise exception 'room is full'; end if;
  insert into public.room_entries (room_id, jockey_id, name, look) values (rid, p_id, btrim(p_name), p_look);
  return rid;
end;
$$;

-- 走った結果を送る（1 ルーム 1 回だけ）
create or replace function public.submit_room_result(
  p_id uuid, p_secret text, p_room uuid, p_time numeric, p_fell boolean, p_ghost jsonb
) returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.room_entries
     set time = case when p_fell then null else p_time end,
         fell = coalesce(p_fell, false),
         ghost = p_ghost,
         finished_at = now()
   where room_id = p_room and jockey_id = p_id and finished_at is null;
  if not found then raise exception 'not in this room or already finished'; end if;
end;
$$;

-- 対戦を申し込む（ルームのメンバーが、ランキングにいる騎手を招待する）
create or replace function public.send_challenge(
  p_id uuid, p_secret text, p_room uuid, p_to uuid
) returns uuid
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  fname text; tname text; cid uuid;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  select name into fname from public.room_entries where room_id = p_room and jockey_id = p_id;
  if fname is null then raise exception 'not in this room'; end if;
  select name into tname from public.leaderboard where id = p_to;
  if tname is null or p_to = p_id then raise exception 'unknown jockey'; end if;
  if exists (select 1 from public.room_entries where room_id = p_room and jockey_id = p_to) then raise exception 'already in this room'; end if;
  if (select count(*) from public.challenges where from_id = p_id and status = 'pending') >= 30 then raise exception 'too many challenges'; end if;
  select id into cid from public.challenges where room_id = p_room and to_id = p_to and status = 'pending';
  if cid is not null then return cid; end if;
  insert into public.challenges (room_id, from_id, from_name, to_id, to_name)
  values (p_room, p_id, fname, p_to, tname) returning id into cid;
  return cid;
end;
$$;

-- 申し込みに答える（受けるとルームに参加）
create or replace function public.respond_challenge(
  p_id uuid, p_secret text, p_name text, p_look jsonb, p_challenge uuid, p_accept boolean
) returns uuid
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  rid uuid;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.challenges set status = case when p_accept then 'accepted' else 'declined' end
   where id = p_challenge and to_id = p_id and status = 'pending'
   returning room_id into rid;
  if rid is null then raise exception 'challenge not found'; end if;
  if p_accept then
    if (select count(*) from public.room_entries where room_id = rid) >= 11 then raise exception 'room is full'; end if;
    insert into public.room_entries (room_id, jockey_id, name, look) values (rid, p_id, btrim(p_name), p_look)
    on conflict do nothing;
  end if;
  return rid;
end;
$$;

revoke all on function public.create_room(uuid, text, text, jsonb, text, text, text) from public;
revoke all on function public.join_room(uuid, text, text, jsonb, text) from public;
revoke all on function public.submit_room_result(uuid, text, uuid, numeric, boolean, jsonb) from public;
revoke all on function public.send_challenge(uuid, text, uuid, uuid) from public;
revoke all on function public.respond_challenge(uuid, text, text, jsonb, uuid, boolean) from public;
grant execute on function public.create_room(uuid, text, text, jsonb, text, text, text) to anon, authenticated;
grant execute on function public.join_room(uuid, text, text, jsonb, text) to anon, authenticated;
grant execute on function public.submit_room_result(uuid, text, uuid, numeric, boolean, jsonb) to anon, authenticated;
grant execute on function public.send_challenge(uuid, text, uuid, uuid) to anon, authenticated;
grant execute on function public.respond_challenge(uuid, text, text, jsonb, uuid, boolean) to anon, authenticated;

-- PostgREST からは使えないが、念のため
revoke truncate, references, trigger on public.race_rooms, public.room_entries, public.challenges from anon, authenticated;
comment on table public.leaderboard is 'ジョッキーロードの騎手ランキング';
