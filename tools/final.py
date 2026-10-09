# 使い方: python3 tools/final.py 2026-10-10 <状態JSON> [出力JSON]
# 馬体重が発表されたレースだけ、体重の増減を加味した最終予想を出す。状態JSONに済んだレースを記録して二重に出さない。
import json,re,sys,os,datetime,numpy as np
sys.path.insert(0,os.path.dirname(__file__)); import scrape,feat
W=json.load(open(os.path.dirname(__file__)+'/weights.json')); FK=W['FK']; w=np.array(W['w'])
date=sys.argv[1]; stp=sys.argv[2]; out=sys.argv[3] if len(sys.argv)>3 else None
state=json.load(open(stp)) if os.path.exists(stp) else {}
C=scrape.C
for f in os.listdir(C):
    if f.startswith(('past','shu')): os.remove(os.path.join(C,f))
lst=scrape.get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}','list'+date)
rids=sorted(set(re.findall(r'race_id=(\d{12})',lst)))
VEN={'01':'札幌','02':'函館','03':'福島','04':'新潟','05':'東京','06':'中山','07':'中京','08':'京都','09':'阪神','10':'小倉'}
EAST={'東京','中山','新潟','福島'}; WEST={'京都','阪神','中京','小倉'}
now=datetime.datetime.utcnow()+datetime.timedelta(hours=9)
H={}; res=[]
for rid in rids:
    if rid in state: continue
    pre=scrape.pre(rid); ri=feat.race_info(pre,date)
    if ri['surf'] not in('芝','ダ'): continue
    tm=re.search(r'(\d{1,2}):(\d\d)発走',pre['d1'])
    post=datetime.datetime.combine(ri['date'],datetime.time(int(tm[1]),int(tm[2]))) if tm else None
    if post and post<now: state[rid]='過ぎた'; continue
    hs=[h for h in pre['horses'] if h['hid'] and h['uma']]
    if not hs or not all(re.search(r'\d{3}kg \([+\-]?\d+\)',h['info']) for h in hs): continue   # 馬体重がまだ
    rows=[]
    for h in hs:
        if h['hid'] not in H:
            t=scrape.get(f'https://db.netkeiba.com/horse/{h["hid"]}/',f'h{h["hid"]}')
            m=re.search(r'生産者</th>\s*<td[^>]*>(.*?)</td>',t,re.S); b=scrape.T(m.group(1)) if m else ''
            H[h['hid']]=dict(breeder=b,gai=bool(re.search('[A-Za-z]',b)))
        f=feat.features(h,ri,H)
        v=np.array([1.0]+[float(f[k]) for k in FK]+[min(f['_best_diff'],2),f['jockey_score']])
        p=float(1/(1+np.exp(-v@w)))
        wm=re.search(r'(\d{3})kg \(([+\-]?\d+)\)',h['info']); kg=int(wm[1]); wd=int(wm[2])
        ps=[x for x in (feat.parse_past(q) for q in h['past']) if x]
        gap=(ri['date']-ps[0]['date']).days if ps else None
        base='美浦' if '美浦' in h['info'] else '栗東' if '栗東' in h['info'] else ''
        trip=(base=='美浦' and ri['venue'] in WEST) or (base=='栗東' and ri['venue'] in EAST) or ri['venue'] in('札幌','函館')
        t2=len(ps)>=2 and gap is not None and gap<70 and (ps[0]['date']-ps[1]['date']).days>=70 and (ps[0]['wd'] or 0)>=4
        good=[q['w'] for q in ps if q['rank'] and q['rank']<=3 and q['w']]
        k=1.0; note=[]
        # 過去1年の集計（全体の3着内20.9%）にもとづく補正
        if wd<=-10:
            if gap is not None and gap>=70: k*=0.5; note.append(f'⚠休み明けで{wd}kg（同条件の3着内9.9%）')
            elif trip: k*=0.65; note.append(f'⚠遠征で{wd}kg。輸送で減った可能性（3着内13.1%）')
            elif gap is not None and gap<=21: k*=0.75; note.append(f'⚠間隔が詰まって{wd}kg。疲れに注意')
            else: k*=0.7; note.append(f'⚠{wd}kgの大幅減（3着内14.2%）')
        elif wd>=10:
            if gap is not None and gap>=70: note.append(f'休み明けで+{wd}kg。成長分なら問題なし（3着内19.7%・単回103%）')
            else: note.append(f'+{wd}kgの大幅増。成長分か太めかパドックで確認（増えても成績は平均並み）')
        if t2:
            if -2<=wd<=2: k*=1.25; note.append(f'叩き2戦目で体重維持（{wd:+d}）＝いちばん良いパターン（3着内27.4%）')
            elif wd<=-4: note.append(f'叩き2戦目で{wd}kg絞れた（3着内19.3%、平均並み）')
            else: k*=0.7; note.append(f'⚠叩き2戦目でさらに+{wd}kg（3着内13.8%）')
        if good and abs(kg-good[0])<=2 and not note: k*=1.08; note.append(f'好走したときと同じ体重（{kg}kg）')
        rows.append(dict(p=min(0.95,p*k),p0=p,uma=h['uma'],waku=int(h['waku'] or 0),name=h.get('name') or h['info'].split()[1],jockey=f['_jockey'],kg=kg,wd=wd,note=' / '.join(note)))
    rows.sort(key=lambda r:-r['p'])
    marks=[dict(mark=mk,uma=r['uma'],waku=r['waku'],name=r['name'],jockey=r['jockey'],pct=round(r['p']*100),why=f"{r['kg']}kg({r['wd']:+d}) "+r['note']) for mk,r in zip('◎○▲',rows)]
    marks+=[dict(mark='紐',uma=r['uma'],waku=r['waku'],name=r['name'],jockey=r['jockey'],pct=round(r['p']*100),why=f"{r['kg']}kg({r['wd']:+d}) "+r['note']) for r in rows[3:5]]
    warn=[f"{r['uma']}{r['name']} {r['kg']}kg({r['wd']:+d}) {r['note']}" for r in rows if r['note']]
    res.append(dict(rid=rid,post=tm[0] if tm else '',name=pre['name'].strip(),venue=VEN.get(rid[4:6],''),R=int(rid[-2:]),marks=marks,weight='\n'.join(warn) or '大きな増減なし'))
    state[rid]='最終予想済み'
json.dump(state,open(stp,'w'),ensure_ascii=False)
for r in res:
    print(f"## {r['venue']}{r['R']}R {r['name']} {r['post']}\n  "+' '.join(f"{m['mark']}{m['uma']}{m['name']}({m['pct']}%)" for m in r['marks'])+"\n  "+r['weight'].replace('\n','\n  '))
if out: json.dump(res,open(out,'w'),ensure_ascii=False)
