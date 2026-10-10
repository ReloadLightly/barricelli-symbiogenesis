# SPDX-License-Identifier: GPL-3.0-only
"""Interpretable numerical descriptors; none is a life/reproduction detector."""
import collections, zlib, time
import numpy as np

def signatures(row,k=4):
 counts=collections.Counter()
 for window in np.lib.stride_tricks.sliding_window_view(row,k):
  if 99999 in window: continue
  # Ignore all-empty and single-type repeats for this organization diagnostic.
  values=set(map(int,window))-{0}
  if len(values)>=2 and np.count_nonzero(window)>=2: counts[tuple(map(int,window))]+=1
 return counts

def describe(arr,stats=None):
 start=time.perf_counter(); valid=(arr!=0)&(arr!=99999)
 tail=arr[-min(32,len(arr)):]; activity=float(np.mean(tail[1:]!=tail[:-1])) if len(tail)>1 else 0.
 repeat=[]; recurring=[]; first_seen={}; new=[]
 for t,row in enumerate(arr):
  count=signatures(row); total=sum(count.values()); repeated={s for s,n in count.items() if n>=2}
  repeat.append(sum(n for n in count.values() if n>=2)/max(1,total)); recurring.append(repeated)
  fresh=set(count)-set(first_seen); new.append(len(fresh))
  for s in count: first_seen.setdefault(s,t)
 seen_tail=collections.Counter(s for group in recurring[-16:] for s in group)
 retained=[s for s,n in seen_tail.items() if n>=8]
 values,counts=np.unique(tail,return_counts=True); prob=counts/counts.sum(); entropy=float(-(prob*np.log2(prob)).sum())
 raw=tail.astype('<i4').tobytes(); compression=float(1-len(zlib.compress(raw,9))/len(raw))
 shifts=[]; translated=[]
 for old,newrow in zip(tail[:-1],tail[1:]):
  scores=[np.mean(np.roll(old,s)==newrow) for s in range(-8,9)]; ix=int(np.argmax(scores)); shift=ix-8
  shifts.append(shift); translated.append(scores[ix]==1 and shift!=0)
 result={'tail_occupancy':float(valid[-len(tail):].mean()),'tail_activity':activity,
  'tail_repeated4_fraction':float(np.mean(repeat[-len(tail):])),
  'retained_repeated4_signatures':len(retained),'tail_new4_signatures':int(sum(new[-len(tail):])),
  'tail_entropy_bits':entropy,'tail_compressibility':compression,
  'exact_translation_fraction':float(np.mean(translated)) if translated else 0,
  'median_best_shift':float(np.median(shifts)) if shifts else 0,
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
