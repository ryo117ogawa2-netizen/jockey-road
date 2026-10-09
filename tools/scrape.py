# 過去1年の10〜12Rを収集（出走前情報と結果は別ファイルに分けて保存）
import re,html,json,os,time,urllib.request,datetime,sys
from concurrent.futures import ThreadPoolExecutor
D=os.path.dirname(os.path.abspath(__file__)); C=os.environ.get('KEIBA_CACHE','/tmp/keiba-cache'); os.makedirs(C,exist_ok=True)
def get(url,key,enc=None):
    p=f'{C}/{key}'
    if os.path.exists(p): return open(p,encoding='utf-8').read()
    for i in range(4):
        try:
            b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read(); break
        except Exception as e: time.sleep(2*(i+1)); b=None
    if b is None: return ''
    s=None
    for e in ([enc] if enc else [])+['utf-8','euc-jp']:
        try: s=b.decode(e); break
        except: pass
    if s is None: s=b.decode('utf-8','ignore')
    open(p,'w',encoding='utf-8').write(s); time.sleep(0.25); return s
T=lambda x:' '.join(html.unescape(re.sub(r'<[^>]+>',' ',x)).split())
def race_ids():
    ids=[]; d=datetime.date(2025,10,4)
    while d<=datetime.date(2026,9,28):
        s=get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={d:%Y%m%d}',f'list{d:%Y%m%d}')
        for r in sorted(set(re.findall(r'race_id=(\d{12})',s))):
            if int(r[-2:])>=10: ids.append((str(d),r))
        d+=datetime.timedelta(1)
    return ids
def pre(rid):
    s=get(f'https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}',f'past{rid}')
    s2=get(f'https://race.netkeiba.com/race/shutuba.html?race_id={rid}',f'shu{rid}')
    m=re.search(r'<title>(.*?)</title>',s2,re.S); name=T(m.group(1)).split('出馬表')[0] if m else ''
    d1=T(re.search(r'RaceData01.*?</div>',s2,re.S).group(0)) if 'RaceData01' in s2 else ''
    d2=T(re.search(r'RaceData02.*?</div>',s2,re.S).group(0)) if 'RaceData02' in s2 else ''
    horses=[]
    for tr in re.findall(r'<tr class="HorseList.*?</tr>',s,re.S):
        tds=dict()
        for c,v in re.findall(r'<td class="([^"]*)"[^>]*>(.*?)</td>',tr,re.S):
            tds.setdefault(c.split()[0],[]).append(v)
        hid=re.search(r'db.netkeiba.com/horse/(\w+)',tr)
        info=tds.get('Horse_Info',[''])[0]
        h=dict(hid=hid.group(1) if hid else '',waku=T(next((v[0] for k,v in tds.items() if k.startswith('Waku') and k!='Waku'),'')),
               uma=T(tds.get('Waku',[''])[0]),
               info=T(info),jockey=T(tds.get('Jockey',[''])[0]),rest=T(tds.get('Rest',[''])[0]),
               past=[T(p) for k in tds if k.startswith('Past') for p in tds[k]][:5])
        horses.append(h)
    return dict(name=name,d1=d1,d2=d2,horses=horses)
def post(rid):
    s=get(f'https://db.netkeiba.com/race/{rid}/',f'db{rid}')
    tb=re.search(r'race_table_01.*?</table>',s,re.S); res=[]
    if tb:
        for tr in re.findall(r'<tr.*?</tr>',tb.group(0),re.S)[1:]:
            tds=[T(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
            hid=re.search(r'/horse/(\w+)',tr)
            if len(tds)>10: res.append(dict(rank=tds[0],uma=tds[2],name=tds[3],hid=hid.group(1) if hid else '',pas=tds[10]))
    s=get(f'https://race.netkeiba.com/race/result.html?race_id={rid}',f'res{rid}')
    m=re.search(r'Payout_Detail_Table.*?</table>\s*</div>\s*</div>',s,re.S) or re.search(r'Payout_Detail_Table.*?(?=<div class="Result_Note|$)',s,re.S)
    pay={}
    for tr in re.findall(r'<tr class="(\w+)">(.*?)</tr>',m.group(0) if m else '',re.S):
        k=tr[0]; cells=re.findall(r'<td class="(\w+)">(.*?)</td>',tr[1],re.S)
        d={c:v for c,v in cells}
        nums=[x for x in re.findall(r'<span>(\d+)</span>',d.get('Result',''))] or re.findall(r'\d+',T(d.get('Result','')))
        pays=[int(x.replace(',','')) for x in re.findall(r'([\d,]+)円',T(d.get('Payout','')))]
        pay[k]=dict(nums=nums,pay=pays,ninki=re.findall(r'\d+',T(d.get('Ninki',''))))
    return dict(result=res,pay=pay)
if __name__=='__main__':
    ids=race_ids(); print('races',len(ids),flush=True)
    out={}
    def job(x):
        d,r=x
        try: return r,dict(date=d,pre=pre(r),post=post(r))
        except Exception as e: return r,dict(date=d,err=str(e))
    with ThreadPoolExecutor(4) as ex:
        for i,(r,v) in enumerate(ex.map(job,ids)):
            out[r]=v
            if i%50==0: print(i,flush=True)
    json.dump(out,open(D+'/races.json','w'),ensure_ascii=False)
    hids=sorted({h['hid'] for v in out.values() if 'pre' in v for h in v['pre']['horses'] if h['hid']})
    print('horses',len(hids),flush=True)
    def hjob(h):
        s=get(f'https://db.netkeiba.com/horse/{h}/',f'h{h}')
        m=re.search(r'生産者</th>\s*<td[^>]*>(.*?)</td>',s,re.S)
        return h,dict(breeder=T(m.group(1)) if m else '',gai=bool(re.search(r'[A-Za-z]',T(m.group(1)) if m else '')))
    hinfo={}
    with ThreadPoolExecutor(4) as ex:
        for i,(h,v) in enumerate(ex.map(hjob,hids)):
            hinfo[h]=v
            if i%500==0: print('h',i,flush=True)
    json.dump(hinfo,open(D+'/horses.json','w'),ensure_ascii=False)
    print('done',flush=True)
