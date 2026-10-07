// Vercel Serverless Function: GET /api/config
// Supabase の接続先をブラウザに渡す。値は Vercel の環境変数で設定する。
// anon key はブラウザに公開される前提のキー（書き込みは DB 側の関数と RLS で制限）。
export default function handler(req, res) {
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
  res.status(200).json({
    url: process.env.SUPABASE_URL || null,
    anonKey: process.env.SUPABASE_ANON_KEY || null,
  });
}
