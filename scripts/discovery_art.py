#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""R8: bounded, resumable search with saved numeric and visual feedback."""
import argparse, datetime, json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw
from barricelli.run import ROOT, read_csv, save_json, sha
from barricelli.descriptors import describe, coverage, mean_nearest_diversity, bootstrap_mean_ci
from scripts.descendant_detector import ensure_native, freeze
from scripts.art import rgb, font

BASE = ROOT / 'results/discovery_art'
METHODS = ['random', 'novelty_archive', 'codex_feedback']

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def design(): return json.loads((BASE/'design.json').read_text())
def history(method, repeat):
    return [json.loads(p.read_text()) for p in sorted((BASE/'search'/method/f'repeat{repeat}').glob('trial*/search_record.json'))]

def starting(theta, seed):
    """All organization imposed here is at t0, never during a run."""
    d=design(); rng=np.random.Generator(np.random.PCG64(seed)); w=d['width']; alphabet=d['alphabets'][theta['alphabet_id']]
    if theta['initial_style']=='iid': row=rng.choice(alphabet,w).astype(np.int32)
    else:
        row=np.resize(rng.choice(alphabet,8),w).astype(np.int32)
        jitter=rng.random(w)<.05; row[jitter]=rng.choice(alphabet,int(jitter.sum()))
    row[rng.random(w)>=theta['density']]=0
    mask=np.zeros(w,dtype=bool); layout=theta['layout']
    if layout=='uniform': mask[:]=True
    elif layout=='center_patch': mask[w//4:3*w//4]=True
    elif layout=='two_patches': mask[w//8:3*w//8]=True; mask[5*w//8:7*w//8]=True
    elif layout=='bands': mask=(np.arange(w)//8)%2==0
    else: raise ValueError('undeclared mask')
    row[~mask]=0; return row

def configuration(theta, seed, path, steps=None, row=None, experiment=None, trace=0):
    d=design(); row=starting(theta,seed) if row is None else row
    return {'model':'research','variant':'r8_'+theta['norm'],'norm':theta['norm'],'width':len(row),
            'steps':d['steps'] if steps is None else steps,'boundary':'ring' if theta['norm'].startswith('galloway_') else 'open',
            'iteration_order':'ascending','seed':seed,'initial_state_file':freeze(path,row),'trace_steps':trace,
            'initial_design':theta,'modifications':['R8 explicitly designed initial integer state; inspectable rule profile in RULE_VARIANTS.md',
             'W192 research world; fixed numerical rule throughout, except declared temporal A/B schedule',
             'any extraction, perturbation or environment intervention is recorded in experiment'],
            'experiment':experiment or {}}

def native(conf,path):
    path.mkdir(parents=True,exist_ok=True)
    if not conf['trace_steps']: (path/'events.csv').touch(exist_ok=True)
    return ensure_native(conf,path)

def execute(method,repeat,trial,index,reason):
    d=design(); path=BASE/'search'/method/f'repeat{repeat}'/f'trial{trial:02d}'
    theta=d['space'][index]; seed=24000+1000*repeat+trial
    conf=configuration(theta,seed,path,experiment={'stage':'R8a','method':method,'repeat':repeat,'trial':trial,'space_index':index})
    stats=native(conf,path); saved=path/'search_record.json'
    if saved.exists():
        record=json.loads(saved.read_text())
        if record['space_index']!=index or record['descriptor_sha256']!=sha(ROOT/'barricelli/descriptors.py'): raise ValueError('frozen record differs')
        return record
    desc=describe(read_csv(path/'trajectory.csv'),stats,boundary=conf['boundary'])
    previous=history(method,repeat); v=np.array(desc['vector'])
    novelty=float(np.mean(sorted(np.linalg.norm(v-np.array(r['descriptors']['vector'])) for r in previous)[:3])) if previous else 0.
    record={'method':method,'repeat':repeat,'trial':trial,'space_index':index,'theta':theta,'seed':seed,'path':str(path.relative_to(ROOT)),
            'reason':reason,'descriptors':desc,'novelty_to_previous_knn3':novelty,'engine_seconds':stats['engine_seconds'],
            'process_seconds':stats['process_seconds'],'max_rss_kib':stats['max_rss_kib'],'descriptor_sha256':sha(ROOT/'barricelli/descriptors.py')}
    save_json(saved,record)
    im=rgb(read_csv(path/'trajectory.csv')); im.save(path/'visual.png')
    save_json(path/'visual.recipe.json',{'source':'trajectory.csv','trajectory_sha256':sha(path/'trajectory.csv'),'render':'exact unsmoothed integer pixels; x horizontal, time downward',
       'dimensions':list(im.size),'palette_file':'configs/palette.json','palette_sha256':sha(ROOT/'configs/palette.json'),'renderer_sha256':sha(ROOT/'scripts/art.py')})
    print(method,repeat,trial,index,desc['archive_bin'],flush=True); return record

def feedback(method,batch):
    out=BASE/'feedback'/method; out.mkdir(parents=True,exist_ok=True); target=out/f'batch{batch}.json'
    if target.exists(): return
    report={'created_utc':now(),'batch':batch,'method':method,'space_file':'results/discovery_art/design.json','space_sha256':sha(BASE/'design.json'),
       'question':'Which six untested admissible configurations could expand this search archive? Use own complete visual and numerical history; model explanations are hypotheses.',
       'repeats':{},'visuals':[]}
    for repeat in range(4):
        h=history(method,repeat); report['repeats'][str(repeat)]={'coverage':coverage(h),'records':h}
        cols=4; cw=216; ch=438; canvas=Image.new('RGB',(cols*cw,((len(h)+cols-1)//cols)*ch),'#080f1c'); draw=ImageDraw.Draw(canvas)
        for i,r in enumerate(h):
            x=(i%cols)*cw; y=(i//cols)*ch
            draw.text((x+8,y+3),f"{r['trial']:02d} #{r['space_index']} {r['theta']['norm'].removeprefix('galloway_')}",font=font(11),fill='#60e6ed')
            draw.text((x+8,y+20),f"bin{r['descriptors']['archive_bin']} / TIME ↓",font=font(10),fill='#d8eaf2')
            with Image.open(ROOT/r['path']/'visual.png') as im: canvas.paste(im,(x+8,y+42))
        image_path=out/f'batch{batch}_repeat{repeat}.png'; canvas.save(image_path)
        report['visuals'].append({'repeat':repeat,'file':str(image_path.relative_to(ROOT)),'sha256':sha(image_path),'contains':'every own-history saved trajectory, in trial order, unchanged common palette','time_axis':'downward'})
    save_json(target,report)

def bootstrap():
    d=design(); space=d['space']
    anchors=[dict(norm='galloway_B',alphabet_id=2,density=.65,layout='uniform',initial_style='iid'),
             dict(norm='galloway_A',alphabet_id=1,density=.35,layout='uniform',initial_style='iid'),
             dict(norm='galloway_AB_halves',alphabet_id=3,density=.9,layout='center_patch',initial_style='block8_jitter'),
             dict(norm='conditional',alphabet_id=0,density=.65,layout='two_patches',initial_style='iid')]
    indexes=[space.index(a) for a in anchors]; save_json(BASE/'anchors.json',{'indexes':indexes,'theta':anchors,'selection':'declared common coverage anchors; deterministic and identical across methods/repeats'})
    for method in METHODS:
        for repeat in range(4):
            for trial,index in enumerate(indexes): execute(method,repeat,trial,index,'shared declared anchor')
        feedback(method,0)

def automatic(batch):
    space=design()['space']; start=4+(batch-1)*6
    if not (BASE/f'round{batch}.json').exists(): raise ValueError('declare feedback round before execution')
    for method in METHODS[:2]:
        for repeat in range(4):
            for trial in range(start,start+6):
                saved=BASE/'search'/method/f'repeat{repeat}'/f'trial{trial:02d}'/'search_record.json'
                if saved.exists():
                    r=json.loads(saved.read_text()); execute(method,repeat,trial,r['space_index'],r['reason']); continue
                h=history(method,repeat); tested={r['space_index'] for r in h}; remaining=[i for i in range(len(space)) if i not in tested]
                rng=np.random.default_rng(33000+repeat*100+trial+(10000 if method=='novelty_archive' else 0))
                if method=='novelty_archive':
                    v=np.array([r['descriptors']['vector'] for r in h]); distance=np.sqrt(np.sum((v[:,None]-v[None,:])**2,axis=-1)); np.fill_diagonal(distance,np.inf)
                    score=np.sort(distance,axis=1)[:,:min(3,len(h)-1)].mean(axis=1); parent=h[int(np.argmax(score))]['theta']
                    neighbors=[i for i in remaining if sum(space[i][k]!=parent[k] for k in parent)==1]
                    index=int(rng.choice(neighbors or remaining)); reason='mean3-nearest descriptor novelty parent; untested one-factor neighbor'
                else: index=int(rng.choice(remaining)); reason='uniform untested admissible index'
                execute(method,repeat,trial,index,reason)
        feedback(method,batch)

def proposals(batch):
    proposal=json.loads((BASE/f'proposals{batch}.json').read_text()); source=BASE/'feedback/codex_feedback'/f'batch{batch-1}.json'
    if proposal['feedback_sha256']!=sha(source): raise ValueError('feedback differs from viewed input')
    f=json.loads(source.read_text())
    if proposal['viewed_visuals']!=f['visuals']: raise ValueError('incomplete visual input log')
    for repeat in range(4):
        entries=proposal['repeats'][str(repeat)]; tested={r['space_index'] for r in history('codex_feedback',repeat)}
        if len(entries)!=6: raise ValueError('exactly six proposals required')
        for offset,entry in enumerate(entries):
            trial=4+(batch-1)*6+offset; index=entry['space_index']
            if not 0<=index<len(design()['space']): raise ValueError('inadmissible index')
            exists=(BASE/'search/codex_feedback'/f'repeat{repeat}'/f'trial{trial:02d}'/'search_record.json').exists()
            if index in tested and not exists: raise ValueError('repeated index')
            execute('codex_feedback',repeat,trial,index,entry['hypothesis']); tested.add(index)
    feedback('codex_feedback',batch)
    save_json(BASE/f'round{batch}_outcome.json',{'completed_utc':now(),'proposal_file':f'proposals{batch}.json','codex_coverage':[coverage(history('codex_feedback',r)) for r in range(4)],
       'decision':'Read complete own-history visual/numeric feedback for next six proposals.' if batch==1 else 'Complete the predeclared aggregate comparison; choose bounded scientific follow-ups and separate aesthetic curation.'})

def summary():
    rows=[]
    for method in METHODS:
        for repeat in range(4):
            h=history(method,repeat)
            if len(h)!=16: raise ValueError('unequal incomplete budgets')
            rows.append({'method':method,'repeat':repeat,'evaluations':len(h),'cell_updates':192*384*len(h),'coverage':coverage(h),'nearest_diversity':mean_nearest_diversity(h),
                         'engine_seconds':sum(r['engine_seconds'] for r in h),'process_seconds':sum(r['process_seconds'] for r in h),
                         'descriptor_seconds':sum(r['descriptors']['descriptor_seconds'] for r in h),'max_native_rss_kib':max(r['max_rss_kib'] for r in h),
                         'coverage_by_trial':[coverage(h[:i+1]) for i in range(len(h))]})
    aggregate={m:{'coverage':bootstrap_mean_ci([r['coverage'] for r in rows if r['method']==m]),'diversity':bootstrap_mean_ci([r['nearest_diversity'] for r in rows if r['method']==m]),
          'process_seconds':sum(r['process_seconds'] for r in rows if r['method']==m),'engine_seconds':sum(r['engine_seconds'] for r in rows if r['method']==m)} for m in METHODS}
    paired={m:bootstrap_mean_ci([next(r['coverage'] for r in rows if r['method']==m and r['repeat']==i)-next(r['coverage'] for r in rows if r['method']=='random' and r['repeat']==i) for i in range(4)]) for m in METHODS[1:]}
    proposals=[json.loads((BASE/f'proposals{i}.json').read_text()) for i in [1,2]]
    save_json(BASE/'summary.json',{'searches':rows,'aggregate':aggregate,'paired_coverage_difference_vs_random':paired,'retained_search_runs':192,'cell_updates':14155776,
      'model_use':{**design()['model_use'],'proposal_batches':2,'configurations_proposed':48,'feedback_to_submission_wall_seconds':[p['feedback_to_submission_wall_seconds'] for p in proposals],
       'wall_interval_scope':'includes human-interface reasoning, tools and other repository work; not isolated model runtime'},
      'limitations':['four search units per method; exploratory bootstrap intervals','one conversation supplies all proposals; repeats do not replicate model sampling independently',
                     'rule and initialization dimensions broaden jointly; archive gain is descriptor-specific','same own-history files available; algorithms intentionally use different parts of feedback',
                     'no score proves life or open-ended evolution; aesthetic curation is separate']})
    print(json.dumps(aggregate,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--phase',required=True,choices=['bootstrap','automatic','proposals','summary','replay']); p.add_argument('--batch',type=int); a=p.parse_args()
    if a.phase=='bootstrap': bootstrap()
    elif a.phase=='automatic': automatic(a.batch)
    elif a.phase=='proposals': proposals(a.batch)
    elif a.phase=='summary': summary()
    else:
        bootstrap()
        for batch in [1,2]: automatic(batch); proposals(batch)
        summary()
