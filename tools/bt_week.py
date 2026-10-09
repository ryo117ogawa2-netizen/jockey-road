# 先週（10/3・10/4）の全レースを、今の方法で機械的に採点 → 上位3頭で馬連BOX・ワイドBOX（各100円×3点）
import json,re,sys,os,datetime,numpy as np
sys.path.insert(0,sys.argv[1]); import scrape,feat
W=json.load(open(sys.argv[1]+'/weights.json')); FK=W['FK']; w=np.array(W['w'])
EAST={'東京','中山','新潟','福島'}; WEST={'京都','阪神','中京','小倉'}
def weight_k(h,ri):
    wm=re.search(r'(\d{3})kg \(([+\-]?\d+)\)',h['info'])
    if not wm: return 1.0
    kg,wd=int(wm[1]),int(wm[2]); ps=[x for x in (feat.parse_past(q) for q in h['past']) if x]
    gap=(ri['date']-ps[0]['date']).days if ps else None
    base='美浦' if '美浦' in h['info'] else '栗東' if '栗東' in h['info'] else ''
    trip=(base=='美浦' and ri['venue'] in WEST) or (base=='栗東' and ri['venue'] in EAST) or ri['venue'] in('札幌','函館')
    t2=len(ps)>=2 and gap is not None and gap<70 and (ps[0]['date']-ps[1]['date']).days>=70 and (ps[0]['wd'] or 0)>=4
    good=[q['w'] for q in ps if q['rank'] and q['rank']<=3 and q['w']]; k=1.0; noted=False
    if wd<=-10:
        noted=True
        k*=0.5 if gap is not None and gap>=70 else 0.65 if trip else 0.75 if gap is not None and gap<=21 else 0.7
    elif wd>=10: noted=True
    if t2:
        noted=True
        if -2<=wd<=2: k*=1.25
        elif wd>=4: k*=0.7
    if good and abs(kg-good[0])<=2 and not noted: k*=1.08
    return k
tot={'前夜':dict(n=0,uh=0,up=0,wh=0,wp=0,bet=0),'最終':dict(n=0,uh=0,up=0,wh=0,wp=0,bet=0)}
det=[]
for date in ['2026-10-03','2026-10-04']:
    lst=scrape.get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}','list'+date)
    for rid in sorted(set(re.findall(r'race_id=(\d{12})',lst))):
        pre=scrape.pre(rid); ri=feat.race_info(pre,date)
        if ri['surf'] not in('芝','ダ'): continue
        OI=scrape.oikiri(rid,fresh=False); H={}
        rows=[]
        for h in pre['horses']:
            if not h['hid'] or not h['uma']: continue
            t=scrape.get(f'https://db.netkeiba.com/horse/{h["hid"]}/',f'h{h["hid"]}')
            m=re.search(r'生産者</th>\s*<td[^>]*>(.*?)</td>',t,re.S); b=scrape.T(m.group(1)) if m else ''
            H[h['hid']]=dict(breeder=b,gai=bool(re.search('[A-Za-z]',b)))
            f=feat.features(h,ri,H); gr=OI.get(h['uma'],{}).get('grade')
            v=np.array([1.0]+[float(f[k]) for k in FK]+[min(f['_best_diff'],2),f['jockey_score'],gr=='A',gr=='C',gr=='D'],float)
            p=float(1/(1+np.exp(-v@w)))
            rows.append((p,p*weight_k(h,ri),h['uma'],h.get('name','')))
        post=scrape.post(rid); pay=post['pay']
        if not pay.get('Umaren'): continue
        um=pay['Umaren']; un=sorted(um['nums'][:2],key=int); upay=um['pay'][0]
        wn=pay['Wide']['nums']; wps=pay['Wide']['pay']; wpairs=[sorted(wn[i:i+2],key=int) for i in range(0,len(wn),2)]
        for mode,idx in [('前夜',0),('最終',1)]:
            top=[r[2] for r in sorted(rows,key=lambda r:-r[idx])[:3]]
            pairs=[sorted([a,b],key=int) for i,a in enumerate(top) for b in top[i+1:]]
            T=tot[mode]; T['n']+=1; T['bet']+=300
            u=sum(upay for pr in pairs if pr==un); wsum=sum(pp for pr in pairs for wp_,pp in zip(wpairs,wps) if pr==wp_)
            T['up']+=u; T['uh']+=u>0; T['wp']+=wsum; T['wh']+=wsum>0
            if mode=='最終': det.append(f"{date[5:]} {scrape.T(pre['name'])[:14]:14} {'-'.join(top):9} 馬連{u:>6} ワイド{wsum:>6}")
for mode,T in tot.items():
    print(f"【{mode}】{T['n']}R 購入{T['bet']*2:,}円（馬連{T['bet']:,}・ワイド{T['bet']:,}）")
    print(f"  馬連: 的中{T['uh']}R 払戻{T['up']:,}円 回収率{100*T['up']/T['bet']:.0f}%")
    print(f"  ワイド: 的中{T['wh']}R 払戻{T['wp']:,}円 回収率{100*T['wp']/T['bet']:.0f}%")
    print(f"  合計 回収率{100*(T['up']+T['wp'])/(2*T['bet']):.0f}%")
open(os.path.dirname(os.path.abspath(__file__))+'/bt_week_detail.txt','w').write('\n'.join(det))
