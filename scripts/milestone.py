#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Regenerate or resume the milestone without model calls or source downloads."""
import pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def call(script,*args): subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)
def main():
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
 call('figures.py'); call('comparison_figures.py'); call('descendant_figures.py'); call('art.py'); call('register.py'); call('replay_verify.py'); call('build_atlas.py')
 with (ROOT/'results/test-results.txt').open('w') as output:
  subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True)
 call('snapshot.py'); call('check_artifacts.py')
 print('Milestone regenerated; open atlas/index.html. No model calls executed.')
if __name__=='__main__': main()
