# ジョッキーロード — 開発メモ（Claude Code 向け）

若手騎手になって地方競馬から始め、凱旋門賞制覇を目指す競馬ゲーム。オーナー（ryo117ogawa2-netizen）が家族と遊ぶために作っている。UI・実況・コメントはすべて日本語。

## 公開とインフラ

| 役割 | サービス | 場所 |
|---|---|---|
| 本番 | Vercel（GitHub の `main` に push すると自動デプロイ） | https://jockey-road.vercel.app |
| API | Vercel Serverless Function | `api/config.js`（`GET /api/config`） |
| DB | Supabase（プロジェクト `jockey-road`、ref `tujcjbqhbwqxhximmdsv`、東京リージョン） | `supabase/migrations/` |
| リポジトリ | GitHub | `ryo117ogawa2-netizen/jockey-road` |

- `api/config.js` は Supabase の URL と publishable key を返す。Vercel の環境変数 `SUPABASE_URL` / `SUPABASE_ANON_KEY` があればそれを使い、なければコード内の既定値を使う。publishable key はブラウザに公開してよいキーなので、コードに書いてよい。
- Supabase の service_role キーやパスワードは絶対にリポジトリに入れない。
- 本番の動作確認は `https://jockey-road.vercel.app/api/config` が URL とキーを返すかで見られる。

## ファイル構成

- `index.html` — ゲーム本体のすべて（HTML・CSS・JS を 1 ファイルに収めている。ビルド工程なし）
- `api/config.js` — Supabase 接続先を返す関数
- `supabase/migrations/20261007000000_leaderboard.sql` — ランキング用テーブルと関数（本番に適用済み）
- `supabase/migrations/20261009000000_versus_rooms.sql` — 対戦ルーム（`race_rooms` / `room_entries` / `challenges` と関数。本番に適用済み。MCP の apply_migration が大きいと時間切れになるので、本番へはテーブルごと・関数 2〜3 個ずつに分けて適用した）
- `supabase/migrations/20261008000000_leaderboard_look.sql` — `look`（アバターと部屋の見た目）列と 12 引数版 `submit_jockey`（本番に適用済み。古い 11 引数版も残してある）
- `tools/sim.mjs` — レースバランスのシミュレーター（`node tools/sim.mjs derby 100`）
- `package.json` — `"type": "module"` のみ。依存パッケージなし

外部読み込みは Google Fonts（Dela Gothic One / M PLUS Rounded 1c / IBM Plex Mono）だけ。ライブラリは使っていない。

## index.html の中身（JS のセクション）

`/* ------------ 見出し ------------ */` のコメントで区切ってある。

1. `//SIM-START` 〜 `//SIM-END` — レースシミュレーション本体（DOM に触らない純粋なロジック）。`STYLE`（脚質）、`GOING`（馬場）、`createRaceState`、`step`（1 フレーム進める）、`playerAct`（抑える / 手綱 / 促す / 鞭）、`standings`。`tools/sim.mjs` がここを切り出して使うので、DOM 依存を入れないこと。`withSeed(seed, fn)` で出走馬・馬番を固定でき、`opts.ghosts` を渡すと一部の馬がゴースト（記録した位置 `s` を 0.5 秒ごとになぞるだけ。`r.ghost` / `r.ghostOf`、落馬したゴーストは `r.gone`）になる。
2. `data` — `STAGES`（地方 → 中央 → 重賞 → GI → 海外 → 世界ツアー → 伝説への道）と `RACES`（全 27 レース、`tough` 相手の末脚の強さ（後半ステージ用）、`lv` 必要レベル、`need` 解放条件、`R` 相手の強さ、`purse` 1 着賞金（万円））、馬の名前と生成 `genHorse`、レベル関連 `capOf`（乗れる馬の総合値上限 = 30 + Lv×3）、`needExp`（Lv10 を過ぎると (Lv-10)²×2 ずつ上乗せ）。鞭のレベル補正は Lv25 で頭打ち。世界ツアーは凱旋門賞を勝つと解放、伝説への道は世界ツアーで 3 勝すると解放、最終戦は Lv45 のレジェンドカップ。
3. `items` — `SLOTS`（鞭・ヘルメット・ゴーグル・靴・服・小物）と `ITEMS`（67 種。ローラーアイドル衣装＋ローラースケートはセット効果あり＝`gearFx()` の中）。効果 `fx` のキーは
   掛け算: `whip` 鞭の伸び / `kakari` 掛かり率 / `going` 重馬場の影響 / `speed` 巡航速度 / `kick` 末脚 / `fall` 落馬リスク / `yore` ヨレやすさ / `cost` 治療費、
   足し算: `hand` 操縦性 / `stam` スタミナ% / `start` 好スタート判定の秒数（マイナスもあり）/ `odoroki` 鞭で馬がびっくりする確率（魔法のステッキ。直線なら `odorokiT` の間だけ急加速、直線前だと掛かる）。
   `gearFx()` が装備中アイテムを合算する。`weird:1` は「変」マーク付きの変なアイテム（靴下・入れ歯・筋肉増強ベルトなど）。
   - `avatar` — 騎手アバター（SVG）。`avatarSVG(save, bare)` が顔 `S.face`（`FACE_OPTS` の各パーツ番号：肌・髪色・髪型・まゆ・目・口・ほっぺ）と装備 `S.equip` から描く。アイテムの絵は `WHIP_ART` / `HELMET_ART` / `GOGGLE_ART` / `SUIT_ART` / `SHOE_ART` / `ACC_ART`（アイテムを追加したらここにも絵を足す。ヘルメットの絵は髪色を受け取る関数でもよい。髪を隠さないかぶり物は `HAIR_SHOW`、小物の描く場所は `belly` / `hand` / `over` / `head` / `floor` / `mouth`）。`bare=true` は装備なしの顔アップ（顔づくり画面のプレビュー）。「自分の成績」に表示し、「顔をカスタム」で編集。
   - `マイルーム` — 家具・インテリア（`FURN`、kind：`wp` 壁紙 / `fl` 床 / `f` 床に置く家具 / `w` 壁に掛けるもの。絵は足もと中央が原点、`w`/`h` は大きさ）。部屋は SVG（360×300、壁 0〜190）。`S.furn` が持っている家具、`S.room = {wp, fl, items:[{id,x,y,flip}]}`（`id:'me'` は自分のアバター。`avatarParts()` で SVG の中身だけ取り出して縮小して置く）。ドラッグで移動（`roomDown` / `roomMove` / `roomUp`）、「おためし」で買う前に部屋に置いてみられる（`roomTrial`）。見た目だけで、レースへの効果はない。
   - `称号` — `ACHV`（24 個、`ok(save)` で判定）。プロフィールに一覧、レース結果で新しく取った称号を表示。`S.sCount` は騎乗評価 S の回数。
4. `save` — localStorage（キー `jockey-road-v2`）に複数の騎手アカウントを保存。`STORE = {current, list:[{id, save}], music, group}`。`fresh()` が騎手 1 人分の初期データ（`face`・`furn`・`room` を含む。`normRoom()` で補う）、`norm()` が古いデータの移行（旧 `gear` 段階制 → `owned` / `equip`）。v1 キー `jockey-road-v1` からの移行もある。
5. `オンライン` — `/api/config` を取れたときだけ「みんな」ランキングを有効化。各騎手は端末で作った `cloud.id`（UUID）と `cloud.secret` を持ち、RPC `submit_jockey` / `delete_jockey` で送る。見た目は `lookOf()` で送り、ランキングの行をタップすると `openViewer()` がその騎手の部屋とアバターを表示する。よその騎手の見た目は必ず `cleanLook()` で検査してから描く（知らない id・変な値は捨てる）。`group_code` は常に `'all'`（合言葉なし・全員公開がオーナーの希望）。
   - `対戦` — ルーム（全員が同じレース・馬場・相手・馬で 1 回だけ走り、タイムで順位）と対戦の申し込み。`vsLoad` / `renderVersus` / `renderRoomDetail` / `vsRun`（ゴーストを読み込んで出走）/ `vsSubmit`（タイムと位置の記録 `st.rec.s` を送る）。書き込みは RPC `create_room` / `join_room` / `submit_room_result` / `send_challenge` / `respond_challenge`（どれも合鍵を確認）。まだ解放していないレースのルームは「練習あつかい」（賞金なし・経験値 3 割・成績に数えない）。よその騎手の名前は必ず `esc()`、ゴーストの数値は `clamp` してから使う。
6. `screens` — ホームの各パネル描画（`renderHome` / `renderShop`（上に試着欄 `renderTryOn`、`tryId`）/ `renderRoom` / `renderRanking` / `renderMenu`）と出馬表（`openCard` / `genOffers`）。
7. `race runtime` — ゲートのタイミング判定（`startTap`、反応時間メーター `renderGateMeter`。判定幅は `gateZones()`：好 0.38 秒以内 / 五分 0.7 秒以内。開く 0.5〜1.1 秒前に「構えて…」を表示し、開く直前 `GATE_FLY`=0.2 秒以内の早押しは好スタート扱い）、実況（`LINES` / `ACT_LINES`、`pick` で同じセリフの連続を避ける）、♪ / モヤモヤの反応マーク（`react`）、落馬（`fallOff`）、記録（`logTick` → `st.log`）、Canvas 描画（`draw` / `drawHorse` / `drawMood`）。
8. `result` — 着順・賞金（騎手の取り分 = 賞金の 5%）・経験値、騎乗評価表（`evaluateRide`：スタート / 位置取り / 折り合い / 仕掛け / スタミナ配分 / 鞭さばき を ◎○△× で採点、S〜D）、馬からのひとこと（`HORSE_SAYS` / `horseComment`、関西弁の荒ぶった口調）、落馬時の治療費。
9. `音楽` — Web Audio でファンファーレと蹄の音をその場で合成（音源ファイルなし）。スマホは最初のタップまで鳴らせない。
10. `タイトル映像` — Canvas で昼の競馬場と走る馬を描くアニメーション（`drawTitle` / `drawGallop`）。
11. `画面遷移` / `boot` — `show(id)` がセクション（`title` / `home` / `card` / `raceScr` / `result`）を切り替え、`showPanel(name)` がホーム内パネル（`menu` / `name` / `profile` / `races` / `shop` / `room` / `versus`）を切り替える。

## 画面の流れ

タイトル（音楽・スタート）→ 初回のみ騎手名入力 → メニュー（レースに出る / アイテムを買う / 対戦 / マイルーム / 自分の成績）→ 出馬表で馬を選ぶ → ゲート（金色になった瞬間にタップ）→ レース（抑える Z / 手綱を引く X / 促す C / 鞭 Space）→ 結果（馬のひとこと・報酬・騎乗評価・着順表）

## Supabase のテーブル

- `public.leaderboard` — `look jsonb`（8000 バイトまで）にアバター・部屋の見た目。誰でも読める（RLS の select ポリシーのみ）。直接の insert / update / delete は不可。
- `public.jockey_secrets` — 騎手ごとの合鍵のハッシュ（bcrypt）。外からは読めない。
- `submit_jockey(...)` / `delete_jockey(...)` — `security definer`。合鍵が一致したときだけ書き換える。Supabase の診断で「anon が security definer 関数を実行できる」という警告が出るが、ログインなしで成績を送るための意図した設計。
- `public.race_rooms`（参加コード・レース・seed・馬場）/ `public.room_entries`（メンバー・タイム・落馬・ゴースト）/ `public.challenges`（申し込み）— 誰でも読める。書き込みは関数だけ。`jockey_ok()` は合鍵確認用で外からは呼べない。
- スキーマを変えるときは `supabase/migrations/` に新しいファイルを追加する（既存ファイルは書き換えない）。

## 作業の決まりごと

- 変更したら `node --check` 相当の構文チェック（`<script>` の中身を取り出して確認）をしてから commit / push する。push すると本番に出る。
- コミットメッセージは日本語。
- バランス調整は `tools/sim.mjs` で勝率を確かめる。目安：同じ能力の馬で「直線で鞭」が勝率 10〜30%、「何もしない」はほぼ勝てない。
- 見た目は「明るくポップ」：空色の背景、紺（`--frame`）の太いふち取りの白いパネル、黄色（`--sun`）と赤（`--silk`）の差し色、丸ゴシック。色はすべて `:root` のトークンから使う。
- スマホ（幅 400px 前後、iPhone の Safari）で遊ばれる前提。ボタンは押しやすく、横スクロールを出さない。
- 実在のブランドやキャラクターの画像・ロゴは使わない。

## オーナーの今後の希望・アイデア

- App Store に出したい。その場合の注意：
  - Apple Developer Program（年 1 万 3 千円前後）、Mac + Xcode（またはクラウドビルド）、Capacitor などでの包み直しが必要。
  - Web を包んだだけだと審査（最低限の機能）で落ちやすいので、オフライン対応・通知・振動などアプリらしい機能を足す。
  - 有馬記念・日本ダービー・凱旋門賞などのレース名は登録商標の可能性があるので、ストア版では架空のレース名に変えるのが安全。
- 先に PWA 化（manifest とアイコンを付けて「ホーム画面に追加」で全画面起動）するのが手軽。

## 気づいている課題

- 「抑える」は速度 -1.8%・スタミナ消費 -50% で、抑えている時間（直線前、掛かっていないとき）だけ `tame`（溜め、最大 `TAME_MAX`=25 秒）がたまり、直線の伸びに `TAME_KICK` の割合で上乗せされる。レース画面に「溜め」ゲージあり。sim では「前半抑え→直線で鞭」が「直線で鞭」と同等〜やや上（ダービー 24% 対 21%、凱旋門賞 42% 対 30%）。短距離では差が小さい。
- 共有している claude.ai のアーティファクト版はリポジトリ外にあり、`/api/config` に届かないためオンラインランキングは使えない。今後の正式版は Vercel 版（この `index.html`）。
