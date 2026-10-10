#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Replay recorded aesthetic choices; no model calls or invented image forms."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,sha,save_json
from scripts.art import export
def main():
 base=ROOT/'results/discovery_art'; c=json.loads((base/'curation.json').read_text()); records=[]
 for w in c['works']:
  path=ROOT/w['source_run']; target=ROOT/'results/art'/f"{w['slug']}.recipe.json"
  if target.exists():
   recipe=json.loads(target.read_text())
   if recipe['trajectory_sha256']!=sha(path/'trajectory.csv'): raise ValueError('saved artwork source changed')
  else: recipe=export(path,w['slug'],w['title'])
  records.append({'work':w,'recipe_file':str(target.relative_to(ROOT)),'recipe_sha256':sha(target),'trajectory_sha256':sha(path/'trajectory.csv'),
                  'print_sha256':sha(target.with_name(w['slug']+'.png')),'animation_sha256':sha(target.with_name(w['slug']+'.gif'))})
 save_json(base/'art_manifest.json',{'series':c['series'],'curation_sha256':sha(base/'curation.json'),'works':records,'mode':'reproduction of recorded choices and integer trajectories, without model calls'})
 print('three R8 prints and reveal animations retained')
if __name__=='__main__': main()
