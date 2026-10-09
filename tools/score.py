# 使い方: python3 tools/score.py 202605040311 2026-10-10  → 学習した重みで出走馬の3着内確率を出す
import json,re,sys,os,numpy as np
sys.path.insert(0,os.path.dirname(__file__)); import scrape,feat
W=json.load(open(os.path.dirname(__file__)+'/weights.json')); FK=W['FK']; w=np.array(W['w'])
rid,date=sys.argv[1],sys.argv[2]; pre=scrape.pre(rid); ri=feat.race_info(pre,date); H={}
for h in pre['horses']:
    if not h['hid']: continue
    s=scrape.get(f'https://db.netkeiba.com/horse/{h["hid"]}/',f'h{h["hid"]}')
    m=re.search(r'生産者</th>\s*<td[^>]*>(.*?)</td>',s,re.S); b=scrape.T(m.group(1)) if m else ''
    H[h['hid']]=dict(breeder=b,gai=bool(re.search('[A-Za-z]',b)))
rows=[]
for h in pre['horses']:
    if not h['hid']: continue
    f=feat.features(h,ri,H); v=np.array([1.0]+[float(f[k]) for k in FK]+[min(f['_best_diff'],2),f['jockey_score']])
    rows.append((1/(1+np.exp(-v@w)),h['uma'],h['info'].split()[1],f['_jockey'],f['_br'],[k for k in FK if f[k]]))
print(pre['name'])
for r in sorted(rows,reverse=True): print(f"{r[0]*100:4.0f}% {r[1]:>2} {r[2]} {r[3]} {r[4]} {','.join(r[5])}")
