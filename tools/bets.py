# 買い方の提案と検証
# 使い方: python3 tools/bets.py <日付> <days ドキュメントJSON>   … 結果と照らして買い方ごとの回収率を出す
import re,html,json,sys,os,time,urllib.request,itertools,collections
T=lambda x:' '.join(html.unescape(re.sub(r'<[^>]+>',' ',x)).split())
C=os.environ.get('KEIBA_CACHE','/tmp/keiba-cache')

def plan(race):
    """印と確率から買い目を決める（1点100円）。戻り値: [(券種, 馬番タプル, 説明)]"""
    mk={m['mark']:m for m in race['marks'] if m['mark'] in '◎○▲'}
    himo=[m['uma'] for m in race['marks'] if m['mark']=='紐']
    if '◎' not in mk: return [],''
    a=mk['◎']['uma']; p=mk['◎'].get('pct',0); o=[mk[k]['uma'] for k in '○▲' if k in mk]
    t=[]
    if p>=50:
        kind='軸型：◎は3着内に来やすいが勝ち切れないことも多い → 複勝と3連複1点'
        t+=[('複勝',(a,),'◎の複勝'),('3連複',tuple([a]+o),'◎○▲の1点')]
    elif p>=35:
        kind='勝負型：◎の単勝に妙味 → 単勝と馬連'
        t+=[('単勝',(a,),'◎の単勝')]+[('馬連',(a,b),'◎-'+b) for b in o]
    else:
        kind='混戦型：配当がつきやすい → 単勝と3連複1点の少額'
        t+=[('単勝',(a,),'◎の単勝'),('3連複',tuple([a]+o),'◎○▲の1点')]
    return t,kind

def attach(race):
    """race に買い方（race['bets']）を付ける"""
    t,kind=plan(race)
    race['bets']=dict(type=kind,tickets=[f"{k} {'-'.join(h)}" for k,h,_ in t],cost=100*len(t)) if t else None
    return race['bets']

def get(u,key):
    p=f'{C}/{key}'
    if os.path.exists(p): return open(p,encoding='utf-8').read()
    for i in range(5):
        try:
            s=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read().decode('utf-8','ignore'); break
        except Exception: time.sleep(3*(i+1)); s=''
    if 'Payout_Detail_Table' in s: open(p,'w',encoding='utf-8').write(s)
    return s
def payouts(rid):
    s=get(f'https://race.netkeiba.com/race/result.html?race_id={rid}',f'res{rid}')
    m=re.search(r'Payout_Detail_Table.*?(?=<div class="Result_Note|$)',s,re.S); pay={}
    for k,body in re.findall(r'<tr class="(\w+)">(.*?)</tr>',m.group(0) if m else '',re.S):
        cells=dict(re.findall(r'<td class="(\w+)">(.*?)</td>',body,re.S))
        nums=re.findall(r'<span>(\d+)</span>',cells.get('Result','')) or re.findall(r'\d+',T(cells.get('Result','')))
        pays=[int(x.replace(',','')) for x in re.findall(r'([\d,]+)円',T(cells.get('Payout','')))]
        pay[k]=(nums,pays)
    return pay
NAME={'単勝':('Tansho',1),'複勝':('Fukusho',1),'馬連':('Umaren',2),'ワイド':('Wide',2),'3連複':('Fuku3',3)}
def ret(pay,kind,horses):
    k,n=NAME[kind]; nums,pays=pay.get(k,([],[]))
    groups=[nums[i:i+n] for i in range(0,len(nums),n)] if kind in('ワイド','複勝') else [nums[:n]]
    for g,pp in zip(groups,pays):
        if sorted(g,key=int)==sorted(horses,key=int): return pp
    return 0

if __name__=='__main__':
    date=sys.argv[1]; d=json.load(open(sys.argv[2]))
    lst=get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}',f'list{date}')
    VEN={'05':'東京','08':'京都'}
    tot=collections.defaultdict(lambda:[0,0]); 
    for rid in sorted(set(re.findall(r'race_id=(\d{12})',lst))):
        key=f"{VEN.get(rid[4:6],'')}{int(rid[-2:])}R "
        race=next((r for r in d['races'] if r['course'].startswith(key)),None)
        if not race: continue
        pay=payouts(rid)
        if not pay: continue
        t,kind=plan(race); p=race['marks'][0].get('pct',0)
        band='50+' if p>=50 else '35-49' if p>=35 else '<35'
        got=sum(ret(pay,k,h) for k,h,_ in t)
        tot['提案'][0]+=100*len(t); tot['提案'][1]+=got
        tot['提案'+band][0]+=100*len(t); tot['提案'+band][1]+=got
        a=race['marks'][0]['uma']; o=[m['uma'] for m in race['marks'][1:3]]; hm=[m['uma'] for m in race['marks'][3:]]
        alt={'単勝◎':[('単勝',(a,))],'複勝◎':[('複勝',(a,))],'ワイド◎-○▲':[('ワイド',(a,b)) for b in o],'馬連◎-○▲':[('馬連',(a,b)) for b in o],
             '3連複◎1頭軸(○▲紐)':[('3連複',(a,)+x) for x in itertools.combinations(o+hm,2)],'3連複◎○▲1点':[('3連複',tuple([a]+o))],'ワイドBOX◎○▲':[('ワイド',x) for x in itertools.combinations([a]+o,2)]}
        for nm,tk in alt.items():
            for kk in (nm,nm+'|'+band):
                tot[kk][0]+=100*len(tk); tot[kk][1]+=sum(ret(pay,k,h) for k,h in tk)
        print(key,band,kind[:3],len(t),'点',got,'円',file=sys.stderr)
    json.dump({k:v for k,v in tot.items()},sys.stdout,ensure_ascii=False)
