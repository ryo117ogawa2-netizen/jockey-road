# 出走前の情報だけから特徴量を作る（結果は使わない）
import re,datetime
LOCAL={'札幌','函館','福島','新潟','小倉','中京'}
JK={'ルメール':5,'川田':4,'武豊':3,'松山':2,'岩田望':2,'津村':2}
LOCALJK={'丹内':2,'菊沢':2}
def num(x,d=None):
    try: return int(x)
    except: return d
def parse_past(p):
    m=re.match(r'(\d{4})\.(\d\d)\.(\d\d) (\S+) (\S+) ',p)
    if not m: return None
    d=datetime.date(int(m[1]),int(m[2]),int(m[3]))
    rank=num(m[5])
    if rank is None: return None   # 除外・取消・中止は走っていないので数えない
    sd=re.search(r' (芝|ダ|障)(\d{3,4})',p)
    nin=re.search(r' (\d+)人 ',p)
    pas=re.search(r' ([\d\-]+) \((\d\d\.\d)\)',p)
    w=re.search(r' (\d{3})\(([+\-]?\d+)\)',p)
    diff=re.search(r'\((-?\d+\.\d)\)\s*$',p)
    heads=re.search(r' (\d+)頭',p)
    return dict(date=d,venue=m[4],rank=rank,surf=sd[1] if sd else None,dist=num(sd[2]) if sd else None,
                ninki=num(nin[1]) if nin else None,first=num(pas[1].split('-')[0]) if pas else None,
                agari=float(pas[2]) if pas else None,w=num(w[1]) if w else None,wd=num(w[2]) if w else None,
                diff=float(diff[1]) if diff else None,heads=num(heads[1]) if heads else None,
                cls=p)
def race_info(pre,date):
    d1,d2=pre['d1'],pre['d2']
    sd=re.search(r'(芝|ダ|障)(\d{3,4})m',d1)
    v=re.search(r'\d+回 (\S+) (\d+)日目',d2)
    return dict(surf=sd[1] if sd else None,dist=num(sd[2]) if sd else None,venue=v[1] if v else '',day=num(v[2]) if v else None,
                handi='ハンデ' in d2,heads=len(pre['horses']),date=datetime.date.fromisoformat(date),
                older='以上' in d2,grade=('G' in pre['name']))
def features(h,ri,hinfo):
    info=h['info']; j=h['jockey'].split()
    sire=info.split()[0] if info else ''
    style=next((t for t in info.split() if t in ('逃','先','差','追')),None)
    w=re.search(r'(\d{3})kg \(([+\-]?\d+)\)',info)
    wd=num(w[2]) if w else None
    sexage=j[0] if j else ''; age=num(re.sub(r'\D','',sexage[1:3]) or 0)
    jockey=j[1] if len(j)>1 else ''; jockey='ルメール' if jockey.startswith('ルメ') else jockey; kin=float(j[2]) if len(j)>2 and re.match(r'[\d.]+$',j[2]) else None
    pasts=[x for x in (parse_past(p) for p in h['past']) if x]
    p1=pasts[0] if pasts else None
    gap=(ri['date']-p1['date']).days if p1 else None
    br=hinfo.get(h['hid'],{}).get('breeder','')
    nf=br=='ノーザンファーム'; sh=br in('社台ファーム','社台コーポレーション白老ファーム')
    waku=num(h['waku'],0); uma=num(h['uma'],0)
    f={}
    js=JK.get(jockey,0)
    if ri['venue'] in LOCAL: js=max(js,LOCALJK.get(jockey,0))
    f['jockey_score']=js
    f['j_ルメール']=jockey=='ルメール'; f['j_川田']=jockey=='川田'; f['j_武豊']=jockey=='武豊'
    f['j_松山岩田望津村']=jockey in('松山','岩田望','津村'); f['j_丹内菊沢ローカル']=jockey in LOCALJK and ri['venue'] in LOCAL
    f['ノーザン生産']=nf; f['社台生産']=sh
    rest=gap is not None and gap>=70
    f['休み明け']=rest
    f['ノーザン休み明け体重増']=nf and rest and (wd or 0)>0
    f['ノーザン休み明け体重増（不明含まず）']=nf and rest and wd is not None and wd>=4
    t2=False
    if len(pasts)>=2 and gap is not None and gap<70:
        g2=(pasts[0]['date']-pasts[1]['date']).days
        if g2>=70 and (pasts[0]['wd'] or 0)>0 and wd is not None and wd<0: t2=True
    f['叩き2戦目で絞れた']=t2
    f['ダート外枠']=ri['surf']=='ダ' and waku>=7
    f['ダート内枠']=ri['surf']=='ダ' and 1<=waku<=2
    f['短距離内枠逃げ先行']=ri['surf'] in('芝','ダ') and (ri['dist'] or 9999)<=1400 and 1<=waku<=3 and style in('逃','先')
    surf_past=[p['surf'] for p in pasts if p['surf']]
    dsw=ri['surf']=='ダ' and surf_past and all(s=='芝' for s in surf_past)
    gai=hinfo.get(h['hid'],{}).get('gai',False)
    f['ダート替わり初戦']=bool(dsw)
    f['外国産/オルフェ産駒のダート替わり']=bool(dsw) and (gai or sire=='オルフェーヴル')
    f['前走人気で大敗（不利・出遅れ候補）']=bool(p1 and p1['ninki'] and p1['rank'] and p1['ninki']<=3 and p1['rank']>=6)
    f['前走出遅れ（初角が後方）']=bool(p1 and p1['first'] and p1['heads'] and style in('逃','先') and p1['first']>=p1['heads']*0.6)
    # 相棒側の特徴
    f['3歳（秋・古馬混合）']=age==3 and ri['older'] and ri['date'].month in(9,10,11,12)
    f['開幕週の逃げ先行']=(ri['day'] or 99)<=4 and style in('逃','先')
    f['逃げ先行']=style in('逃','先')
    f['前走3着内']=bool(p1 and p1['rank'] and p1['rank']<=3)
    f['前走0.3秒差以内']=bool(p1 and p1['diff'] is not None and p1['diff']<=0.3)
    best=min([p['diff'] for p in pasts[:3] if p['diff'] is not None] or [9])
    f['_best_diff']=best
    f['近3走で0.2秒差以内あり']=best<=0.2
    ag=[p['agari'] for p in pasts[:3] if p['agari']]
    f['外国産']=gai
    f['_wd']=wd; f['_style']=style; f['_age']=age; f['_jockey']=jockey; f['_br']=br; f['_sire']=sire
    f['_p1rank']=p1['rank'] if p1 else None
    return f
