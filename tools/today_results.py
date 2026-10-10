# 使い方: python3 tools/today_results.py <日付> <days ドキュメントJSON> [出力JSON]
# 終わったレースの結果を取り、アプリに出している印（最終予想）と照らし合わせる
import re,html,json,sys,os,urllib.request,time
date=sys.argv[1]; d=json.load(open(sys.argv[2])); out=sys.argv[3] if len(sys.argv)>3 else None
T=lambda x:' '.join(html.unescape(re.sub(r'<[^>]+>',' ',x)).split())
def get(u):
    import time
    for i in range(5):
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read(); return b.decode('utf-8','ignore')
        except Exception:
            time.sleep(3*(i+1))
    raise RuntimeError(u)
VEN={'05':'東京','08':'京都','06':'中山','09':'阪神','01':'札幌','02':'函館','03':'福島','04':'新潟','07':'中京','10':'小倉'}
lst=get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}')
res=[]; tot=dict(n=0,h1=0,h3=0,tan=0,fuku=0,uren=0,wide=0,f3=0,shobu=None)
for rid in sorted(set(re.findall(r'race_id=(\d{12})',lst))):
    key=f"{VEN.get(rid[4:6],'')}{int(rid[-2:])}R "
    race=next((r for r in d['races'] if r['course'].startswith(key)),None)
    if not race: continue
    try: s=get(f'https://race.netkeiba.com/race/result.html?race_id={rid}')
    except Exception as e: continue
    tb=re.search(r'id="All_Result_Table".*?</table>',s,re.S)
    if not tb: continue
    rows=[]
    for tr in re.findall(r'<tr[^>]*>.*?</tr>',tb.group(0),re.S)[1:]:
        c=[T(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
        if len(c)>10: rows.append(dict(rank=c[0],waku=c[1],uma=c[2],name=c[3],jockey=c[6],nin=c[9],odds=c[10],agari=c[11],pas=c[12] if len(c)>12 else '',stable=c[13] if len(c)>13 else '',wt=c[14] if len(c)>14 else ''))
    if not rows or not rows[0]['rank'].isdigit(): continue
    pay={}
    m=re.search(r'Payout_Detail_Table.*?(?=<div class="Result_Note|$)',s,re.S)
    for k,body in re.findall(r'<tr class="(\w+)">(.*?)</tr>',m.group(0) if m else '',re.S):
        cells=dict(re.findall(r'<td class="(\w+)">(.*?)</td>',body,re.S))
        nums=re.findall(r'<span>(\d+)</span>',cells.get('Result','')) or re.findall(r'\d+',T(cells.get('Result','')))
        pay[k]=dict(nums=nums,pay=[int(x.replace(',','')) for x in re.findall(r'([\d,]+)円',T(cells.get('Payout','')))])
    rk={r['uma']:r for r in rows}
    marks=race['marks']; top=[m['uma'] for m in marks[:3] if m.get('uma')]
    fin={m['uma']:(rk.get(m['uma'],{}).get('rank','?')) for m in marks if m.get('uma')}
    for m in marks:
        if m.get('uma') in fin: m['finish']=int(fin[m['uma']]) if str(fin[m['uma']]).isdigit() else None
    tan=dict(zip(pay.get('Tansho',{}).get('nums',[]),pay.get('Tansho',{}).get('pay',[])))
    fk=dict(zip(pay.get('Fukusho',{}).get('nums',[]),pay.get('Fukusho',{}).get('pay',[])))
    pairs=[sorted([a,b],key=int) for i,a in enumerate(top) for b in top[i+1:]]
    un=sorted(pay.get('Umaren',{}).get('nums',[])[:2],key=int); up=(pay.get('Umaren',{}).get('pay') or [0])[0]
    wn=pay.get('Wide',{}).get('nums',[]); wps=pay.get('Wide',{}).get('pay',[]); wpairs=[sorted(wn[i:i+2],key=int) for i in range(0,len(wn),2)]
    f3n=sorted(pay.get('Fuku3',{}).get('nums',[]),key=int); f3p=(pay.get('Fuku3',{}).get('pay') or [0])[0]
    a=top[0] if top else None
    r=dict(rid=rid,course=race['course'],rows=rows,key=key.strip(),name=race['name'],shobu=bool(race.get('shobu')),
        top3=[f"{x['rank']}着 {x['uma']}{x['name']}（{x['nin']}人気）" for x in rows[:3]],
        marks=[f"{m['mark']}{m['uma']}{m['name']}→{fin.get(m['uma'],'?')}着" for m in marks if m.get('uma')],
        tan=tan.get(a,0),fuku=fk.get(a,0),uren=sum(up for p in pairs if p==un),
        wide=sum(pp for p in pairs for q,pp in zip(wpairs,wps) if p==q),f3=f3p if sorted(top,key=int)==f3n else 0,
        top_nin=rk.get(a,{}).get('nin','?'))
    res.append(r); tot['n']+=1; tot['h1']+=r['tan']>0; tot['h3']+=r['fuku']>0
    for k in ('tan','fuku','uren','wide','f3'): tot[k]+=r[k]
    hit=[f"{n}{r[k]:,}円" for k,n in (('tan','単勝'),('fuku','複勝'),('uren','馬連'),('wide','ワイド'),('f3','3連複')) if r[k]]
    race['result']=dict(top3=' ／ '.join(r['top3']),hit=('的中：'+'・'.join(hit)) if hit else '印からの的中なし')
    print(('【勝負】' if r['shobu'] else '')+f"{r['key']} {r['name']}：{' '.join(r['marks'][:5])} ｜ 結果 {' / '.join(r['top3'])} ｜ {race['result']['hit']}")
n=tot['n']
if n:
    print(f"\n{n}R：◎勝率{tot['h1']}/{n}・◎3着内{tot['h3']}/{n}｜100円ずつ買った場合の回収率 ◎単勝{tot['tan']/n:.0f}% ◎複勝{tot['fuku']/n:.0f}% 馬連BOX{tot['uren']/(3*n):.0f}% ワイドBOX{tot['wide']/(3*n):.0f}% 3連複1点{tot['f3']/n:.0f}%")
json.dump(d,open(sys.argv[2],'w'),ensure_ascii=False)
if out: json.dump(dict(races=res,total=tot),open(out,'w'),ensure_ascii=False)
