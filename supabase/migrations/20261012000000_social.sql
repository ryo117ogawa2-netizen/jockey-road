-- ジョッキーロード：掲示板・オンライン表示・友達・個人チャット・プレゼント
-- 掲示板（board_posts）と last_seen は誰でも読める。友達・個人チャット・プレゼントは外から読めず、合鍵を確かめる関数（my_inbox / get_dms など）だけが返す。
-- 本番へは MCP の時間切れを避けるため 7 つに分けて適用した（中身はこのファイルと同じ）。

alter table public.leaderboard add column if not exists last_seen timestamptz;

create table if not exists public.board_posts (
  id         bigint generated always as identity primary key,
  jockey_id  uuid not null,
  name       text not null check (char_length(name) between 1 and 12),
  body       text not null check (char_length(body) between 1 and 200),
  created_at timestamptz not null default now()
);
create index if not exists board_posts_time_idx on public.board_posts (created_at desc);
create index if not exists board_posts_jockey_idx on public.board_posts (jockey_id, created_at desc);
alter table public.board_posts enable row level security;
create policy "board is readable" on public.board_posts for select to anon, authenticated using (true);
revoke insert, update, delete, truncate, references, trigger on public.board_posts from anon, authenticated;

create table if not exists public.friendships (
  from_id    uuid not null,
  to_id      uuid not null,
  status     text not null default 'pending' check (status in ('pending','accepted','declined','removed')),
  created_at timestamptz not null default now(),
  primary key (from_id, to_id),
  check (from_id <> to_id)
);
create index if not exists friendships_to_idx on public.friendships (to_id, status);
alter table public.friendships enable row level security;
revoke all on public.friendships from anon, authenticated;

create table if not exists public.direct_messages (
  id         bigint generated always as identity primary key,
  from_id    uuid not null,
  to_id      uuid not null,
  body       text not null check (char_length(body) between 1 and 300),
  created_at timestamptz not null default now()
);
create index if not exists dm_pair_idx on public.direct_messages (to_id, from_id, id);
alter table public.direct_messages enable row level security;
revoke all on public.direct_messages from anon, authenticated;

create table if not exists public.gifts (
  id         bigint generated always as identity primary key,
  from_id    uuid not null,
  from_name  text not null,
  to_id      uuid not null,
  kind       text not null check (kind in ('item','furn','money')),
  item_id    text check (item_id is null or char_length(item_id) <= 32),
  amount     numeric not null default 0 check (amount >= 0 and amount <= 1000000),
  note       text check (note is null or char_length(note) <= 60),
  created_at timestamptz not null default now(),
  claimed_at timestamptz
);
create index if not exists gifts_to_idx on public.gifts (to_id, claimed_at);
alter table public.gifts enable row level security;
revoke all on public.gifts from anon, authenticated;

create or replace function public.are_friends(a uuid, b uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.friendships where status = 'accepted' and ((from_id = a and to_id = b) or (from_id = b and to_id = a)));
$$;
revoke all on function public.are_friends(uuid, uuid) from public, anon, authenticated;

create or replace function public.post_board(p_id uuid, p_secret text, p_body text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare nm text; b text := btrim(p_body);
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  if b is null or char_length(b) = 0 then raise exception 'empty'; end if;
  select name into nm from public.leaderboard where id = p_id;
  if nm is null then raise exception 'unknown jockey'; end if;
  if exists (select 1 from public.board_posts where jockey_id = p_id and created_at > now() - interval '5 seconds') then raise exception 'too fast'; end if;
  if (select count(*) from public.board_posts where jockey_id = p_id and created_at > now() - interval '1 day') >= 200 then raise exception 'too many'; end if;
  insert into public.board_posts (jockey_id, name, body) values (p_id, nm, left(b, 200));
end;
$$;
revoke all on function public.post_board(uuid, text, text) from public;
grant execute on function public.post_board(uuid, text, text) to anon, authenticated;

create or replace function public.friend_request(p_id uuid, p_secret text, p_to uuid)
returns text language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  if p_to = p_id or not exists (select 1 from public.leaderboard where id = p_to) then raise exception 'unknown jockey'; end if;
  if public.are_friends(p_id, p_to) then return 'already'; end if;
  if exists (select 1 from public.friendships where from_id = p_to and to_id = p_id and status = 'pending') then
    update public.friendships set status = 'accepted' where from_id = p_to and to_id = p_id;
    return 'accepted';
  end if;
  if (select count(*) from public.friendships where from_id = p_id and status = 'pending') >= 50 then raise exception 'too many'; end if;
  insert into public.friendships (from_id, to_id, status) values (p_id, p_to, 'pending')
  on conflict (from_id, to_id) do update set status = 'pending', created_at = now();
  return 'sent';
end;
$$;

create or replace function public.friend_respond(p_id uuid, p_secret text, p_from uuid, p_accept boolean)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.friendships set status = case when p_accept then 'accepted' else 'declined' end
   where from_id = p_from and to_id = p_id and status = 'pending';
  if not found then raise exception 'request not found'; end if;
end;
$$;

create or replace function public.friend_remove(p_id uuid, p_secret text, p_other uuid)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.friendships set status = 'removed'
   where (from_id = p_id and to_id = p_other) or (from_id = p_other and to_id = p_id);
end;
$$;
revoke all on function public.friend_request(uuid, text, uuid) from public;
revoke all on function public.friend_respond(uuid, text, uuid, boolean) from public;
revoke all on function public.friend_remove(uuid, text, uuid) from public;
grant execute on function public.friend_request(uuid, text, uuid) to anon, authenticated;
grant execute on function public.friend_respond(uuid, text, uuid, boolean) to anon, authenticated;
grant execute on function public.friend_remove(uuid, text, uuid) to anon, authenticated;

create or replace function public.send_dm(p_id uuid, p_secret text, p_to uuid, p_body text)
returns bigint language plpgsql security definer set search_path = public, extensions as $$
declare b text := btrim(p_body); nid bigint;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  if not public.are_friends(p_id, p_to) then raise exception 'not friends'; end if;
  if b is null or char_length(b) = 0 then raise exception 'empty'; end if;
  if exists (select 1 from public.direct_messages where from_id = p_id and created_at > now() - interval '2 seconds') then raise exception 'too fast'; end if;
  insert into public.direct_messages (from_id, to_id, body) values (p_id, p_to, left(b, 300)) returning id into nid;
  return nid;
end;
$$;

create or replace function public.get_dms(p_id uuid, p_secret text, p_other uuid, p_after bigint)
returns table (id bigint, from_id uuid, body text, created_at timestamptz)
language plpgsql security definer set search_path = public, extensions as $$
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  return query
    select m.id, m.from_id, m.body, m.created_at from (
      select d.id, d.from_id, d.body, d.created_at from public.direct_messages d
       where ((d.from_id = p_id and d.to_id = p_other) or (d.from_id = p_other and d.to_id = p_id)) and d.id > coalesce(p_after, 0)
       order by d.id desc limit 100) m
    order by m.id;
end;
$$;
revoke all on function public.send_dm(uuid, text, uuid, text) from public;
revoke all on function public.get_dms(uuid, text, uuid, bigint) from public;
grant execute on function public.send_dm(uuid, text, uuid, text) to anon, authenticated;
grant execute on function public.get_dms(uuid, text, uuid, bigint) to anon, authenticated;

create or replace function public.send_gift(p_id uuid, p_secret text, p_to uuid, p_kind text, p_item text, p_amount numeric, p_note text)
returns bigint language plpgsql security definer set search_path = public, extensions as $$
declare nm text; gid bigint;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  if not public.are_friends(p_id, p_to) then raise exception 'not friends'; end if;
  if (select count(*) from public.gifts where to_id = p_to and claimed_at is null) >= 50 then raise exception 'box full'; end if;
  select name into nm from public.leaderboard where id = p_id;
  insert into public.gifts (from_id, from_name, to_id, kind, item_id, amount, note)
  values (p_id, coalesce(nm, '騎手'), p_to, p_kind, case when p_kind = 'money' then null else p_item end,
          case when p_kind = 'money' then coalesce(p_amount, 0) else 0 end, left(btrim(p_note), 60))
  returning id into gid;
  return gid;
end;
$$;

create or replace function public.claim_gift(p_id uuid, p_secret text, p_gift bigint)
returns json language plpgsql security definer set search_path = public, extensions as $$
declare g public.gifts;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.gifts set claimed_at = now() where id = p_gift and to_id = p_id and claimed_at is null returning * into g;
  if g.id is null then raise exception 'gift not found'; end if;
  return json_build_object('id', g.id, 'kind', g.kind, 'item_id', g.item_id, 'amount', g.amount, 'from_name', g.from_name);
end;
$$;
revoke all on function public.send_gift(uuid, text, uuid, text, text, numeric, text) from public;
revoke all on function public.claim_gift(uuid, text, bigint) from public;
grant execute on function public.send_gift(uuid, text, uuid, text, text, numeric, text) to anon, authenticated;
grant execute on function public.claim_gift(uuid, text, bigint) to anon, authenticated;

-- 受信箱：ついでに「いまオンライン」を記録する（30〜60 秒ごとに呼ぶ）
create or replace function public.my_inbox(p_id uuid, p_secret text)
returns json language plpgsql security definer set search_path = public, extensions as $$
declare res json;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  update public.leaderboard set last_seen = now() where id = p_id;
  select json_build_object(
    'requests', coalesce((select json_agg(json_build_object('id', f.from_id, 'name', l.name, 'last_seen', l.last_seen) order by f.created_at desc)
       from public.friendships f join public.leaderboard l on l.id = f.from_id where f.to_id = p_id and f.status = 'pending'), '[]'::json),
    'sent', coalesce((select json_agg(f.to_id) from public.friendships f where f.from_id = p_id and f.status = 'pending'), '[]'::json),
    'friends', coalesce((select json_agg(json_build_object('id', l.id, 'name', l.name, 'level', l.level, 'last_seen', l.last_seen, 'look', l.look,
         'last_in', (select max(d.id) from public.direct_messages d where d.from_id = l.id and d.to_id = p_id)) order by l.name)
       from public.leaderboard l
       where l.id in (select case when f.from_id = p_id then f.to_id else f.from_id end from public.friendships f
                      where f.status = 'accepted' and (f.from_id = p_id or f.to_id = p_id))), '[]'::json),
    'gifts', coalesce((select json_agg(json_build_object('id', g.id, 'from_name', g.from_name, 'kind', g.kind, 'item_id', g.item_id, 'amount', g.amount, 'note', g.note, 'created_at', g.created_at) order by g.id)
       from public.gifts g where g.to_id = p_id and g.claimed_at is null), '[]'::json)
  ) into res;
  return res;
end;
$$;
revoke all on function public.my_inbox(uuid, text) from public;
grant execute on function public.my_inbox(uuid, text) to anon, authenticated;
