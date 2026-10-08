-- ジョッキーロード：コースレコード一覧で「自分のレコード」がわかるよう、race_top に jockey_id を足す（列は最後に追加）
create or replace view public.race_top with (security_invoker = true) as
  select distinct on (race_id) race_id, name, time, horse, going, set_at, jockey_id
  from public.race_records
  order by race_id, time, set_at;
grant select on public.race_top to anon, authenticated;
