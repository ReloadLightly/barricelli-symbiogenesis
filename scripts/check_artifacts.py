#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check saved visual recipes, final GIF pixels and local evidence links."""
import json,pathlib,sys,re
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv,sha,save_json
from barricelli.plot import color
import numpy as np
from PIL import Image
def main():
 results=[]
 for p in (ROOT/'results/art').glob('*.recipe.json'):
  r=json.loads(p.read_text()); source=ROOT/r['source_run']; assert sha(source/'trajectory.csv')==r['trajectory_sha256']; assert sha(source/'initial.csv')==r['initial_sha256']; assert sha(ROOT/r['palette_file'])==r['palette_sha256']
  a=read_csv(source/'trajectory.csv'); expected=np.zeros((*a.shape,3),dtype=np.uint8)
  for v in np.unique(a): expected[a==v]=list(bytes.fromhex(color(v)[1:]))
  gif=p.with_name(p.name.removesuffix('.recipe.json')+'.gif')
  with Image.open(gif) as im:
   assert im.n_frames==r['animation']['frames']; assert list(im.size)==r['animation']['frame_dimensions']; im.seek(im.n_frames-1); actual=np.array(im.convert('RGB').crop(r['animation']['numerical_crop'])); np.testing.assert_array_equal(actual,expected)
  results.append({'recipe':str(p.relative_to(ROOT)),'final_frame_numeric_pixels_exact':True,'source_and_palette_hashes_exact':True})
 for p in (ROOT/'results/figures').glob('*.json'):
  meta=json.loads(p.read_text())
  if p.name.endswith('.recipe.json'): continue
  for source in meta['data_sources']: assert sha(ROOT/source['file'])==source['sha256'],p
 broken=[]
 for p in [ROOT/'README.md',ROOT/'PROVENANCE.md',ROOT/'NOTICES.md',ROOT/'atlas/index.html',ROOT/'atlas/register.html']:
  s=p.read_text(); links=re.findall(r'(?:href|src)="([^"]+)"',s) if p.suffix=='.html' else re.findall(r'\]\(([^)]+)\)',s)
  for link in links:
   if link.startswith(('https://','http://','#','mailto:')): continue
   path=(p.parent/link.split('#')[0]).resolve()
   if not path.exists(): broken.append({'file':str(p.relative_to(ROOT)),'link':link})
 assert not broken,broken
 save_json(ROOT/'results/artifact_checks.json',{'artworks':results,'scientific_figure_source_hashes':'all exact','scientific_figures':len(list((ROOT/'results/figures').glob('*.png'))),'local_links_checked':True,'broken_links':broken}); print('saved artwork pixels, figure hashes and evidence links pass')
if __name__=='__main__': main()
