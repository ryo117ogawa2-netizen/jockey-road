-- ジョッキーロード：レースごとのレコード（騎手ごとの自己ベスト。全員のなかで一番速いのがコースレコード）
-- 読むのは誰でも可。書き込みは submit_record だけ（合鍵が一致したとき、自己ベストを更新したときだけ書き換える）。

create table if not exists public.race_records (
  race_id   text not null check (char_length(race_id) between 1 and 32),
  jockey_id uuid not null,
  name      text not null check (char_length(name) between 1 and 12),
  time      numeric not null check (time >= 30 and time < 1000),
  horse     text check (horse is null or char_length(horse) <= 16),
  going     text check (going is null or going in ('良','稍重','重','不良')),
  set_at    timestamptz not null default now(),
  primary key (race_id, jockey_id)
);
create index if not exists race_records_time_idx on public.race_records (race_id, time);
alter table public.race_records enable row level security;
drop policy if exists "records are readable" on public.race_records;
create policy "records are readable" on public.race_records for select to anon, authenticated using (true);
revoke insert, update, delete, truncate, references, trigger on public.race_records from anon, authenticated;

-- レースごとの 1 位（コースレコード）
create or replace view public.race_top with (security_invoker = true) as
  select distinct on (race_id) race_id, name, time, horse, going, set_at
  from public.race_records
  order by race_id, time, set_at;
grant select on public.race_top to anon, authenticated;

-- タイムを送る。自己ベストを更新したら true
create or replace function public.submit_record(
  p_id uuid, p_secret text, p_name text, p_race text, p_time numeric, p_horse text, p_going text
) returns boolean
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  n int;
begin
  if not public.jockey_ok(p_id, p_secret) then raise exception 'not the owner of this jockey'; end if;
  insert into public.race_records as r (race_id, jockey_id, name, time, horse, going)
  values (p_race, p_id, btrim(p_name), round(p_time, 2), left(p_horse, 16), p_going)
  on conflict (race_id, jockey_id) do update
    set time = excluded.time, name = excluded.name, horse = excluded.horse, going = excluded.going, set_at = now()
    where excluded.time < r.time;
  get diagnostics n = row_count;
  return n > 0;
end;
$$;
revoke all on function public.submit_record(uuid, text, text, text, numeric, text, text) from public;
grant execute on function public.submit_record(uuid, text, text, text, numeric, text, text) to anon, authenticated;

-- メモ：騎手を消したときにレコードも消すよう delete_jockey を変えたかったが、本番への適用がツールの確認待ちで止まるため見送り。
--      いまは騎手を消してもレコード（名前とタイム）は残る。
