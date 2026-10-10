#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explore four inspectable neighbors of a saved designed-random world."""
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,run,save_json

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run',required=True); p.add_argument('--output',required=True); p.add_argument('--seed',type=int); p.add_argument('--steps',type=int); a=p.parse_args()
 conf=json.loads((pathlib.Path(a.run)/'config.json').read_text())
 if conf.get('initialization')!='designed_random': raise ValueError('choose a designed-random search world for parameter neighbors')
 conf.pop('initial_state_file',None); conf['model']='research'; conf['seed']=a.seed if a.seed is not None else conf['seed']; conf['steps']=a.steps if a.steps is not None else conf['steps']
 layouts=['uniform','center_patch','two_patches']; variants=[]
 for name,key,value in [('density_down','density',max(.05,conf['density']-.15)),('density_up','density',min(.95,conf['density']+.15)),('next_layout','layout',layouts[(layouts.index(conf['layout'])+1)%3]),('constituent_A','norm','galloway_A')]:
  variant=dict(conf); variant[key]=value; variant['variant']='nearby_'+name; variant['modifications']=variant['modifications']+['EXTERNALLY DESIGNED CONFIGURATION NEIGHBOR: '+key+'='+str(value)]
  variants.append({'id':name,'config':variant})
 base=pathlib.Path(a.output); base.mkdir(parents=True,exist_ok=True); save_json(base/'manifest.json',{'parent':a.run,'declared_before_execution':True,'runs':variants})
 for plan in variants: run(plan['config'],base/plan['id'])
 print('saved four neighboring worlds in',base)
if __name__=='__main__': main()
