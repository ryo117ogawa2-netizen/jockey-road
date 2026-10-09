import json,os,sys,math,datetime,collections
import numpy as np
D=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,D)
from feat import features,race_info
R=json.load(open(D+'/races.json')); H=json.load(open(D+'/horses.json'))
rows=[]
for rid,v in R.items():
    if 'pre' not in v or not v['post']['result']: continue
    ri=race_info(v['pre'],v['date'])
    if ri['surf'] not in('芝','ダ'): continue
    rank={r['uma']:r['rank'] for r in v['post']['result']}
    pay=v['post']['pay']; tan=dict(zip(pay.get('Tansho',{}).get('nums',[]),pay.get('Tansho',{}).get('pay',[])))
    fk=pay.get('Fukusho',{}); fuku=dict(zip(fk.get('nums',[]),fk.get('pay',[])))
    f3=pay.get('Fuku3',{}); wide=pay.get('Wide',{})
    for h in v['pre']['horses']:
        if not h['uma'] or h['uma'] not in rank: continue
        rk=rank[h['uma']]
        if not rk.isdigit(): continue
        f=features(h,ri,H)
        rows.append(dict(rid=rid,date=ri['date'],ri=ri,uma=h['uma'],rank=int(rk),tan=tan.get(h['uma'],0),fuku=fuku.get(h['uma'],0),f=f,
                         f3=(sorted(f3.get('nums',[]),key=int),f3.get('pay',[0])[0] if f3.get('pay') else 0),
                         wide=wide))
print('horses',len(rows),'races',len({r['rid'] for r in rows}))
def stat(sub):
    n=len(sub)
    if n==0: return (0,0,0,0,0)
    w=sum(r['rank']==1 for r in sub); t3=sum(r['rank']<=3 for r in sub)
    return (n,100*w/n,100*t3/n,sum(r['tan'] for r in sub)/n,sum(r['fuku'] for r in sub)/n)
base=stat(rows)
out=[]
out.append(f"全体 {base[0]}頭: 勝率{base[1]:.1f}% 3着内{base[2]:.1f}% 単回{base[3]:.0f}% 複回{base[4]:.0f}%")
keys=[k for k in rows[0]['f'] if not k.startswith('_') and isinstance(rows[0]['f'][k],bool)]
tab=[]
for k in keys:
    sub=[r for r in rows if r['f'][k]]
    a=stat([r for r in sub if r['date']<datetime.date(2026,4,1)]); b=stat([r for r in sub if r['date']>=datetime.date(2026,4,1)]); s=stat(sub)
    tab.append((k,s,a,b))
for k,s,a,b in sorted(tab,key=lambda x:-x[1][2]):
    out.append(f"| {k} | {s[0]} | {s[1]:.1f}% | {s[2]:.1f}% | {s[3]:.0f}% | {s[4]:.0f}% | 前半3着内{a[2]:.0f}%/後半{b[2]:.0f}% |")
# 騎手別
out.append('\n騎手別')
for jk in ['ルメール','川田','武豊','松山','岩田望','津村','丹内','菊沢','戸崎圭','坂井','横山武','西村淳','Ｍデムーロ','鮫島駿','北村友','横山和','池添','浜中','団野','佐々木']:
    sub=[r for r in rows if r['f']['_jockey']==jk]
    s=stat(sub)
    if s[0]: out.append(f"| {jk} | {s[0]} | {s[1]:.1f}% | {s[2]:.1f}% | {s[3]:.0f}% | {s[4]:.0f}% |")
out.append('\n生産者別')
for br in ['ノーザンファーム','社台ファーム','社台コーポレーション白老ファーム','追分ファーム','ダーレー・ジャパン・ファーム','ノースヒルズ','三嶋牧場','岡田スタッド','ビッグレッドファーム','下河辺牧場']:
    s=stat([r for r in rows if r['f']['_br']==br])
    if s[0]: out.append(f"| {br} | {s[0]} | {s[1]:.1f}% | {s[2]:.1f}% | {s[3]:.0f}% | {s[4]:.0f}% |")
# 体重増減×休み明け（ノーザン）
out.append('\nノーザン休み明けの体重増減')
for lo,hi,lab in [(-99,-4,'-4以下'),(-2,2,'±2'),(4,8,'+4〜+8'),(10,99,'+10以上')]:
    s=stat([r for r in rows if r['f']['ノーザン生産'] and r['f']['休み明け'] and r['f']['_wd'] is not None and lo<=r['f']['_wd']<=hi])
    out.append(f"| {lab} | {s[0]} | {s[1]:.1f}% | {s[2]:.1f}% | {s[3]:.0f}% | {s[4]:.0f}% |")
# 戦略
races=collections.defaultdict(list)
for r in rows: races[r['rid']].append(r)
def s_like(f): # 好み
    return (f['jockey_score']+2*f['ノーザン生産']+1*f['社台生産']+2*f['ノーザン休み明け体重増']+2*f['叩き2戦目で絞れた']+1.5*f['ダート外枠']
            +1.5*f['短距離内枠逃げ先行']+2*f['外国産/オルフェ産駒のダート替わり']+1.5*f['前走人気で大敗（不利・出遅れ候補）'])
def s_mine(f):
    return (-5*min(f['_best_diff'],2)+1.5*f['前走3着内']+1.5*f['3歳（秋・古馬混合）']+1*f['開幕週の逃げ先行']+0.8*f['逃げ先行']+0.4*f['jockey_score']+0.8*f['ノーザン生産'])
FK=[k for k in keys]
def vec(f): return np.array([1.0]+[float(f[k]) for k in FK]+[min(f['_best_diff'],2),f['jockey_score']])
calib=[r for r in rows if r['date']<datetime.date(2026,4,1)]
X=np.array([vec(r['f']) for r in calib]); y=np.array([1.0 if r['rank']<=3 else 0 for r in calib])
w=np.zeros(X.shape[1])
for it in range(3000):
    p=1/(1+np.exp(-X@w)); g=X.T@(p-y)/len(y)+0.001*w; w-=0.5*g
coef=sorted(zip(['定数']+FK+['近3走の最小着差','騎手スコア'],w),key=lambda x:-abs(x[1]))
def s_fit(f): return float(vec(f)@w)
def evalS(score,period):
    st=collections.Counter(); n=0
    for rid,hs in races.items():
        if not(period[0]<=hs[0]['date']<period[1]): continue
        hs=sorted(hs,key=lambda r:-score(r['f'])); n+=1
        a,b,c=hs[0],hs[1],hs[2]
        st['win']+=a['rank']==1; st['top3']+=a['rank']<=3; st['tan']+=a['tan']; st['fuku']+=a['fuku']
        mk=sorted([a['uma'],b['uma'],c['uma']],key=int)
        if mk==hs[0]['f3'][0]: st['f3']+=1; st['f3pay']+=hs[0]['f3'][1]
        # ワイド◎-○
        wn=hs[0]['wide'].get('nums',[]); wp=hs[0]['wide'].get('pay',[])
        pairs=[sorted(wn[i:i+2],key=int) for i in range(0,len(wn),2)]
        for pr,pp in zip(pairs,wp):
            if pr==sorted([a['uma'],b['uma']],key=int): st['wide']+=1; st['widepay']+=pp
        st['rand_win']+=1/len(hs); st['rand_t3']+=3/len(hs)
    return n,st
out.append('\n戦略の成績（◎の勝率・3着内率・単回・複回、◎○▲の3連複1点、◎-○ワイド1点）')
for lab,per in [('前半(25/10-26/3)',(datetime.date(2025,1,1),datetime.date(2026,4,1))),('後半(26/4-26/9)',(datetime.date(2026,4,1),datetime.date(2027,1,1)))]:
    for nm,sc in [('好み',s_like),('相棒',s_mine),('学習(前半で学習)',s_fit)]:
        n,st=evalS(sc,per)
        out.append(f"| {lab} | {nm} | {n}R | ◎勝率{100*st['win']/n:.1f}% | ◎3着内{100*st['top3']/n:.1f}% | 単回{st['tan']/n:.0f}% | 複回{st['fuku']/n:.0f}% | 3連複的中{100*st['f3']/n:.1f}% 回収{st['f3pay']/n:.0f}% | ワイド的中{100*st['wide']/n:.1f}% 回収{st['widepay']/n:.0f}% |")
    out.append(f"| {lab} | ランダム | | 勝率{100*st['rand_win']/n:.1f}% | 3着内{100*st['rand_t3']/n:.1f}% |")
out.append('\n学習した重み（大きいほど3着内に効く）')
for k,v in coef: out.append(f"  {k}: {v:+.2f}")
json.dump(dict(FK=FK,w=list(w)),open(D+'/weights.json','w'),ensure_ascii=False)
open(D+'/report.txt','w').write('\n'.join(out)); print('\n'.join(out))
