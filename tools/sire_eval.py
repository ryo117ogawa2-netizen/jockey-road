# 使い方: python3 sire_eval.py <種牡馬名>  → 産駒の過去1年（全レース）の成績を、人気からの期待と比べる
import sys,re,json,urllib.request,urllib.parse,collections,html
def get(u,enc='euc-jp'):
    b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
    try: return b.decode(enc)
    except: return b.decode('utf-8','ignore')
name=sys.argv[1]
s=get('https://db.netkeiba.com/?pid=horse_list&word='+urllib.parse.quote(name.encode('euc-jp')))
sid=re.search(r'horse/(\d{10})/',s).group(1)
kids=set(); page=1
while True:
    t=get(f'https://db.netkeiba.com/horse/list.html?sire_id={sid}&range=all&page={page}')
    ids=set(re.findall(r'db\.netkeiba\.com/horse/(\d{10})/|href="/horse/(\d{10})/',t)); ids={a or b for a,b in ids}-{sid}
    if not ids-kids: break
    kids|=ids; page+=1
    if page>15: break
A=json.load(open(sys.argv[2] if len(sys.argv)>2 else 'yr/allraces.json'))
rows=[]
for r in A:
    if not r['rows'] or r['surf'] not in('芝','ダ'): continue
    for h in r['rows']:
        if h['rank'].isdigit() and h['ninki'].isdigit():
            rows.append(dict(k=h['hid'] in kids,s=r['surf'],nb='新馬' in r['name'] or '新馬' in r['small'],two='2歳' in r['small'],rk=int(h['rank']),nin=min(int(h['ninki']),18),odds=float(h['odds'] or 0),d=r['date']))
pe=collections.Counter(); pn=collections.Counter()
for x in rows: pn[x['nin']]+=1; pe[x['nin']]+=x['rk']<=3
exp={k:pe[k]/pn[k] for k in pn}
def show(lab,g):
    n=len(g)
    if not n: print(f'| {lab} | 0 |'); return
    print(f"| {lab} | {n} | {100*sum(x['rk']==1 for x in g)/n:.1f}% | {100*sum(x['rk']<=3 for x in g)/n:.1f}% | {100*sum(exp[x['nin']] for x in g)/n:.1f}% | {sum(x['odds']*100 for x in g if x['rk']==1)/n:.0f}% | {sum(x['nin'] for x in g)/n:.1f} |")
print(f'{name}（id {sid}）産駒 {len(kids)}頭\n| 区分 | 出走 | 勝率 | 3着内 | 人気から期待 | 単回 | 平均人気 |')
K=[x for x in rows if x['k']]
show('全体',K); show('芝',[x for x in K if x['s']=='芝']); show('ダート',[x for x in K if x['s']=='ダ']); show('新馬',[x for x in K if x['nb']])
show('2歳戦（比較：全馬）',[x for x in rows if x['two']])
