"""Kuku promo discovery: reproducible rule-based baseline, no dependencies."""
import argparse, csv, json, re, zipfile
from pathlib import Path
BLOCK = re.compile(r'(?m)^\*\*(.+?):\*\*\s*\nStart: \((\d\d:\d\d\.\d+)\) \| End: \((\d\d:\d\d\.\d+)\)\s*\n(.*?)(?=\n\s*\n|\Z)', re.S)
SCENE = re.compile(r'(?m)^Scene start: (\d\d:\d\d\.\d+)|^Scene end: (\d\d:\d\d\.\d+)')
HOOK = re.compile(r'\b(why|what|who|how|never|no|stop|wait|marry|husband|wife|duke|secret|betray|kill|dead|divorce|liar|truth|father|mother|sister|brother|look)\b|[?!]', re.I)
CLIFF = re.compile(r'\b(why|what|who|how|but|unless|wait|stop|never|secret|truth|actually|real|if|or else|not|cannot|will|must)\b|[?!]|\.\.\.', re.I)
CONFLICT = re.compile(r'\b(betray|hate|liar|marry|husband|wife|duke|secret|kill|dead|shame|humiliat|slap|shock|threat|revenge|abandon|reject|love|divorce|wedding|blood|enemy)\w*', re.I)
def seconds(s):
    m,rest=s.split(':'); return round(int(m)*60+float(rest),2)
def stamp(t): return f'{int(t//60):02d}:{t%60:05.2f}'
def parse_script(txt,episode):
    items=[]
    for m in BLOCK.finditer(txt):
        kind,start,end,body=m.groups(); a,b=seconds(start),seconds(end)
        if b>a: items.append(dict(kind=kind.strip(),start=a,end=b,text=re.sub(r'\s+',' ',body).strip()))
    items.sort(key=lambda x:(x['start'],x['end']))
    scenes=[seconds(v) for pair in SCENE.findall(txt) for v in pair if v]
    return dict(episode=episode,duration=max([x['end'] for x in items]+scenes+[0]),items=items)
def load_zip(path):
    eps=[]
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if re.search(r'episode-\d+.*\.txt$',n,re.I)):
            num=int(re.search(r'episode-(\d+)',name,re.I).group(1))
            eps.append(parse_script(z.read(name).decode('utf-8-sig'),num))
    return eps
def dialogue(x): return x['kind'].upper() not in {'ACTION','CAMERA','SFX','MUSIC','SOUND','VFX'}
def evaluate(ep,start,end):
    entries=[x for x in ep['items'] if x['start']<end and x['end']>start]
    spoken=[x for x in entries if dialogue(x)]
    opening=[x for x in entries if x['start']<start+3 and x['end']>start]
    ending=[x for x in entries if x['end']>end-5 and x['start']<end]
    hooks=[x for x in opening if dialogue(x) and HOOK.search(x['text'])]
    cliffs=[x for x in ending if dialogue(x) and CLIFF.search(x['text'])]
    hook=hooks[0] if hooks else next((x for x in opening if dialogue(x)),None)
    cliff=cliffs[-1] if cliffs else next((x for x in reversed(ending) if dialogue(x)),None)
    conflict=sum(bool(CONFLICT.search(x['text'])) for x in spoken)
    context=sum(bool(re.search(r'\b(he|she|they|him|her|them|this|that)\b',x['text'],re.I)) for x in spoken[:2])
    score=round(2*(3 if hooks else 1 if hook else 0)+2*(3 if cliffs else 1 if cliff else 0)+min(conflict,5)*.6+min(len(spoken),8)*.15-min(context,2)*.6,2)
    warnings=[]
    if not hooks: warnings.append('Weak or missing immediate dialogue hook')
    if not cliffs: warnings.append('Weak or missing unresolved ending')
    if not spoken: warnings.append('No dialogue')
    if context>=2: warnings.append('Opening may require prior context')
    if not any(x['kind'].upper()=='ACTION' for x in entries): warnings.append('No explicit action beat in clip')
    desc=lambda x: f"{x['kind']}: {x['text'][:180]}" if x else 'No clear dialogue moment detected'
    return dict(episode=ep['episode'],segments=[dict(episode=ep['episode'],start=stamp(start),end=stamp(end))],start_seconds=start,end_seconds=end,duration_seconds=round(end-start,2),hook=desc(hook),cliffhanger=desc(cliff),why_it_works=f'{"Immediate verbal tension" if hooks else "Opening action/dialogue"}; {"unresolved final line" if cliffs else "possible suspense at the cut"}; {conflict} conflict-related dialogue beats.',score=score,quality_warnings=warnings,method='heuristic baseline; requires editorial validation')
def candidates(ep):
    events=sorted(set(round(x['start'],2) for x in ep['items'] if dialogue(x) or x['kind'].upper()=='ACTION'))
    ends=sorted(set(round(x['end'],2) for x in ep['items'] if dialogue(x) or x['kind'].upper()=='ACTION'))
    pool=[]
    for s in events:
        for e in sorted((e for e in ends if 20<=e-s<=60),key=lambda t:abs(t-s-38))[:5]:
            pool.append(evaluate(ep,s,e))
    return sorted(pool,key=lambda x:-x['score'])
def select(episodes,per_episode=2,total=30):
    pool=[]
    for ep in episodes:
        picked=[]
        for c in candidates(ep):
            if any(max(0,min(c['end_seconds'],p['end_seconds'])-max(c['start_seconds'],p['start_seconds']))/min(c['duration_seconds'],p['duration_seconds'])>.35 for p in picked): continue
            picked.append(c)
            if len(picked)>=per_episode: break
        pool.extend(picked)
    pool.sort(key=lambda x:(-x['score'],len(x['quality_warnings']),x['episode']))
    for i,c in enumerate(pool,1): c['rank']=i
    return pool[:total],pool
def main():
    ap=argparse.ArgumentParser();ap.add_argument('input_zip');ap.add_argument('--output',default='outputs');ap.add_argument('--top',type=int,default=30)
    args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    eps=load_zip(args.input_zip);top,all_results=select(eps,total=args.top)
    (out/'all_candidates.json').write_text(json.dumps(all_results,indent=2,ensure_ascii=False))
    (out/'top_promos.json').write_text(json.dumps(top,indent=2,ensure_ascii=False))
    with (out/'top_promos.csv').open('w',newline='') as f:
        fields=['rank','episode','start','end','duration_seconds','score','hook','cliffhanger','why_it_works','quality_warnings']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for c in top: writer.writerow(dict(rank=c['rank'],episode=c['episode'],start=c['segments'][0]['start'],end=c['segments'][0]['end'],duration_seconds=c['duration_seconds'],score=c['score'],hook=c['hook'],cliffhanger=c['cliffhanger'],why_it_works=c['why_it_works'],quality_warnings='; '.join(c['quality_warnings'])))
    summary=dict(episodes_processed=len(eps),timestamped_blocks=sum(len(e['items']) for e in eps),candidates_after_dedup=len(all_results),top_count=len(top),episodes_with_no_blocks=[e['episode'] for e in eps if not e['items']])
    (out/'run_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
