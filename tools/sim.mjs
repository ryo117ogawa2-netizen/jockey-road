// レースバランスを確かめるシミュレーター（ブラウザ不要）
// 使い方: node tools/sim.mjs [レースID] [回数]
//   例: node tools/sim.mjs derby 100
// index.html の //SIM-START 〜 /* ------------ items ------------ */ を読み込み、
// いくつかの乗り方（何もしない／直線で鞭／前半抑えて直線で鞭）で勝率を出す。
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, '..', 'index.html'), 'utf8');
const code = src.slice(src.indexOf('//SIM-START'), src.indexOf('/* ------------ items ------------ */'));
const raceId = process.argv[2] || 'derby';
const N = Number(process.argv[3] || 60);

const run = new Function('raceId', 'N', code + `
  const race = raceById(raceId);
  if (!race) throw new Error('レースIDが見つかりません: ' + raceId);
  const strategies = {
    '何もしない': () => {},
    '直線で鞭': (st, p, rem) => { if (rem < race.straight + 150 && (st.t % 1.3) < 1/30) playerAct(st, 'whip'); },
    '前半抑え→直線で鞭': (st, p, rem, f) => {
      if (!f.held && p.d < race.dist * 0.5) { playerAct(st, 'hold'); f.held = true; }
      if (f.held && p.d >= race.dist * 0.5) { playerAct(st, 'hold'); f.held = false; }
      if (rem < race.straight + 150 && (st.t % 1.3) < 1/30) playerAct(st, 'whip');
    }
  };
  const out = [];
  for (const [name, fn] of Object.entries(strategies)) {
    let wins = 0, sum = 0;
    for (let i = 0; i < N; i++) {
      usedNames.clear();
      const st = createRaceState(race, genHorse(race.R, false), race.lv, '良');
      const p = st.player, f = {};
      while (!st.runners.every(r => r.fin)) {
        if (p.kakari > 0 && Math.random() < 0.1) playerAct(st, 'rein');
        fn(st, p, race.dist - p.d, f);
        step(st, 1/30);
      }
      const order = [...st.runners].sort((a, b) => a.time - b.time);
      const place = order.indexOf(p) + 1;
      if (place === 1) wins++; sum += place;
    }
    out.push({ 乗り方: name, 勝率: Math.round(wins / N * 100) + '%', 平均着順: (sum / N).toFixed(1) });
  }
  return { race: race.name, out };
`);
const { race, out } = run(raceId, N);
console.log(`${race}（${N}回・相手と同じ能力の馬）`);
console.table(out);
