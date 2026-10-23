# 馬場の傾向（内前／外差し）を結果から読み取り、予想の紐に反映する
# 使い方:
#   python3 tools/bias.py analyze <日付> [<日付> ...] > bias.json   … 指定日の確定レースから 場×芝ダ の傾向を出す
#   python3 tools/bias.py apply <bias.json> <days ドキュメントJSON>    … 傾向が強い場・コースのレースに、合う馬を紐に1頭足す
import re,html,json,sys,os,time,urllib.request,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
T=lambda x:' '.join(html.unescape(re.sub(r'<[^>]+>',' ',x)).split())
C=os.environ.get('KEIBA_CACHE','/tmp/keiba-cache')
VEN={'01':'札幌','02':'函館','03':'福島','04':'新潟','05':'東京','06':'中山','07':'中京','08':'京都','09':'阪神','10':'小倉'}

def get(u,key=None,keep=None):
    p=f'{C}/{key}' if key else None
    if p and os.path.exists(p): return open(p,encoding='utf-8').read()
    s=''
    for i in range(4):
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
            s=b.decode('utf-8','ignore')
            if 'race_id' not in s and '出馬表' not in s and 'レース結果' not in s: s=b.decode('euc-jp','ignore')
            break
        except Exception: time.sleep(3*(i+1))
    if p and keep and keep in s:
        os.makedirs(C,exist_ok=True); open(p,'w',encoding='utf-8').write(s)
    return s

def race_ids(date):
    s=get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}')
    return sorted(set(re.findall(r'race_id=(\d{12})',s)))

def result(rid):
    """確定レースの上位3頭の 枠・馬番・4角の位置（割合）と 芝ダ・頭数。未確定なら None"""
    s=get(f'https://race.netkeiba.com/race/result.html?race_id={rid}',f'bias_res{rid}',keep='Corner_Num')
    tb=re.search(r'id="All_Result_Table".*?</table>',s,re.S)
    cn=re.search(r'<strong>4</strong>コーナー</th>\s*<td>(.*?)</td>',s,re.S)
    if not tb or not cn: return None
    info=T((re.search(r'RaceData01.*?</div>',s,re.S) or re.search('$',s)).group(0))
    surf='ダ' if 'ダ' in info.split('m')[0] else '障' if '障' in info.split('m')[0] else '芝'
    rows=[]
    for tr in re.findall(r'<tr[^>]*>.*?</tr>',tb.group(0),re.S)[1:]:
        c=[T(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
        if len(c)>3 and c[0].isdigit(): rows.append((int(c[0]),int(c[1]),c[2]))
    order=re.findall(r'\d+',T(cn.group(1)))
    n=len(rows)
    if not n or not order: return None
    top=[]
    for rk,waku,uma in sorted(rows)[:3]:
        if uma in order: top.append(dict(rank=rk,waku=waku,uma=int(uma),pos=(order.index(uma)+1)/n))
    return dict(rid=rid,venue=VEN.get(rid[4:6],''),R=int(rid[-2:]),surf=surf,n=n,top=top)

def analyze(dates):
    """場×芝ダごとに、上位3頭のうち 前（4角で前1/3）・後ろ（後ろ1/3）・内（馬番が前半）・外 の割合"""
    agg=collections.defaultdict(lambda:dict(races=0,horses=0,front=0,back=0,inner=0,outer=0,win_front=0,win_back=0,win_in=0,win_out=0))
    for d in dates:
        for rid in race_ids(d):
            r=result(rid)
            if not r or r['surf']=='障' or not r['top']: continue
            a=agg[f"{r['venue']}{r['surf']}"]; a['races']+=1
            for h in r['top']:
                a['horses']+=1
                f=h['pos']<=1/3; b=h['pos']>2/3; i=h['uma']<=r['n']/2
                a['front']+=f; a['back']+=b; a['inner']+=i; a['outer']+=not i
                if h['rank']==1: a['win_front']+=f; a['win_back']+=b; a['win_in']+=i; a['win_out']+=not i
    out={}
    for k,a in agg.items():
        h=max(1,a['horses']); fr=a['front']/h; bk=a['back']/h; inn=a['inner']/h
        tag=[]
        # 上位3頭が偶然でもこのくらいは出る：前1/3・後ろ1/3 は各33%、内外は各50%
        if a['races']>=5:
            if fr>=0.50: tag.append('前有利')
            elif bk>=0.40: tag.append('差し有利')
            if inn>=0.65: tag.append('内有利')
            elif inn<=0.35: tag.append('外有利')
        out[k]=dict(a,front_pct=round(100*fr),back_pct=round(100*bk),inner_pct=round(100*inn),tag=tag,
                    text=f"{k}（{a['races']}R）：上位3頭の4角位置 前{round(100*fr)}%・後ろ{round(100*bk)}%／馬番 内{round(100*inn)}%・外{100-round(100*inn)}%"+(f" → {'・'.join(tag)}" if tag else ' → はっきりした偏りなし'))
    return out

def styles(rid):
    """出走馬ごとの近3走の4角位置（割合の平均。小さいほど前）と馬番"""
    s=get(f'https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}',f'bias_past{rid}',keep='HorseList')
    res={}
    for tr in re.findall(r'<tr[^>]*HorseList[^>]*>.*?</tr>',s,re.S):
        u=re.search(r'class="Waku">\s*(\d+)',tr) or re.search(r'Umaban\d*[^>]*>\s*(\d+)',tr)
        nm=re.search(r'class="Horse02">\s*<a[^>]*>([^<]+)</a>',tr,re.S) or re.search(r'HorseName.*?>([^<]+)</a>',tr,re.S)
        ps=[]
        for td in re.findall(r'<td[^>]*class="Past[^"]*"[^>]*>(.*?)</td>',tr,re.S)[:3]:
            t=T(td); n=re.search(r'(\d+)頭',t); p=re.search(r'\s(\d+(?:-\d+)+)\s*\(',t)
            if n and p: ps.append(int(p.group(1).split('-')[-1])/int(n.group(1)))
        w=re.search(r'Waku(\d)',tr)
        if u: res[u.group(1)]=dict(name=nm.group(1).strip() if nm else '',waku=int(w.group(1)) if w else 0,style=sum(ps)/len(ps) if ps else None)
    return res

def odds(rid):
    try:
        d=json.loads(get(f'https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={rid}&type=1&action=init'))
        return {str(int(k)):float(v[0]) for k,v in d['data']['odds']['1'].items() if v[0] not in('','---')}
    except Exception: return {}

def apply(bias,day):
    """傾向がはっきりした場・コースのレースで、傾向に合う印なしの馬（単勝30倍以内でいちばん人気）を紐に1頭足す。◎○▲は動かさない"""
    import bets
    changed=[]
    for r in day['races']:
        if r.get('result'): continue
        m=re.match(r'(\D+?)\d+R\s*(芝|ダ|障)',r.get('course',''))
        if not m: continue
        b=bias.get(m.group(1)+m.group(2))
        if not b or not b['tag']: continue
        r['bias']=b['text']
        st=styles(r['rid']); od=odds(r['rid']); n=len(st) or 16
        marked={x['uma'] for x in r['marks']}
        def fit(u,x):
            s=x['style']
            if s is None: return False
            ok=True
            if '前有利' in b['tag']: ok&= s<=0.40
            if '差し有利' in b['tag']: ok&= s>=0.55
            if '内有利' in b['tag']: ok&= int(u)<=n/2
            if '外有利' in b['tag']: ok&= int(u)>n/2
            return ok
        def clash(u,x):
            # はっきり逆の馬だけ（前有利なのに後方一辺倒、外有利なのに最内付近 など）
            s=x['style']
            return (('前有利' in b['tag'] and s>=0.6) or ('差し有利' in b['tag'] and s<=0.3)
                    or ('外有利' in b['tag'] and int(u)<=n/3) or ('内有利' in b['tag'] and int(u)>2*n/3))
        cand=[(od.get(u,999),u,x) for u,x in st.items() if u not in marked and fit(u,x) and od.get(u,999)<=30]
        # 印の馬で傾向に合わない馬にはメモだけ付ける（印は動かさない）
        for mk in r['marks']:
            x=st.get(mk['uma'])
            if x and x['style'] is not None and clash(mk['uma'],x) and mk['mark'] in '◎○▲' and '馬場傾向' not in mk.get('why',''):
                mk['why']=(mk.get('why','')+f" ／ 馬場傾向（{'・'.join(b['tag'])}）とは逆の脚質・枠なので割り引き気味").strip(' ／')
        if cand:
            o,u,x=sorted(cand)[0]
            if not x['name']:   # 馬柱から名前が取れなかったときは出馬表から
                try:
                    import scrape
                    x['name']=next((h.get('name') or '' for h in scrape.pre(r['rid'])['horses'] if h['uma']==u),'')
                except Exception: pass
            if not any(mm.get('bias') for mm in r['marks']):
                r['marks'].append(dict(mark='紐',uma=u,waku=x['waku'],name=x['name'],jockey='',pct=None,bias=True,
                    why=f"馬場傾向で追加：{'・'.join(b['tag'])}（近3走の4角位置 平均{round(100*x['style'])}%地点・{u}番、単勝{o}倍）"))
                changed.append(f"{r['course'].split(' ')[0]} 紐{u}{x['name']}（{'・'.join(b['tag'])}・{o}倍）")
        bets.attach(r)
    return changed

if __name__=='__main__':
    if sys.argv[1]=='analyze':
        json.dump(analyze(sys.argv[2:]),sys.stdout,ensure_ascii=False,indent=1)
    elif sys.argv[1]=='apply':
        bias=json.load(open(sys.argv[2])); p=sys.argv[3]; day=json.load(open(p))
        for k,v in bias.items(): print(v['text'])
        ch=apply(bias,day)
        day['trend']=' ／ '.join(v['text'] for v in bias.values() if v['tag'])
        json.dump(day,open(p,'w'),ensure_ascii=False)
        print('紐に追加：'+('、'.join(ch) if ch else 'なし'))
