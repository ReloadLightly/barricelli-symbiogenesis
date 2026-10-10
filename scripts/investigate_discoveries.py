#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""R8b: fresh states, bounded causal probes, copying audits and nearby art worlds."""
import argparse, collections, csv, json, pathlib, sys, datetime
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from barricelli.run import ROOT, read_csv, save_json, sha
from barricelli.descriptors import describe, bootstrap_mean_ci
from barricelli.motifs import outcome, matches, disjoint
from barricelli.lineage import initial_lineages, propagate_step, child_support, root_positions
from scripts.discovery_art import BASE, METHODS, history, configuration, native, now, starting

STUDY=BASE/'investigation'
CONDITIONS=['whole','focal_only','left_half_only','right_half_only','adjacent_removed','matched_damage_elsewhere',
            'composition_shuffle','spacing_shuffle','global_shuffle','rescue','rule_control1','rule_control2','rule_control3']

def select():
    chosen=[]
    for method in METHODS:
        records=[r for repeat in range(4) for r in history(method,repeat) if r['descriptors']['tail_occupancy']>0]
        records.sort(key=lambda r:(-r['descriptors']['retained_repeated4_signatures'],-r['descriptors']['tail_new4_signatures'],
                                  -r['novelty_to_previous_knn3'],r['repeat'],r['trial']))
        chosen.append(records[0])
    return chosen

def declare():
    STUDY.mkdir(exist_ok=True)
    if (STUDY/'design.json').exists(): return
    if not (BASE/'summary.json').exists(): raise ValueError('finish search first')
    candidates=select()
    d={'round':'R8b','declared_utc':now(),'question':'Do selected regimes retain their structure on unseen states and longer runs, depend on nearby components, or show exact recoverable inherited copies?',
       'selection':'one occupied candidate per method: highest retained signatures, then late novelty, then previous-history descriptor novelty; earliest repeat/trial breaks ties. Shared bootstrap states can recur; these are targeted cases, not independent population estimates.',
       'candidates':candidates,'source_time':192,'focal':'earliest richest valid eight-cell window at t192; maximize distinct nonzero types then occupancy; exclude X; whole snapshot is retained',
       'confirmation':{'seeds':[48000,48001,48002,48003],'steps':1536,'width':192},
       'conditions':CONDITIONS,'assay_steps':384,'trace':'whole and isolated focal run separately for two fully traced updates; unchanged ancestry criteria; ring matching uses explicit wrapping',
       'recovery':'at most earliest two certified internally supported common-founder children per candidate; temporal A/B only at even times to retain restart phase; extract actual child into empty same-boundary world,32 updates',
       'measures':['phase-aware world recurrence','retained and newly appearing signatures','tail occupancy/activity/compression','exact focal template presence/persistence/guarded counts','matched damage/rescue equality','full-founder copying and helper dependencies from surviving traced edges','child recovery: template every time and first-update branching'],
       'controls':'adjacent component removal versus same-value/count damage elsewhere, two isolated halves, occupancy/composition-preserving shuffles, exact restoration; three same-start constituent rule controls. Fixed source time192 preserves temporal phase.',
       'budget':{'long_confirmation_runs':12,'perturbation_and_rule_controls':39,'two_update_traces':6,'nearby_art_worlds':12,'baseline_native_runs':69,'baseline_cell_updates':7301376,'max_child_recovery_runs':6,'max_child_recovery_updates':36864,'mode':'serial CPU, one trajectory at a time; traced events streamed'},
       'completion':'retain all69 baseline outcomes; exact continuing snapshot check, complete first-two-update trace audit; execute any qualifying child probes; three actual-trajectory artworks plus four saved neighbors each; negative reproduction/persistence completes the round',
       'interpretation':'exact templates and first-two-update ancestry are limited operational checks; absence excludes only these specified events, not every form of reproduction. Template proliferation alone is not inheritance. No biological partner label is inferred from a component position.',
       'next_decision':'Choose the next bounded hypothesis from actual longer-horizon and perturbation outcomes; keep art and scientific claims separate.'}
    save_json(STUDY/'design.json',d)

def focal(row):
    candidates=[]
    for x in range(len(row)-7):
        m=row[x:x+8]
        if 99999 not in m: candidates.append((len(set(map(int,m))-{0}),int(np.count_nonzero(m)), -x,x))
    if not candidates: raise ValueError('no valid focal window')
    x=max(candidates)[3]; return x,row[x:x+8].copy()

def treatments(row,x):
    w=len(row); motif=row[x:x+8]; isolated=np.zeros(w,dtype=np.int32); isolated[x:x+8]=motif
    result={k:row.copy() for k in CONDITIONS}; result['focal_only']=isolated
    result['left_half_only']=isolated.copy(); result['left_half_only'][x+4:x+8]=0
    result['right_half_only']=isolated.copy(); result['right_half_only'][x:x+4]=0
    adjacent=x+8 if x+16<=w else x-8; removed=[i for i in range(adjacent,adjacent+8) if row[i] not in (0,99999)]
    result['adjacent_removed'][removed]=0
    available=[i for i in range(w) if i not in range(x,x+8) and i not in range(adjacent,adjacent+8) and row[i] not in (0,99999)]
    matched=[]; exact=True
    for i in removed:
        choices=[j for j in available if row[j]==row[i]]
        if not choices: exact=False; choices=available
        if not choices: break
        j=choices[0]; matched.append(j); available.remove(j)
    result['matched_damage_elsewhere'][matched]=0
    rng=np.random.default_rng(771); occupied=np.flatnonzero(motif)
    result['composition_shuffle'][x+occupied]=rng.permutation(motif[occupied])
    result['spacing_shuffle'][x:x+8]=rng.permutation(motif)
    result['global_shuffle']=rng.permutation(row)
    result['rescue']=result['adjacent_removed'].copy(); result['rescue'][removed]=row[removed]
    return result,{'focal_position':x,'motif':motif.tolist(),'adjacent_removed_sites':removed,'matched_removed_sites':matched,'damage_same_count':len(removed)==len(matched),
       'damage_same_value_multiset':exact and len(removed)==len(matched),'composition_shuffle_identity':np.array_equal(result['composition_shuffle'],row),
       'spacing_shuffle_identity':np.array_equal(result['spacing_shuffle'],row),'all_edits':'externally imposed at saved t192 before assay t0; no intervention during dynamics'}

def analyze(path,motif):
    c=json.loads((path/'config.json').read_text()); a=read_csv(path/'trajectory.csv'); s=json.loads((path/'statistics.json').read_text())
    rec={'path':str(path.relative_to(ROOT)),'descriptors':describe(a,s,boundary=c['boundary']),'template':outcome(a,motif,boundary=c['boundary']),
         'trajectory_sha256':sha(path/'trajectory.csv')}
    save_json(path/'analysis.json',rec); return rec

def audit(path,motif,founder):
    c=json.loads((path/'config.json').read_text()); a=read_csv(path/'trajectory.csv'); states=initial_lineages(a[0]); founder_mask=sum(1<<(founder+i) for i,v in enumerate(motif) if v)
    results=[]; nodes=[]; pair=None
    with (path/'events.csv').open() as stream:
        reader=iter(csv.DictReader(stream)); pending=next(reader,None)
        for t in [1,2]:
            def events():
                nonlocal pending
                while pending is not None and int(pending['time'])==t-1:
                    event=pending; pending=next(reader,None); yield event
            states,parents,same,count=propagate_step(a[t-1],a[t],states,events())
            guarded=disjoint(matches(a[t],motif,guard=2,boundary=c['boundary']),len(motif),len(a[t]),c['boundary'])
            extended=states+states[:len(motif)] if c['boundary']=='ring' else states
            support=[child_support(extended,x,motif,founder_mask) for x in guarded]
            qualified=[v for v in support if v['exclusive_full_founder_copying'] and v['dependencies_confined_to_founder'] and v['internal_helper_support']]
            phase_eligible=c['norm']!='galloway_AB_temporal' or t%2==0
            if len(qualified)>=2 and phase_eligible and pair is None: pair={'time':t,'children':qualified[:2]}
            results.append({'time':t,'events_audited':count,'guarded_template_matches':len(guarded),'qualified_children':qualified,'recovery_phase_eligible':phase_eligible,
               'ambiguous_cells':sum(v.roots.bit_count()>1 for v in states),'unknown_copy_origins':sum(v.unknown for v in states)})
            for x,v in enumerate(states):
                if a[t,x] not in (0,99999): nodes.append({'time':t,'x':x,'value':int(a[t,x]),'copy_roots':root_positions(v.roots),'helper_roots':root_positions(v.helpers),'unknown':v.unknown})
        if pending is not None: raise ValueError('trace beyond saved window')
    rec={'trace_matches_every_saved_update':True,'updates':results,'first_internal_common_founder_pair':pair,'source_hashes':{n:sha(path/n) for n in ['initial.csv','trajectory.csv','events.csv']},
         'criterion':'unchanged full-founder unambiguous copy roots, confined dependencies and internal helper support; two disjoint exact footprints with2 empty exterior cells','scope':'two-update operational ancestry only; changed or mutation-origin templates excluded'}
    save_json(path/'copying_audit.json',rec); save_json(path/'lineage_nodes.json',nodes); return rec

def run_study():
    d=json.loads((STUDY/'design.json').read_text()); all_rows=[]; confirmed=[]; audits=[]; recoveries=[]
    for ci,candidate in enumerate(d['candidates']):
        source=ROOT/candidate['path']; original=read_csv(source/'trajectory.csv'); row=original[192]; x,motif=focal(row); treatments_map,metadata=treatments(row,x)
        save_json(STUDY/f'case{ci}.json',{'source_run':candidate['path'],'source_trajectory_sha256':sha(source/'trajectory.csv'),'source_time':192,'selection_method':candidate['method'],**metadata})
        for seed in d['confirmation']['seeds']:
            path=STUDY/f'case{ci}'/f'confirmation{seed}'; conf=configuration(candidate['theta'],seed,path,steps=1536,experiment={'stage':'R8b_reserved','candidate':ci,'source':candidate['path']})
            native(conf,path); record=analyze(path,motif); record['candidate']=ci; record['seed']=seed; confirmed.append(record)
        norms=['galloway_A','galloway_B','galloway_0'] if candidate['theta']['norm'].startswith('galloway_') else ['basic','symbiotic','exclusion']
        for condition in CONDITIONS:
            path=STUDY/f'case{ci}'/condition; theta=dict(candidate['theta'])
            if condition.startswith('rule_control'): theta['norm']=norms[int(condition[-1])-1]
            conf=configuration(theta,None,path,row=treatments_map[condition],experiment={'stage':'R8b_assay','candidate':ci,'condition':condition,**metadata})
            native(conf,path); record=analyze(path,motif); record.update(candidate=ci,condition=condition); all_rows.append(record)
            if condition in ['whole','rescue']:
                np.testing.assert_array_equal(read_csv(path/'trajectory.csv')[:193],original[192:385])
        for condition in ['whole','focal_only']:
            path=STUDY/f'case{ci}'/(condition+'_trace'); conf=configuration(candidate['theta'],None,path,steps=2,row=treatments_map[condition],trace=2,experiment={'stage':'R8b_trace','candidate':ci,'condition':condition})
            native(conf,path); result=audit(path,motif,x); result.update(candidate=ci,condition=condition,path=str(path.relative_to(ROOT))); audits.append(result)
            if condition=='focal_only' and result['first_internal_common_founder_pair']:
                pair=result['first_internal_common_founder_pair']; traced=read_csv(path/'trajectory.csv')
                for index,child in enumerate(pair['children']):
                    isolated=np.zeros(192,dtype=np.int32); isolated[88:96]=traced[pair['time'],(child['position']+np.arange(8))%192]
                    p=STUDY/f'case{ci}'/f'child{index}'; conf=configuration(candidate['theta'],None,p,steps=32,row=isolated,experiment={'stage':'R8b_recovery','candidate':ci,'source_time':pair['time'],'source_child':child,'intervention':'extract actual footprint, translate to88, clear exterior'})
                    native(conf,p); record=analyze(p,motif); record['persistent_every_time']=record['template']['times_with_motif']==33; recoveries.append(record)
        print('case',ci,candidate['method'],candidate['space_index'],'done',flush=True)
    contrast=[]
    for ci in range(3):
        g={r['condition']:r for r in all_rows if r['candidate']==ci}
        contrast.append({'candidate':ci,'adjacent_minus_matched_retained':g['adjacent_removed']['descriptors']['retained_repeated4_signatures']-g['matched_damage_elsewhere']['descriptors']['retained_repeated4_signatures'],
          'isolated_template_present_times':g['focal_only']['template']['times_with_motif'],'isolated_max_detached':g['focal_only']['template']['max_detached_motif_copies'],
          'rescue_numbers_exact':True,'source_continuation_exact':True})
    save_json(STUDY/'summary.json',{'confirmation':confirmed,'assays':all_rows,'contrasts':contrast,'copying_audits':audits,'child_probes':recoveries,
       'first_two_update_certified_reproduction_cases':sum(bool(r['first_internal_common_founder_pair']) for r in audits if r['condition']=='focal_only'),
       'confirmation_aggregate':[{'candidate':ci,'retained':bootstrap_mean_ci([r['descriptors']['retained_repeated4_signatures'] for r in confirmed if r['candidate']==ci]),
         'late_novelty':bootstrap_mean_ci([r['descriptors']['tail_new4_signatures'] for r in confirmed if r['candidate']==ci]),'recurred_worlds':sum(r['descriptors']['recurrence'] is not None for r in confirmed if r['candidate']==ci)} for ci in range(3)],
       'completion':'57 targeted baseline worlds completed;12 nearby artistic variants are counted separately','limits':d['interpretation']})

def nearby():
    curation=json.loads((BASE/'curation.json').read_text()); rows=[]
    for i,work in enumerate(curation['works']):
        source=ROOT/work['source_run']; c=json.loads((source/'config.json').read_text()); theta=c['initial_design']; seed=c['seed']; variants=[]
        variants.append(('new_seed',dict(theta),seed+1,None))
        density=dict(theta); ds=[.15,.35,.65,.9]; density['density']=ds[(ds.index(theta['density'])+1)%4]; variants.append(('density_neighbor',density,seed,None))
        layout=dict(theta); ls=['uniform','center_patch','two_patches','bands']; layout['layout']=ls[(ls.index(theta['layout'])+1)%4]; variants.append(('layout_neighbor',layout,seed,None))
        rule=dict(theta); rule['norm']='galloway_B' if theta['norm']=='galloway_A' else 'galloway_A' if theta['norm'].startswith('galloway_') else 'exclusion' if theta['norm']=='conditional' else 'conditional'
        variants.append(('rule_neighbor',rule,seed,read_csv(source/'initial.csv')[0]))
        for name,t,s,row in variants:
            path=BASE/'nearby'/f'work{i}'/name; conf=configuration(t,s,path,row=row,experiment={'stage':'R8_art_nearby','source':work['source_run'],'condition':name,'intervention':'external one-parameter design change; rule neighbor shares exact original integer row'})
            native(conf,path); rec=analyze(path,[1,-1]); rec.update(work=i,condition=name,source_run=work['source_run']); rows.append(rec)
    save_json(BASE/'nearby/manifest.json',{'runs':rows,'scope':'saved local variants for exploration, not independent search evaluations or evidence of model advantage'})

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['declare','run','nearby'],required=True); a=p.parse_args()
    if a.phase=='declare': declare()
    elif a.phase=='run': run_study()
    else: nearby()
