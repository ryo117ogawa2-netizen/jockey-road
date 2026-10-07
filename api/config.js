// Vercel Serverless Function: GET /api/config
// Supabase の接続先をブラウザに渡す。
// Vercel の環境変数（SUPABASE_URL / SUPABASE_ANON_KEY）があればそれを使い、
// なければ下の既定値を使う。publishable key はブラウザに公開する前提のキーで、
// 書き込みは DB 側の関数と RLS で制限している。
const DEFAULT_URL = 'https://tujcjbqhbwqxhximmdsv.supabase.co';
const DEFAULT_KEY = 'sb_publishable_mjBD1Uc7JaLSj45-1ww--w_BxdQ5M7R';

export default function handler(req, res) {
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
  res.status(200).json({
    url: process.env.SUPABASE_URL || DEFAULT_URL,
    anonKey: process.env.SUPABASE_ANON_KEY || DEFAULT_KEY,
  });
}
