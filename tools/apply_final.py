# 使い方: python3 tools/apply_final.py <final.json> <days ドキュメントJSON> <predictions.md>
# final.py の結果をアプリ用の days ドキュメントと予想メモに反映し、前の印からの変更点を表示する
import json,sys
fin=json.load(open(sys.argv[1])); dp=sys.argv[2]; d=json.load(open(dp)); md=sys.argv[3]
lines=[]
for f in fin:
    key=f"{f['venue']}{f['R']}R "
    for r in d['races']:
        if not r['course'].startswith(key): continue
        old=[(m['mark'],m['uma']) for m in r['marks'][:3]]; new=[(m['mark'],m['uma']) for m in f['marks'][:3]]
        hand=bool(r.get('partner'))   # 重賞・メインの手作り予想は印を残し、体重だけ足す
        if not hand: r['marks']=f['marks']
        r['status']=f"最終予想（馬体重反映）{f['post']}"
        w=[l for l in f['weight'].split('\n') if '⚠' in l or '維持' in l]
        r['weight']=' ／ '.join(w) if w else '大きな増減なし'
        marked={m['uma'] for m in (r['marks'][:3])}
        warn=[l for l in f['weight'].split('\n') if '⚠' in l and l.split(' ')[0].rstrip('0123456789') is not None and any(l.startswith(u) and not l[len(u)].isdigit() for u in marked)]
        chg='' if hand or old==new else f" 印変更 {old}→{new}"
        print(f"{key}{f['name']} {f['post']}{' 【手作り予想】' if hand else ''}{' 【勝負レース】' if r.get('shobu') else ''}{chg}")
        print('   '+' '.join(f"{m['mark']}{m['uma']}{m['name']}({m.get('pct','')}%)" for m in r['marks']))
        for l in warn: print('   印の馬に注意: '+l)
        lines.append(f"- {key}{f['name']} {f['post']}："+' '.join(f"{m['mark']}{m['uma']}{m['name']}" for m in r['marks'])+(' ／ 注意: '+'；'.join(warn) if warn else ''))
json.dump(d,open(dp,'w'),ensure_ascii=False)
if lines: open(md,'a').write('\n'.join(lines)+'\n')
