# 調教師の条件別成績（過去1年・全レース）。新馬・芝/ダ・距離帯（短〜1400/中〜2000/長2100〜）
import json,os
D=json.load(open(os.path.join(os.path.dirname(__file__),'trainers.json')))
K=30  # 少ない走数の数字に振り回されないよう、平均値を30走ぶん足して縮める
def cats(surf,dist,newbie):
    c=[surf,f"{surf}{'短' if dist<=1400 else '中' if dist<=2000 else '長'}"]
    if newbie: c.append('新馬')
    return c
LAB={'新馬':'新馬','芝':'芝','ダ':'ダート','芝短':'芝短距離','芝中':'芝中距離','芝長':'芝長距離','ダ短':'ダート短距離','ダ中':'ダート中距離','ダ長':'ダート長距離'}
def info(tid,surf,dist,newbie):
    """一番細かい条件での (縮小した上振れ, 表示用の文) を返す"""
    t=D['trainers'].get(tid)
    if not t: return 0.0,''
    for c in reversed(cats(surf,dist,newbie)):
        v=t['c'].get(c)
        if v:
            b=D['base'][c]; adj=(v[1]+K*b)/(v[0]+K)-b
            txt=f"{t['name'].split(' ')[-1]}厩舎は{LAB[c]}で3着内{100*v[1]/v[0]:.0f}%（{v[0]}走、平均{100*b:.0f}%）"
            return adj,txt
    return 0.0,''
