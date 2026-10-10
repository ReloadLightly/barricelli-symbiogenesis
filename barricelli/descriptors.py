# SPDX-License-Identifier: GPL-3.0-only
"""Interpretable numerical descriptors; none is a life/reproduction detector."""
import collections, zlib, time
import numpy as np

def signatures(row,k=4,boundary='open'):
 if boundary not in ('open','ring'): raise ValueError('unknown boundary')
 if k<1: raise ValueError('window must be positive')
 counts=collections.Counter()
 if not len(row) or (boundary=='open' and len(row)<k): return counts
 extended=np.pad(row,(0,k-1),mode='wrap') if boundary=='ring' else row
 for window in np.lib.stride_tricks.sliding_window_view(extended,k):
  if 99999 in window: continue
  # Ignore all-empty and single-type repeats for this organization diagnostic.
  values=set(map(int,window))-{0}
  if len(values)>=2 and np.count_nonzero(window)>=2: counts[tuple(map(int,window))]+=1
 return counts

def translation(old,new,boundary='open',radius=8):
 """Exact motion requires a unique nonzero displacement and no boundary loss.

 Stationary equality takes priority over periodic aliases. Ring offsets are
 deduplicated modulo width. Open shifts use zero exterior and reject lost
 nonzero cells; wrapping is never used for an open world.
 """
 if boundary not in ('open','ring'): raise ValueError('unknown boundary')
 if np.array_equal(old,new): return {'kind':'stationary','shift':0,'best_shift':0,'exact_shifts':[0]}
 scores={}; exact=[]; width=len(old)
 for s in range(-min(radius,width-1),min(radius,width-1)+1):
  key=((s+width//2)%width)-width//2 if boundary=='ring' else s
  if key in scores: continue
  if boundary=='ring': shifted=np.roll(old,key); loss=False
  else:
   shifted=np.zeros_like(old)
   if key>0: shifted[key:]=old[:-key]; loss=bool(np.any(old[-key:]!=0))
   elif key<0: shifted[:key]=old[-key:]; loss=bool(np.any(old[:-key]!=0))
   else: shifted[:]=old; loss=False
  score=float(np.mean(shifted==new)); scores[key]=score
  if score==1 and not loss: exact.append(key)
 best=max(scores.values()); tied=[s for s,v in scores.items() if v==best]
 return {'kind':'unique_motion' if len(exact)==1 else 'ambiguous_motion' if exact else 'no_exact_motion',
         'shift':exact[0] if len(exact)==1 else None,'best_shift':tied[0] if len(tied)==1 else None,'exact_shifts':exact}

def describe(arr,stats=None,*,boundary='open'):
 start=time.perf_counter(); valid=(arr!=0)&(arr!=99999)
 tail=arr[-min(32,len(arr)):]; activity=float(np.mean(tail[1:]!=tail[:-1])) if len(tail)>1 else 0.
 repeat=[]; recurring=[]; first_seen={}; new=[]
 for t,row in enumerate(arr):
  count=signatures(row,boundary=boundary); total=sum(count.values()); repeated={s for s,n in count.items() if n>=2}
  repeat.append(sum(n for n in count.values() if n>=2)/max(1,total)); recurring.append(repeated)
  fresh=set(count)-set(first_seen); new.append(len(fresh))
  for s in count: first_seen.setdefault(s,t)
 seen_tail=collections.Counter(s for group in recurring[-16:] for s in group)
 retained=[s for s,n in seen_tail.items() if n>=8]
 values,counts=np.unique(tail,return_counts=True); prob=counts/counts.sum(); entropy=float(-(prob*np.log2(prob)).sum())
 raw=tail.astype('<i4').tobytes(); compression=float(1-len(zlib.compress(raw,9))/len(raw))
 motions=[translation(old,newrow,boundary) for old,newrow in zip(tail[:-1],tail[1:])]
 shifts=[m['best_shift'] for m in motions if m['best_shift'] is not None]
 translated=[m['kind']=='unique_motion' for m in motions]
 result={'tail_occupancy':float(valid[-len(tail):].mean()),'tail_activity':activity,
  'tail_repeated4_fraction':float(np.mean(repeat[-len(tail):])),
  'retained_repeated4_signatures':len(retained),'tail_new4_signatures':int(sum(new[-len(tail):])),
  'tail_entropy_bits':entropy,'tail_compressibility':compression,
  'exact_translation_fraction':float(np.mean(translated)) if translated else 0,
  'median_best_shift':float(np.median(shifts)) if shifts else None,
  'stationary_fraction':float(np.mean([m['kind']=='stationary' for m in motions])) if motions else 0,
  'ambiguous_translation_fraction':float(np.mean([m['kind']=='ambiguous_motion' for m in motions])) if motions else 0,
  'boundary':boundary,'descriptor_version':2,
  'signature_count_total':len(first_seen),'descriptor_seconds':time.perf_counter()-start}
 if stats: result['recurrence']=stats.get('whole_world_recurrence')
 # Archive coordinates chosen before exploration, all in [0,1].
 result['vector']=[result['tail_occupancy'],activity,result['tail_repeated4_fraction'],compression]
 result['archive_bin']=[min(4,int(result[k]*5)) for k in ['tail_occupancy','tail_activity','tail_repeated4_fraction']]
 return result

def coverage(records): return len({tuple(r['descriptors']['archive_bin']) for r in records})
def mean_nearest_diversity(records):
 if len(records)<2: return 0.
 vec=np.array([r['descriptors']['vector'] for r in records]); d=np.sqrt(np.sum((vec[:,None]-vec[None,:])**2,axis=-1)); np.fill_diagonal(d,np.inf)
 return float(np.min(d,axis=1).mean())

def bootstrap_mean_ci(values,seed=7788):
 values=np.array(values,dtype=float); rng=np.random.default_rng(seed)
 means=np.mean(rng.choice(values,(10000,len(values))),axis=1)
 return {'mean':float(values.mean()),'ci95_percentile':[float(v) for v in np.quantile(means,[.025,.975])],'units':len(values),'method':'seed/search-level bootstrap; exploratory with very few units'}
