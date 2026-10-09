# 使い方: python3 tools/day.py 2026-10-10 [出力JSON]
# その日のJRA全レース（1R〜12R）を、学習した重みで採点して印をつける。出走前の情報だけを使う。
import json,re,sys,os,numpy as np
sys.path.insert(0,os.path.dirname(__file__)); import scrape,feat
W=json.load(open(os.path.dirname(__file__)+'/weights.json')); FK=W['FK']; w=np.array(W['w'])
date=sys.argv[1]; out=sys.argv[2] if len(sys.argv)>2 else None
C=scrape.C
for f in os.listdir(C):
    if f.startswith(('past','shu','list')) : os.remove(os.path.join(C,f))   # 出馬表・馬体重は毎回取り直す
s=scrape.get(f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date.replace("-","")}','list'+date)
rids=sorted(set(re.findall(r'race_id=(\d{12})',s)))
VEN={'01':'札幌','02':'函館','03':'福島','04':'新潟','05':'東京','06':'中山','07':'中京','08':'京都','09':'阪神','10':'小倉'}
SHORT={'前走人気で大敗（不利・出遅れ候補）':'前走人気で大敗','3歳（秋・古馬混合）':'秋の3歳','ノーザン生産':'ノーザン','外国産':'外国産',
 'ダート外枠':'ダート外枠','前走3着内':'前走3着内','j_ルメール':'ルメール','j_川田':'川田','j_武豊':'武豊','j_松山岩田望津村':'信頼騎手',
 'j_丹内菊沢ローカル':'ローカルの丹内・菊沢','ダート替わり初戦':'ダート替わり初戦(減点)','短距離内枠逃げ先行':'短距離内枠の先行',
 'ノーザン休み明け体重増（不明含まず）':'ノーザン休み明け増'}
PREF=['前走人気で大敗（不利・出遅れ候補）','3歳（秋・古馬混合）','ダート外枠','短距離内枠逃げ先行','j_丹内菊沢ローカル']
H={}; races=[]
for rid in rids:
    pre=scrape.pre(rid); ri=feat.race_info(pre,date)
    if ri['surf'] not in('芝','ダ'): continue
    rows=[]
    for h in pre['horses']:
        if not h['hid'] or not h['uma']: continue
        if h['hid'] not in H:
            t=scrape.get(f'https://db.netkeiba.com/horse/{h["hid"]}/',f'h{h["hid"]}')
            m=re.search(r'生産者</th>\s*<td[^>]*>(.*?)</td>',t,re.S); b=scrape.T(m.group(1)) if m else ''
            H[h['hid']]=dict(breeder=b,gai=bool(re.search('[A-Za-z]',b)))
        f=feat.features(h,ri,H)
        v=np.array([1.0]+[float(f[k]) for k in FK]+[min(f['_best_diff'],2),f['jockey_score']])
        p=float(1/(1+np.exp(-v@w)))
        name=h['info'].split()[1] if len(h['info'].split())>1 else '?'
        why=[SHORT[k] for k in SHORT if f.get(k)]
        if f['_best_diff']<9: why.insert(0,f"近3走の最小着差{f['_best_diff']:+.1f}秒" if f['_best_diff']!=0 else '近走で勝ち負け')
        rows.append(dict(p=p,uma=h['uma'],waku=int(h['waku'] or 0),name=name,jockey=f['_jockey'],why='・'.join(why[:4]),f=f,newbie=not h['past']))
    if not rows: continue
    rows.sort(key=lambda r:-r['p'])
    marks=[dict(mark=mk,uma=r['uma'],waku=r['waku'],name=r['name'],jockey=r['jockey'],pct=round(r['p']*100),why=r['why']) for mk,r in zip('◎○▲',rows)]
    himo=[r for r in rows[3:] if any(r['f'].get(k) for k in PREF)][:2]
    if len(himo)<2: himo+= [r for r in rows[3:] if r not in himo][:2-len(himo)]
    marks+=[dict(mark='紐',uma=r['uma'],waku=r['waku'],name=r['name'],jockey=r['jockey'],pct=round(r['p']*100),why=r['why']) for r in himo]
    newbie=all(r['newbie'] for r in rows)
    races.append(dict(rid=rid,R=int(rid[-2:]),venue=VEN.get(rid[4:6],''),name=pre['name'].strip(),
        course=f"{VEN.get(rid[4:6],'')}{int(rid[-2:])}R {ri['surf']}{'ート' if ri['surf']=='ダ' else ''}{ri['dist']}m・{len(rows)}頭",
        status='データ採点（新馬戦は参考程度）' if newbie else 'データ採点',marks=marks))
races.sort(key=lambda r:(r['R'],r['venue']))
for r in races:
    print(f"{r['course']} {r['name']}  "+' '.join(f"{m['mark']}{m['uma']}{m['name']}({m['pct']}%)" for m in r['marks']))
if out: json.dump(races,open(out,'w'),ensure_ascii=False)
