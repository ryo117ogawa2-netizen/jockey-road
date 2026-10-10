# 過去1年の全レース（1R〜12R）の結果ページから、調教師・人気・オッズ・着順を集める
import re,html,json,os,sys,glob
sys.path.insert(0,'.'); import scrape
from concurrent.futures import ThreadPoolExecutor
T=scrape.T
ids=[]
for f in sorted(glob.glob('cache/list20*')):
    d=f[-8:]; date=f"{d[:4]}-{d[4:6]}-{d[6:]}"
    if not('2025-10-04'<=date<='2026-09-28'): continue
    for r in sorted(set(re.findall(r'race_id=(\d{12})',open(f,encoding='utf-8').read()))): ids.append((date,r))
print(len(ids),flush=True)
def job(x):
    date,rid=x
    s=scrape.get(f'https://db.netkeiba.com/race/{rid}/',f'db{rid}')
    m=re.search(r'diary_snap_cut.*?<span>(.*?)</span>',s,re.S); head=T(m.group(1)) if m else ''
    sd=re.search(r'(芝|ダ|障)\D{0,3}?(\d{3,4})m',head)
    tt=re.search(r'<title>(.*?)</title>',s,re.S); title=T(tt.group(1)) if tt else ''
    h1=re.search(r'<dl class="racedata.*?<h1>(.*?)</h1>',s,re.S); name=T(h1.group(1)) if h1 else ''
    tb=re.search(r'race_table_01.*?</table>',s,re.S); rows=[]
    if tb:
        for tr in re.findall(r'<tr.*?</tr>',tb.group(0),re.S)[1:]:
            tds=[T(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
            if len(tds)<23: continue
            tid=re.search(r'/trainer/(?:result/recent/)?(\d{5})',tr); hid=re.search(r'/horse/(\w+)',tr)
            rows.append(dict(rank=tds[0],uma=tds[2],hid=hid.group(1) if hid else '',jockey=tds[6],odds=tds[16],ninki=tds[17],trainer=tds[22],tid=tid.group(1) if tid else ''))
    sm=re.search(r'smalltxt">(.*?)</p>',s,re.S); small=T(sm.group(1)) if sm else ''
    return dict(date=date,rid=rid,name=name,surf=sd.group(1) if sd else '',dist=int(sd.group(2)) if sd else 0,small=small,rows=rows)
out=[]
with ThreadPoolExecutor(3) as ex:
    for i,r in enumerate(ex.map(job,ids)):
        out.append(r)
        if i%300==0: print(i,flush=True)
json.dump(out,open('allraces.json','w'),ensure_ascii=False); print('done',flush=True)
