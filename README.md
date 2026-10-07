# ジョッキーロード

若手騎手として地方競馬から始め、凱旋門賞制覇を目指す競馬ゲーム。

- フロント：`index.html`（1ファイル）
- API：`api/config.js`（Vercel Serverless Function。Supabase の接続先を返す）
- DB：`supabase/migrations/`（Supabase のランキング用テーブル）

## Vercel の環境変数

| 名前 | 値 |
|---|---|
| `SUPABASE_URL` | Supabase プロジェクトの URL |
| `SUPABASE_ANON_KEY` | Supabase の publishable key（公開してよいキー） |

GitHub の `main` に push すると Vercel が自動で公開し直す。
