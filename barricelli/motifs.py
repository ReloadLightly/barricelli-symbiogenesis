# SPDX-License-Identifier: GPL-3.0-only
"""Declared exact motif matching. Color never identifies a collective."""
import numpy as np

def matches(row,motif,guard=0,boundary='open'):
 """All translations, zero value/position tolerance, open boundaries.
 guard empty cells outside the ENTIRE footprint distinguish detached copies
 from a tiled domain. Truncated matches at an edge are excluded.
 """
 width=len(motif); positions=[]
 if boundary not in ('open','ring'): raise ValueError('unknown boundary')
 if boundary=='ring':
  if len(row)<width+2*guard: return []
  for x in range(len(row)):
   if np.array_equal(row[(x+np.arange(width))%len(row)],motif) and all(row[(x+i)%len(row)]==0 for i in list(range(-guard,0))+list(range(width,width+guard))): positions.append(x)
  return positions
 if len(row)<width: return positions
 windows=np.lib.stride_tricks.sliding_window_view(row,width)
 candidates=np.flatnonzero(np.all(windows==motif,axis=1))
 for x in candidates:
  if x<guard or x+width+guard>len(row): continue
  if not guard or (np.all(row[x-guard:x]==0) and np.all(row[x+width:x+width+guard]==0)): positions.append(int(x))
 return positions

def disjoint(positions,width,world_width=None,boundary='open'):
 selected=[]
 if boundary=='ring':
  if not world_width: raise ValueError('ring disjoint matching requires world width')
  used=set()
  for p in positions:
   footprint={(p+i)%world_width for i in range(width)}
   if not used&footprint: selected.append(p); used|=footprint
  return selected
 for p in positions:
  if not selected or p>=selected[-1]+width: selected.append(p)
 return selected

def outcome(arr,motif,boundary='open'):
 counts=[]; detached=[]; positions=[]
 for row in arr:
  p=matches(row,motif,boundary=boundary); positions.append(p); counts.append(len(disjoint(p,len(motif),len(row),boundary)))
  detached.append(len(disjoint(matches(row,motif,guard=2,boundary=boundary),len(motif),len(row),boundary)))
 present=[t for t,c in enumerate(counts) if c]
 # Domain expansion is a separate quantity; unguarded matches are not offspring.
 return {'max_disjoint_motif_matches':max(counts),'final_motif_matches':counts[-1],
         'motif_persistence_last_time':max(present,default=0),'times_with_motif':len(present),
         'max_detached_motif_copies':max(detached),'detached_beyond_one':max(0,max(detached)-1),
         'motif_counts_by_time':counts,'detached_counts_by_time':detached,'match_positions_by_time':positions}
