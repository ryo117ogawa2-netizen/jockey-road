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
- `supabase/migrations/20261012000000_social.sql` — 掲示板・オンライン表示・友達・個人チャット・プレゼント（本番に適用済み。7 つに分けて適用。関数の中に DELETE / DROP を書くと MCP が確認待ちで止まるので、友達をやめる・断るは `status` の更新で表している）
- `supabase/migrations/20261011000000_race_top_jockey.sql` — `race_top` ビューに `jockey_id` を追加（本番に適用済み）
- `supabase/migrations/20261010000000_race_records.sql` — レースレコード（`race_records`、ビュー `race_top`、関数 `submit_record`。本番に適用済み。`delete_jockey` を書きかえてレコードも消す案は、MCP の確認待ちで止まるので見送り）
- `supabase/migrations/20261008000000_leaderboard_look.sql` — `look`（アバターと部屋の見た目）列と 12 引数版 `submit_jockey`（本番に適用済み。古い 11 引数版も残してある）
- `kondate/index.html` — 別ゲーム「献ダテマン」（`/kondate/`）。空を飛んで料理をよける全 100 レベル（10 ごとにボス、ボスを倒すとスキル）。ユーザー登録（名前＋好きな料理＋アイコン）、レベルごとのスコア・タイムのレコード、ランキング（名前を押すとユーザー情報と好きな料理）、ミニゲーム「管理栄養士試験」（`QUIZ` 50 問から 10 問、6 問以上で合格）。localStorage キー `kondateman-v1`。オンラインは同じ `/api/config` を使う。
- `supabase/migrations/20261013000000_kondate.sql` — 献ダテマン用（`kd_players` / `kd_records` / `kd_secrets`、関数 `kd_submit_player` / `kd_submit_record` / `kd_hide_player`。本番に適用済み。ユーザー削除は `hidden` を立てるだけ。動作テストで作ったユーザーは hidden 済み）
- `tools/sim.mjs` — レースバランスのシミュレーター（`node tools/sim.mjs derby 100`）
- `package.json` — `"type": "module"` のみ。依存パッケージなし

外部読み込みは Google Fonts（Dela Gothic One / M PLUS Rounded 1c / IBM Plex Mono）だけ。ライブラリは使っていない。

## index.html の中身（JS のセクション）

`/* ------------ 見出し ------------ */` のコメントで区切ってある。

1. `//SIM-START` 〜 `//SIM-END` — レースシミュレーション本体（DOM に触らない純粋なロジック）。`STYLE`（脚質）、`GOING`（馬場）、`createRaceState`、`step`（1 フレーム進める）、`playerAct`（抑える / 手綱 / 促す / 鞭）、`standings`。`tools/sim.mjs` がここを切り出して使うので、DOM 依存を入れないこと。`withSeed(seed, fn)` で出走馬・馬番を固定でき、`opts.ghosts` を渡すと一部の馬がゴースト（記録した位置 `s` を 0.5 秒ごとになぞるだけ。`r.ghost` / `r.ghostOf`、落馬したゴーストは `r.gone`）になる。魔界の乗りもの `BEASTS`（馬・犬・牛・ライオン・ウサギ・ブタ・カメ・ゾウ・カンガルー・チーター・ドラゴン。`sp` 巡航速度× → `r.bSpeed`、`st`/`bu`/`ha` は能力の補正、`w` は出やすさ）と `pickBeast(luck)` / `applyBeast()`。`race.makai` のレースでは相手も乗りものがランダムで、名前は `DEMON_PRE`＋動物名。
2. `data` — `STAGES`（地方 → 中央 → 重賞 → GI → 海外 → 世界ツアー → 伝説への道 → 魔界（`secret`、招待されるまで隠す））と `RACES`（全 30 レース、`makai` 魔界レース、`tough` 相手の末脚の強さ（後半ステージ用）、`lv` 必要レベル、`need` 解放条件、`R` 相手の強さ、`purse` 1 着賞金（万円））、馬の名前と生成 `genHorse`、レベル関連 `capOf`（乗れる馬の総合値上限 = 30 + Lv×3）、`needExp`（Lv10 を過ぎると (Lv-10)²×2 ずつ上乗せ）。鞭のレベル補正は Lv25 で頭打ち。世界ツアーは凱旋門賞を勝つと解放、伝説への道は世界ツアーで 3 勝すると解放、最終戦は Lv45 のレジェンドカップ。魔界は騎手収入が 5 億円（50000 万円）を超えると `S.makaiInv` が立ち、招待状 `showMakaiInvite()` が出る。魔界レースは優勝で `purse`（10 億）をまるごと、2 着以下・落馬は同額の罰金（借金になってよい）。出馬表は 5 つの檻（`makaiCages`）で、中身は出走時に明かす。sim では乗りもの次第で勝率がほぼ決まり、全体で 3 割前後。
3. `items` — `SLOTS`（鞭・ヘルメット・ゴーグル・靴・服・小物）と `ITEMS`（73 種。高額品：ダイヤモンドの鞭・プラチナヘルメット・純金ゴーグル・ジェットブーツ・金ピカ勝負服・悪魔の契約書（`luck`＝魔界で速い乗りものが出やすい）。ローラーアイドル衣装＋ローラースケートはセット効果あり＝`gearFx()` の中）。効果 `fx` のキーは
   掛け算: `whip` 鞭の伸び / `kakari` 掛かり率 / `going` 重馬場の影響 / `speed` 巡航速度 / `kick` 末脚 / `fall` 落馬リスク / `yore` ヨレやすさ / `cost` 治療費、
   足し算: `hand` 操縦性 / `stam` スタミナ% / `start` 好スタート判定の秒数（マイナスもあり）/ `luck` 魔界の檻の当たりやすさ / `odoroki` 鞭で馬がびっくりする確率（魔法のステッキ。直線なら `odorokiT` の間だけ急加速、直線前だと掛かる）。
   `gearFx()` が装備中アイテムを合算する。`weird:1` は「変」マーク付きの変なアイテム（靴下・入れ歯・筋肉増強ベルトなど）。
   - `avatar` — 騎手アバター（SVG）。`avatarSVG(save, bare)` が顔 `S.face`（`FACE_OPTS` の各パーツ番号：肌・髪色・髪型・まゆ・目・口・ほっぺ）と装備 `S.equip` から描く。アイテムの絵は `WHIP_ART` / `HELMET_ART` / `GOGGLE_ART` / `SUIT_ART` / `SHOE_ART` / `ACC_ART`（アイテムを追加したらここにも絵を足す。ヘルメットの絵は髪色を受け取る関数でもよい。髪を隠さないかぶり物は `HAIR_SHOW`、小物の描く場所は `belly` / `hand` / `over` / `head` / `floor` / `mouth`）。`bare=true` は装備なしの顔アップ（顔づくり画面のプレビュー）。「自分の成績」に表示し、「顔をカスタム」で編集。
   - `マイルーム` — 家具・インテリア（`FURN`、kind：`wp` 壁紙 / `fl` 床 / `f` 床に置く家具 / `w` 壁に掛けるもの。絵は足もと中央が原点、`w`/`h` は大きさ）。部屋は SVG（360×300、壁 0〜190）。`S.furn` が持っている家具、`S.room = {wp, fl, items:[{id,x,y,flip}]}`（`id:'me'` は自分のアバター。`avatarParts()` で SVG の中身だけ取り出して縮小して置く）。ドラッグで移動（`roomDown` / `roomMove` / `roomUp`）、「おためし」で買う前に部屋に置いてみられる（`roomTrial`）。見た目だけで、レースへの効果はない。`cat:'lux'` は「ぜいたく」タブ（パートナー 5 億・子供 3 億・ペット 1 億・軽トラ・スポーツカー・リムジン・金のスーパーカー・悪魔の像）。家族は `famSVG()`（アバターと同じ絵、`whip:'none'` / `helmet:'none'` で鞭・帽子なし）、車は `carSVG()`。
   - `称号` — `ACHV`（28 個。魔界の勝者・魔王・協会にバレた・家族ができた を追加、`ok(save)` で判定）。プロフィールに一覧、レース結果で新しく取った称号を表示。`S.sCount` は騎乗評価 S の回数。
4. `save` — localStorage（キー `jockey-road-v2`）に複数の騎手アカウントを保存。`STORE = {current, list:[{id, save}], music, group}`。`fresh()` が騎手 1 人分の初期データ（`face`・`furn`・`room` を含む。`normRoom()` で補う）、`norm()` が古いデータの移行（旧 `gear` 段階制 → `owned` / `equip`）。v1 キー `jockey-road-v1` からの移行もある。
5. `オンライン` — `/api/config` を取れたときだけ「みんな」ランキングを有効化。各騎手は端末で作った `cloud.id`（UUID）と `cloud.secret` を持ち、RPC `submit_jockey` / `delete_jockey` で送る。見た目は `lookOf()` で送り、ランキングの行をタップすると `openViewer()` がその騎手の部屋とアバターを表示する。よその騎手の見た目は必ず `cleanLook()` で検査してから描く（知らない id・変な値は捨てる）。`group_code` は常に `'all'`（合言葉なし・全員公開がオーナーの希望）。
   - `対戦` — ルーム（全員が同じレース・馬場・相手・馬で 1 回だけ走り、タイムで順位）と対戦の申し込み。`vsLoad` / `renderVersus` / `renderRoomDetail` / `vsRun`（ゴーストを読み込んで出走）/ `vsSubmit`（タイムと位置の記録 `st.rec.s` を送る）。書き込みは RPC `create_room` / `join_room` / `submit_room_result` / `send_challenge` / `respond_challenge`（どれも合鍵を確認）。まだ解放していないレースのルームは「練習あつかい」（賞金なし・経験値 3 割・成績に数えない）。よその騎手の名前は必ず `esc()`、ゴーストの数値は `clamp` してから使う。
   - `馬券` — 出馬表で単勝を買える（通常レースのみ。魔界・対戦ルームは不可）。`openCard` で `cardSeed` を決め、`betField()` が同じ seed で `createRaceState` して出走馬とオッズ（総合力の softmax）を出す。本番も同じ seed なので、見せた相手のまま走る。買ったお金は出走時に引き、`finishRace` で精算。`S.betProfit`（馬券の通算もうけ）が `BET_LIMIT`＝1 億円を超えると競馬協会に見つかり、もうけを全額没収（`S.confiscated`）。
   - `レースレコード` — レース中は上に経過タイム（`hClock`）、結果画面にタイムと自己ベスト・コースレコードとの差（`resTime`）。自己ベストは端末の `S.bestTime`、全員分はサーバーの `race_records`（騎手×レースで最速だけ残す）。`fetchRecords()` が `race_top` から各レースの 1 位を `RECORDS` に読み、レース一覧（🏆 ボタン → `openRecords()` でトップ 10）と出馬表のチップに出す。落馬・練習あつかいはタイムを残さない。`records` パネル（メニュー下とレース一覧の「🏆 コースレコード一覧」）の `renderRecordsPanel()` が全レースの 1 位・自分の自己ベストと差・自分の保持数・レコード保持数ランキング（上位 5 人）を出し、行を押すとトップ 10。
   - `ひろば`（`social` パネル）— タブは 掲示板 / 友達 / プレゼント箱。`socPoll()` が 30 秒ごと（画面が見えているときだけ）に `my_inbox` を呼び、ついでに `leaderboard.last_seen` を更新（＝オンライン表示。2 分以内なら「● オンライン」、`onlineTag()`）。掲示板は `board_posts` を直接読む（最新 50 件、200 文字、5 秒に 1 回まで）。ブロックは端末だけ（`S.blocked`）。友達申請はランキングの「のぞく」画面の「友達申請」（`friend_request`、おたがいに申請したら自動で友達）。個人チャット（`send_dm` / `get_dms`、開いている間は 5 秒ごとに読む、既読は `S.dmRead`）とプレゼント（`send_gift` / `claim_gift`、アイテム・家具・お金。贈った側は送れた時点で手元から消し、受け取った側は `claimGift()` で持ち物に足す。すでに持っていたら半額のお金に）は友達だけ。メニューの「ひろば」に未読・申請・プレゼントの件数バッジ。よその騎手の名前・本文は必ず `esc()`。
6. `screens` — ホームの各パネル描画（`renderHome` / `renderShop`（上に試着欄 `renderTryOn`、`tryId`）/ `renderRoom` / `renderRanking` / `renderMenu`）と出馬表（`openCard` / `genOffers`）。
7. `race runtime` — 魔界レースは `body.makai` / `html.makai` で色トークンを暗く入れかえ、Canvas は `drawHellSky`（赤い月・コウモリ・観客の悪魔）と暗いコース、乗りものは `drawBeast`（絵文字を左右反転して描く）。ゲートのタイミング判定（`startTap`、反応時間メーター `renderGateMeter`。判定幅は `gateZones()`：好 0.38 秒以内 / 五分 0.7 秒以内。開く 0.5〜1.1 秒前に「構えて…」を表示し、開く直前 `GATE_FLY`=0.2 秒以内の早押しは好スタート扱い）、実況（`LINES` / `ACT_LINES`、`pick` で同じセリフの連続を避ける）、♪ / モヤモヤの反応マーク（`react`）、落馬（`fallOff`）、記録（`logTick` → `st.log`）、Canvas 描画（`draw` / `drawHorse` / `drawMood`）。
   - `チュートリアル` — `startTutorial()` が練習用の `TUTORIAL_RACE`（`RACES` には入れない、6 頭・弱い相手）を走らせる。`st.tut` があると `tutTick()` が場面ごとに `tutAsk(ボタン, 説明, 終わり判定)` でレースを止め（`simDt=0`）、`coach()` の吹き出しと `.tut-glow` で押すボタンを光らせる。順番は ゲート → 抑える → 掛かり（わざと起こす。手綱は必ず成功）→ 促す → 鞭。チュートリアル中は落馬なし・ゲートの判定幅 +0.15 秒。結果は練習あつかい（成績・レコードに残らない）で、初回だけ完了ボーナス 50 万円（`S.tutorialDone`）。メニューの「はじめての人へ」カード（`S.tutSkip` で隠す）と「チュートリアル」ボタンから何度でも遊べる。
8. `result` — 着順・賞金（騎手の取り分 = 賞金の 5%）・経験値、騎乗評価表（`evaluateRide`：スタート / 位置取り / 折り合い / 仕掛け / スタミナ配分 / 鞭さばき を ◎○△× で採点、S〜D）、馬からのひとこと（`HORSE_SAYS` / `horseComment`、関西弁の荒ぶった口調）、落馬時の治療費。
9. `音楽` — Web Audio でファンファーレと蹄の音をその場で合成（音源ファイルなし）。スマホは最初のタップまで鳴らせない。
10. `タイトル映像` — Canvas で昼の競馬場と走る馬を描くアニメーション（`drawTitle` / `drawGallop`）。
11. `画面遷移` / `boot` — `show(id)` がセクション（`title` / `home` / `card` / `raceScr` / `result`）を切り替え、`showPanel(name)` がホーム内パネル（`menu` / `name` / `profile` / `races` / `records` / `shop` / `room` / `versus` / `social`）を切り替える。

## 画面の流れ

タイトル（音楽・スタート）→ 初回のみ騎手名入力 → メニュー（初回は「はじめての人へ」からチュートリアル）（レースに出る / アイテムを買う / 対戦 / ひろば / マイルーム / 自分の成績）→ 出馬表で馬を選ぶ → ゲート（金色になった瞬間にタップ）→ レース（抑える Z / 手綱を引く X / 促す C / 鞭 Space）→ 結果（馬のひとこと・報酬・騎乗評価・着順表）

## Supabase のテーブル

- `public.leaderboard` — `look jsonb`（8000 バイトまで）にアバター・部屋の見た目。誰でも読める（RLS の select ポリシーのみ）。直接の insert / update / delete は不可。
- `public.jockey_secrets` — 騎手ごとの合鍵のハッシュ（bcrypt）。外からは読めない。
- `submit_jockey(...)` / `delete_jockey(...)` — `security definer`。合鍵が一致したときだけ書き換える。Supabase の診断で「anon が security definer 関数を実行できる」という警告が出るが、ログインなしで成績を送るための意図した設計。
- `public.race_rooms`（参加コード・レース・seed・馬場）/ `public.room_entries`（メンバー・タイム・落馬・ゴースト）/ `public.challenges`（申し込み）— 誰でも読める。書き込みは関数だけ。`jockey_ok()` は合鍵確認用で外からは呼べない。
- `public.race_records`（レース×騎手の自己ベスト：名前・タイム・馬・馬場）とビュー `race_top`（レースごとの 1 位、`security_invoker`）— 誰でも読める。書き込みは `submit_record`（合鍵確認、速いときだけ上書き）。
- `public.board_posts`（掲示板）と `leaderboard.last_seen`（最後にアクセスした時刻）は誰でも読める。`public.friendships`（`pending` / `accepted` / `declined` / `removed`）/ `public.direct_messages` / `public.gifts` は外から読めない（anon に権限なし）。読むのは合鍵を確かめる `my_inbox` / `get_dms` だけ。`are_friends()` は内部用で外からは呼べない。
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
