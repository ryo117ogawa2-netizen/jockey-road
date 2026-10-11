import json,sys,re,collections as C
d=json.load(open(sys.argv[1])); h=json.load(open(sys.argv[2])); h.update(json.load(open(sys.argv[3])))
def rows(surf):
    for r in d:
        if '新馬' in r['name'] and r['surf']==surf:
            n=len(r['rows'])
            for x in r['rows']:
                try: rk=int(x['rank'])
                except: continue
                try: nk=int(x['ninki']); od=float(x['odds'])
                except: continue
                yield r,x,rk,nk,od
def norm_j(j): return 'ルメール' if j.startswith('ルメー') else j
def br(x):
    b=h.get(x['hid'],{}).get('breeder','')
    return b
for surf in ['ダ','芝']:
    R=list(rows(surf))
    # expected top3 by ninki
    e=C.defaultdict(lambda:[0,0])
    for r,x,rk,nk,od in R: e[min(nk,12)][0]+=1; e[min(nk,12)][1]+=rk<=3
    exp={k:v[1]/v[0] for k,v in e.items()}
    print(f'=== {surf} 新馬 {len({r["rid"] for r,*_ in R})}レース {len(R)}頭 3着内平均{sum(rk<=3 for _,_,rk,_,_ in R)/len(R):.1%}')
    if surf=='芝': 
        TURF={}
    for name,key,mn in [('騎手',lambda x:norm_j(x['jockey']),8),('厩舎',lambda x:re.sub(r'^\[.\]\s*','',x['trainer']),5),('生産',br,6)]:
        g=C.defaultdict(lambda:dict(n=0,w=0,t3=0,ex=0.,ret=0.,pop=0))
        for r,x,rk,nk,od in R:
            k=key(x)
            if not k: continue
            s=g[k]; s['n']+=1; s['w']+=rk==1; s['t3']+=rk<=3; s['ex']+=exp[min(nk,12)]; s['ret']+=od*100 if rk==1 else 0; s['pop']+=nk<=3
        L=[(k,s) for k,s in g.items() if s['n']>=mn]
        L.sort(key=lambda kv:-(kv[1]['t3']-kv[1]['ex']))
        print(f'--- {name}（{mn}走以上、人気から見た期待との差で並べた上位/下位）')
        for k,s in L[:12]+[('…',None)]+L[-5:]:
            if s is None: print('  …'); continue
            print(f"  {k}: {s['n']}走 勝{s['w']} 3着内{s['t3']/s['n']:.0%}（人気からの期待{s['ex']/s['n']:.0%}） 単回{s['ret']/s['n']:.0f}% 上位人気率{s['pop']/s['n']:.0%}")
        if surf=='ダ': json.dump({k:s for k,s in g.items()},open(f'{sys.argv[4]}/{name}.json','w'),ensure_ascii=False)
