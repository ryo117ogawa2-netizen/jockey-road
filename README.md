# ジョッキーロード

若手騎手として地方競馬から始め、凱旋門賞制覇を目指す競馬ゲーム。

遊ぶ：https://jockey-road.vercel.app

- フロント：`index.html`（1ファイル。ビルド不要）
- API：`api/config.js`（Vercel Serverless Function。Supabase の接続先を返す）
- DB：`supabase/migrations/`（Supabase のランキング用テーブル）
- バランス確認：`node tools/sim.mjs derby 100`

GitHub の `main` に push すると Vercel が自動で公開し直す。

開発の詳しいメモは [CLAUDE.md](CLAUDE.md) を参照。
