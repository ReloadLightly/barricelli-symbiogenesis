#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Regenerate or resume the milestone without model calls or source downloads."""
import argparse,pathlib,subprocess,sys,datetime,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def call(script,*args): subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)
def originals():
 call('build.py'); call('reconstruct.py'); call('ensemble.py')
 # The numerical Java oracle method extractor is optional: the original sketch
 # has no explicit software license and is retrieved into a private cache only.
 # Frozen oracle outputs remain included and are checked by the final replay.
 if pathlib.Path('/tmp/barricelli-sources/Barricelli.pde').exists(): call('validate_galloway.py')
 call('assay.py'); call('partner_followup.py')
 call('search.py','--phase','replay'); call('search_confirmation.py')
 call('heterogeneity.py'); call('descriptor_controls.py')
 call('nearby.py','--run','results/search/codex_feedback/repeat3/trial07','--output','results/nearby')
 call('descendant_detector.py','--phase','all')
 call('partner_dyad.py','--phase','all')
 call('figures.py'); call('comparison_figures.py'); call('descendant_figures.py'); call('partner_dyad_figures.py'); call('art.py')
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--regenerate-originals',action='store_true',help='archive prior metadata before rerunning the original pipeline'); args=parser.parse_args()
 if args.regenerate_originals or not (ROOT/'results/run_register.json').exists():
  archive=ROOT/'results/regeneration_history'/datetime.datetime.now(datetime.timezone.utc).strftime('before_%Y%m%dT%H%M%SZ.tar.gz'); archive.parent.mkdir(exist_ok=True)
  with tarfile.open(archive,'w:gz') as stream:
   for p in sorted((ROOT/'results').rglob('*')):
    if p.is_file() and p.suffix in ['.json','.txt'] and 'regeneration_history' not in p.parts: stream.add(p,arcname=str(p.relative_to(ROOT)))
  originals()
 else:
  # Saved original runs and analyses are immutable during routine replay.
  call('build.py'); call('partner_dyad.py','--phase','verify')
 if (ROOT/'results/corrections/descriptor_v2/design.json').exists(): call('correct_descriptors.py'); call('correction_figures.py')
 if (ROOT/'results/discovery_art/curation.json').exists():
  call('discovery_art.py','--phase','replay'); call('investigate_discoveries.py','--phase','declare'); call('investigate_discoveries.py','--phase','run'); call('investigate_discoveries.py','--phase','nearby')
  call('discovery_artworks.py'); call('discovery_figures.py')
 if (ROOT/'results/art/temporal/design.json').exists(): call('temporal_art.py')
 call('register.py'); call('replay_verify.py'); call('build_atlas.py')
 with (ROOT/'results/test-results.txt').open('w') as output:
  subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True)
 call('snapshot.py'); call('check_artifacts.py')
 print('Milestone regenerated; open atlas/index.html. No model calls executed.')
if __name__=='__main__': main()
